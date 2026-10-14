"""Single-collection research getters with explicit workspace and request receipts."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import box
from shapely.ops import unary_union

from .shared.acquisition import (AcquisitionBudget, CacheScopeError, SourceUnavailableError,
    download_arcgis_snapshot, download_direct_snapshot, read_source_frame, resolve_source_path, _ResponseBudget)
from .shared.artifacts import source_record
from .shared.config import GovernanceConfig, DEFAULT_CONFIG_PATH, load_governance_config, strict_bool
from .shared.grid import validate_resolution
from .shared.registry import normalize_collection
from .shared.schema import empty_governance_frame, validate_governance_geometry
from .shared.spatial import bbox_parts, clip_to_full_area, concatenate_clipped_frames, validate_bbox
from .workspace import initialize_workspace


def _producer():
    """Use package/VCS installation metadata; never probe cwd or require Git."""
    from importlib.metadata import distribution, PackageNotFoundError
    from . import __version__
    revision = None
    try:
        installed = distribution('toolkit-governance')
        direct = json.loads(installed.read_text('direct_url.json') or '{}')
        candidate = direct.get('vcs_info', {}).get('commit_id')
        if (Path(installed.locate_file('governance/__init__.py')).resolve() == Path(__file__).with_name('__init__.py').resolve()
            and installed.version == __version__ and direct.get('vcs_info', {}).get('vcs') == 'git'
            and isinstance(candidate, str) and len(candidate) == 40
            and all(character in '0123456789abcdef' for character in candidate)):
            revision = candidate
    except (PackageNotFoundError, ValueError, TypeError, AttributeError, OSError):
        pass
    return {'package': 'toolkit-governance', 'version': __version__, 'code_revision': revision,
            'code_revision_source': 'installed_vcs_metadata' if revision else 'unavailable'}


class LayerNotImplementedError(NotImplementedError):
    """Planned layer has no qualified geometry implementation."""


@dataclass(frozen=True)
class GovernanceResult:
    features: gpd.GeoDataFrame
    h3: pd.DataFrame | None
    memberships: pd.DataFrame | None
    coverage: pd.DataFrame
    provenance: dict[str, Any]


def _support_bbox(grid, bbox):
    bounds = grid.total_bounds
    if bbox[0] > bbox[2] or bounds[2] - bounds[0] > 180:
        pieces = [part for geometry in grid.geometry for part in getattr(geometry, 'geoms', [geometry])]
        positive = [part.bounds[0] for part in pieces if part.centroid.x >= 0]
        negative = [part.bounds[2] for part in pieces if part.centroid.x < 0]
        return (min(positive), float(bounds[1]), max(negative), float(bounds[3]))
    return tuple(map(float, bounds))


def get_layer(collection_id: str, bounding_box, *, make_h3: bool = False, h3_res: int = 7,
              sources: Sequence[str] | str | None = None, systems: Sequence[str] | str | None = None,
              workspace: str | Path | None = None, cache: str | Path | None = None,
              config: GovernanceConfig | None = None, config_path: str | Path = DEFAULT_CONFIG_PATH,
              allow_partial: bool = False, include_proposed: bool = False,
              mode: str = 'cache-first', as_of: str | None = None,
              budget: AcquisitionBudget | None = None, max_cells: int = 100_000,
              max_memberships: int = 1_000_000) -> GovernanceResult:
    """Return full native boundaries intersecting bbox (or full intersecting H3 cells).

    Only this acquisition-capable API retrieves missing inputs. Offline never calls
    acquisition. Cache-first validates receipts; refresh stages a replacement.
    ``as_of`` is rejected: inventories cannot reconstruct historical law.
    """
    if type(max_cells) is not int or max_cells <= 0 or type(max_memberships) is not int or max_memberships <= 0:
        raise ValueError('Cell and membership budgets must be positive integers')
    started = time.perf_counter()
    bbox = validate_bbox(bounding_box)
    for name, value in [('make_h3', make_h3), ('allow_partial', allow_partial), ('include_proposed', include_proposed)]:
        strict_bool(value, name)
    validate_resolution(h3_res)
    if not make_h3 and h3_res != 7:
        raise ValueError('h3_res requires make_h3=True')
    if include_proposed and collection_id != 'marine_protected_areas':
        raise ValueError('include_proposed is supported for marine_protected_areas only')
    if mode not in {'cache-first', 'refresh', 'offline'}:
        raise ValueError('mode must be cache-first, refresh, or offline')
    if as_of is not None:
        raise ValueError('Historical as_of queries are unsupported; current inventories are not historical law')
    if sources is not None and systems is not None:
        raise ValueError('Select sources or systems, not both; systems currently use exact provider source IDs')
    if config is not None and (workspace is not None or config_path != DEFAULT_CONFIG_PATH):
        raise ValueError('Pass config or workspace/config_path, not both')
    if config is None:
        root = Path(workspace or Path.cwd()).expanduser().resolve()
        initialize_workspace(root)
        config = load_governance_config(config_path, workspace=root)
    if collection_id not in config.collections:
        from .shared.registry import CATEGORY_COLLECTIONS
        if collection_id not in {name for names in CATEGORY_COLLECTIONS.values() for name in names}:
            raise ValueError(f'Unknown governance layer {collection_id!r}')
        raise LayerNotImplementedError(f'{collection_id}: no qualified provider geometry; see coverage matrix')
    collection = config.collections[collection_id]
    selected = sources if sources is not None else systems
    if systems is not None:
        aliases = {'wdfw.recreational_marine_catch_reporting':'wdfw_recreational_marine_areas', 'adfg.groundfish.statistical':'adfg_groundfish_statistical_areas', 'dfo.pacific.pfma.subareas':'dfo_pacific_fishery_management_areas'}
        selected = aliases.get(selected, selected) if isinstance(selected, str) else [aliases.get(value, value) for value in selected]
    source_ids = (selected,) if isinstance(selected, str) else tuple(selected) if selected is not None else collection.source_ids
    if not source_ids or any(not isinstance(s, str) for s in source_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError('Source selectors must contain unique, nonempty source IDs')
    unknown = set(source_ids).difference(collection.source_ids)
    if unknown:
        raise ValueError(f'Invalid source/system selectors for {collection_id}: {sorted(unknown)}')
    excluded_proposals = 'dfo_oceans_act_areas_of_interest' in source_ids and not include_proposed
    if not include_proposed:
        source_ids = tuple(s for s in source_ids if s != 'dfo_oceans_act_areas_of_interest')
    grid = None
    support = bbox
    if make_h3:
        from .shared.grid import candidate_grid
        grid = candidate_grid(bbox, h3_res, max_cells=max_cells)
        if not grid.empty:
            support = _support_bbox(grid, bbox)
    selector_shape = unary_union(grid.geometry) if grid is not None and not grid.empty else unary_union(bbox_parts(bbox))
    from .shared.availability import provider_region_states
    frames, coverage, receipts, timings = [], [], [], []
    transfer_budget = _ResponseBudget((budget or AcquisitionBudget()).max_bytes)
    for source_id in source_ids:
        source = config.sources[source_id]
        if cache is not None and source.snapshot_path is not None:
            source = replace(source, snapshot_path=Path(cache).expanduser().resolve() / source_id / source.snapshot_path.name)
        request_source = source
        if source.acquisition_type in {'arcgis', 'local_vector_or_arcgis'} and source.snapshot_path is not None:
            identity = hashlib.sha256(json.dumps([source.url, source.provider, source.source_as_of, source.selection_where, source.requested_grid_mask_sha256, support], sort_keys=True).encode()).hexdigest()[:24]
            request_source = replace(source, local_path=None, snapshot_path=source.snapshot_path.parent / 'queries' / identity / 'features.pages.json')
            if resolve_source_path(source) is None and resolve_source_path(request_source) is not None:
                source = request_source
        if mode == 'refresh' and source.local_path is not None and source.local_path.exists():
            raise ValueError(f'{source_id}: refresh conflicts with an explicit local_path override; use offline/cache-first or remove the override')
        acquisition_start = time.perf_counter()
        state, reason, raw = 'unavailable', source.source_limitation, None
        try:
            if source.source_status == 'unavailable' or source.acquisition_type == 'reference_only':
                raise SourceUnavailableError(f'{source_id}: provider is explicitly unavailable: {source.source_limitation}')
            if mode != 'refresh' and resolve_source_path(source) is not None:
                try:
                    raw = read_source_frame(source, bbox=support)
                except CacheScopeError:
                    if request_source.snapshot_path != source.snapshot_path and resolve_source_path(request_source) is not None:
                        source = request_source
                        raw = read_source_frame(source, bbox=support)
                    elif mode == 'offline':
                        raise
            if raw is None:
                if mode == 'offline':
                    raise SourceUnavailableError(f'{source_id}: no compatible offline cache')
                if source.acquisition_type in {'arcgis', 'local_vector_or_arcgis'}:
                    if source.snapshot_path is None:
                        raise SourceUnavailableError(f'{source_id}: missing cache destination')
                    source = request_source
                    if transfer_budget.received >= transfer_budget.maximum:
                        raise SourceUnavailableError('Aggregate query acquisition byte budget exhausted')
                    download_arcgis_snapshot(source, bbox=support, overwrite=mode == 'refresh', budget=budget, transfer_budget=transfer_budget)
                elif source.acquisition_type == 'direct_archive':
                    if source.snapshot_path is None or source.snapshot_path.suffix.lower() in {'.parquet', '.geoparquet'}:
                        raise SourceUnavailableError(f'{source_id}: requires provisioned provider-specific source frame; automatic bulk download unsupported')
                    if transfer_budget.received >= transfer_budget.maximum:
                        raise SourceUnavailableError('Aggregate query acquisition byte budget exhausted')
                    download_direct_snapshot(source, overwrite=mode == 'refresh', max_bytes=(budget or AcquisitionBudget()).max_bytes, transfer_budget=transfer_budget)
                else:
                    raise SourceUnavailableError(f'{source_id}: acquisition type {source.acquisition_type} unavailable')
                raw = read_source_frame(source, bbox=support)
            acquisition_end = time.perf_counter()
            normalized = normalize_collection(raw, source, collection)
            if collection_id == 'marine_protected_areas' and not include_proposed and 'DESIGNATION_STATUS' in normalized:
                normalized = normalized.loc[~normalized.DESIGNATION_STATUS.eq('area_of_interest')].copy()
            # Canonicalize wrapping/repairs over the globe without clipping at user bbox.
            full_config = replace(config, bounds=dict(min_lon=-180., min_lat=-90., max_lon=180., max_lat=90.))
            native, diagnostics = clip_to_full_area(normalized, full_config)
            native = native.loc[native.geometry.intersects(selector_shape)].copy()
            validate_governance_geometry(native)
            frames.append(native)
            state = 'empty' if native.empty else 'available'
            receipts.append({**source_record(source, resolve_source_path(source)), 'query_receipt': raw.attrs.get('request_receipt'), 'clipping': diagnostics.to_dict()})
            timings.append({'source_id': source_id, 'acquisition_or_cache_s': acquisition_end-acquisition_start, 'normalize_select_s': time.perf_counter()-acquisition_end, 'source_rows': len(raw), 'native_parts': len(native)})
        except (SourceUnavailableError, requests.RequestException) as error:
            if not allow_partial:
                raise SourceUnavailableError(f'{source_id}: {error}') from error
            reason = str(error)
            receipts.append(source_record(source, None))
        geographic = 'partial' if any(status in {'partial', 'unknown', 'unavailable'} for status in source.coverage.values()) else 'qualified_named_source_scope'
        coverage.append({'collection': collection_id, 'source_id': source_id, 'provider': source.provider,
            'status': state, 'acquisition_completeness': 'complete' if raw is not None else 'unavailable',
            'geographic_completeness': geographic, 'legal_currentness': 'not_verified',
            'temporal_capability': 'instrument_version_snapshot' if source_id == 'tc_srkw_interim_order_2026' else 'inventory_snapshot_only', 'source_regions': dict(source.coverage), 'regional_support': provider_region_states(source),
            'requested_bbox': list(bbox), 'source_support_bbox': list(support), 'limitation': reason})
    if not allow_partial and any(row['geographic_completeness'] == 'partial' for row in coverage):
        raise SourceUnavailableError('Geographic completeness is partial/unknown; pass allow_partial=True for research inventories')
    from .maintenance.catalog import EXTRA_FEATURES
    if excluded_proposals:
        coverage.append({'collection': collection_id, 'source_id': 'dfo_oceans_act_areas_of_interest', 'provider': config.sources['dfo_oceans_act_areas_of_interest'].provider,
            'status': 'not_applicable', 'acquisition_completeness': 'not_applicable', 'geographic_completeness': 'not_applicable', 'legal_currentness': 'not_verified',
            'temporal_capability': 'inventory_snapshot_only', 'source_regions': dict(config.sources['dfo_oceans_act_areas_of_interest'].coverage), 'requested_bbox': list(bbox),
            'source_support_bbox': list(support), 'limitation': 'Proposals excluded by default; no source query executed'})
    features = concatenate_clipped_frames(frames) if frames else empty_governance_frame(extra_fields=[field[0] for field in EXTRA_FEATURES.get(collection_id, ())])
    metrics = memberships = None
    h3_start = time.perf_counter()
    if grid is not None:
        from .shared.query_overlay import overlay
        metrics, memberships = overlay(grid, features, source_ids=source_ids, coverage=coverage, max_memberships=max_memberships)
    provenance = {'result_schema_version': 1, 'scientific_method_version': 'native-reference-query-2.1', 'producer': _producer(),
        'collection': collection_id, 'request': {'bounding_box': list(bbox), 'make_h3': make_h3, 'h3_res': h3_res if make_h3 else None, 'source_ids': list(source_ids), 'include_proposed': include_proposed, 'mode': mode},
        'sources': receipts, 'config_hash': config.config_hash,
        'query_time_utc': datetime.now(UTC).isoformat(), 'time_semantics': 'Knowledge timestamps retain source receipts; query/build time is separate. No historical legal inference.',
        'spatial_semantics': 'Full native boundaries selected by intersection; H3 requests select full cell support, never bbox-truncated cell denominators.',
        'model_eligible': False, 'acquisition_decoded_bytes': transfer_budget.received, 'measurements': {'polygon_coverage_full_cell_fraction': 'EPSG:6933 union area / full cell area; no water denominator', 'line_union_length_m': 'WGS84 geodesic length', 'point_count': 'distinct recorded coordinates; boundary points count in each touching cell'},
        'timings': {'sources': timings, 'h3_s': time.perf_counter()-h3_start, 'total_s': time.perf_counter()-started}}
    return GovernanceResult(features, metrics, memberships, pd.DataFrame(coverage), provenance)


def _getter(collection_id):
    def getter(bounding_box, **options):
        return get_layer(collection_id, bounding_box, **options)
    import inspect
    signature = inspect.signature(get_layer)
    getter.__signature__ = signature.replace(parameters=list(signature.parameters.values())[1:])
    getter.__name__ = 'get_' + collection_id
    getter.__doc__ = f'Query {collection_id}. Keyword options and return contract follow governance.get_layer.'
    return getter

from .shared.registry import CATEGORY_COLLECTIONS
for _collections in CATEGORY_COLLECTIONS.values():
    for _collection in _collections:
        globals()['get_' + _collection] = _getter(_collection)
get_fishery_management_areas = get_management_areas
get_marine_protected_area = get_marine_protected_areas
get_vessel_exclusion_zones = get_exclusion_zones
# No qualified safety/security systems exist; specific exception, never an empty inventory.
def get_safety_security_zones(bounding_box, **options):
    validate_bbox(bounding_box)
    raise LayerNotImplementedError('Safety/security zones require a qualified issuer/instrument/geometry roster')
