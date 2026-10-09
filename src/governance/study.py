"""Explicit offline study adapter; frozen selection is distinct from metric support.

No application imports, acquisition, automatic discovery or legal-time reconstruction.
A study generation always validates again at its permanent path before activation.
"""
from __future__ import annotations

from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import shutil

import geopandas as gpd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely

from .delivery import export_delivery, validate_delivery, METHOD_VERSION, METRICS
from .h3_matrix import _grid, export_h3_matrix
from .preflight import preflight
from .shared.artifacts import sha256_file, sha256_dataset
from .shared.config import load_governance_config
from .shared.schema import validate_governance_geometry
from .shared_contract import export_shared_manifest


@contextmanager
def _workspace(path):
    previous = os.environ.get('GOVERNANCE_WORKSPACE')
    os.environ['GOVERNANCE_WORKSPACE'] = str(Path(path).resolve())
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('GOVERNANCE_WORKSPACE', None)
        else:
            os.environ['GOVERNANCE_WORKSPACE'] = previous


def _write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def _replace(value, old, new):
    if isinstance(value, str):
        return new + value[len(old):] if value == old or value.startswith(old + '/') else value
    if isinstance(value, list):
        return [_replace(x, old, new) for x in value]
    if isinstance(value, dict):
        return {k: _replace(x, old, new) for k, x in value.items()}
    return value


def _binding(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256_file(path), 'bytes': path.stat().st_size}


def _check_binding(record):
    if sha256_file(record['path']) != record['sha256']:
        raise ValueError('Study input checksum mismatch: ' + record['path'])


def study_preflight(study, grids, mask, *, mask_layer, mask_manifest, cache_workspace):
    """Inventory explicit input bindings and cached query scopes without downloading."""
    study, mask = Path(study).resolve(), Path(mask).resolve()
    config = json.loads(study.read_text())
    if config.get('schema_version') != 1 or config['time']['timezone'] != 'UTC':
        raise ValueError('Unsupported study configuration/timezone')
    if config['domain']['selection_policy']['reporting_support'] != 'positive_area_intersection_with_materialized_coastal_plus_inland_water_mask':
        raise ValueError('Unsupported study reporting policy')
    frames = [_grid(Path(p)) for p in grids]
    resolutions = [set(f.H3_RESOLUTION) for f in frames]
    if any(len(r) != 1 for r in resolutions) or len(set.union(*resolutions)) != len(frames):
        raise ValueError('Each study grid must have one distinct resolution')
    if 6 not in set.union(*resolutions):
        raise ValueError('Explicit default R6 grid required')
    water = gpd.read_file(mask, layer=mask_layer)
    if water.empty or water.crs is None or water.crs.to_epsg() != 4326 or not water.geometry.is_valid.all():
        raise ValueError('Mask must be nonempty valid EPSG:4326 geometry')
    mask_provenance = json.loads(Path(mask_manifest).read_text())
    mask_sha256 = sha256_file(mask)
    if mask_provenance['source_mapped_geometry']['raw_sha256'] != mask_sha256:
        raise ValueError('Mask provenance checksum mismatch')
    cache_generation = Path(cache_workspace).resolve().parent / 'generation.json'
    if cache_generation.is_file():
        from .releases import verify_generation
        verify_generation(cache_generation.parent)
    with _workspace(cache_workspace):
        inventory = preflight()
    envelope = config['domain']['bbox_wgs84']
    for source in inventory['sources'].values():
        bbox = source.get('requested_bbox_wgs84')
        selection_mask = source.get('requested_grid_mask_sha256')
        source['study_cache_support'] = (
            'unavailable' if source['runtime_status'] != 'available' else
            'source_selected_against_different_mask_requires_requalification' if selection_mask and
            selection_mask != mask_sha256 else
            'source_selection_mask_matches_requires_roster_review' if selection_mask else
            'query_envelope_covers_study_planning_envelope_only' if bbox and
            bbox[0] <= envelope[0] and bbox[1] <= envelope[1] and bbox[2] >= envelope[2] and bbox[3] >= envelope[3] else
            'query_envelope_does_not_cover_expanded_study' if bbox else
            'cache_scope_requires_source_specific_review')
        source['study_geographic_completeness'] = 'unknown'
    return {'schema_version': 1, 'study': _binding(study), 'study_configuration': config,
            'grids': [_binding(p) | {'resolution': int(next(iter(r))), 'rows': len(f)}
                      for p, r, f in zip(grids, resolutions, frames)],
            'mask': _binding(mask) | {'layer': mask_layer, 'pieces': len(water)},
            'mask_manifest': _binding(mask_manifest), 'mask_provenance': mask_provenance,
            'cache_generation': _binding(cache_generation) if cache_generation.is_file() else None,
            'selection_interpretation': 'Exact frozen supplied membership; mask selection only. Governance measurements use full H3 cells, including mixed land/water cells.',
            'time_interpretation': 'Requested study window retained, with no daily replication, historical applicability or current-law claim.',
            'central_registry_status': config['grid_registry']['status'],
            'explicit_grid_override': 'R6 default and explicitly supplied native R8 companion; no hierarchy rollup or central config mutation',
            'inventory': inventory, 'new_acquisition_bytes': 0}


def _positive_mask_support(grid, water):
    """Independently test positive area against native mask pieces in bounded batches."""
    tree = shapely.STRtree(water.geometry.to_numpy())
    supported = set()
    for offset in range(0, len(grid), 512):
        cells = grid.geometry.to_numpy()[offset:offset + 512]
        pairs = tree.query(cells, predicate='intersects')
        areas = shapely.area(shapely.intersection(cells[pairs[0]], water.geometry.to_numpy()[pairs[1]]))
        supported.update(offset + int(i) for i, area in zip(pairs[0], areas) if area > 0)
    if len(supported) != len(grid):
        raise ValueError(f'{len(grid)-len(supported)} supplied cells lack positive-area mask intersection')
    return len(supported)


def _sample_overlay(matrix, manifests, map_path):
    """Scalar reference calculation, separate from producer's vectorized join.

    Same GEOS/projection libraries; not an independent engine or authority review.
    Compare finite and missing cells in every source-role group at each resolution.
    """
    from pyproj import Transformer
    from shapely.ops import transform, unary_union
    table = pq.read_table(matrix)
    meta = json.loads(table.schema.metadata[b'governance_h3_matrix'])
    grids = _grid(matrix)
    projection = Transformer.from_crs(4326, 6933, always_xy=True).transform
    lengths = Transformer.from_crs(6933, meta['length_crs'], always_xy=True).transform
    checks = []
    for group_name, group in meta['metric_groups'].items():
        native = gpd.read_parquet(map_path(manifests[group['collection']]['artifact']['path']))
        if 'role' in group:
            native = native.loc[(native[group.get('role_field', 'ROUTING_ROLE')] == group['role']) & (native.SOURCE_DATASET_ID == group['source_id'])]
        # Match the explicitly declared producer extent clipping before projection.
        local = native.iloc[native.sindex.query(shapely.box(*grids.total_bounds), predicate='intersects')].copy()
        local.geometry = local.geometry.intersection(shapely.box(*grids.total_bounds))
        projected = local.to_crs(6933)
        count_values = table[group_name + '__FEATURE_COUNT'].to_pylist()
        for resolution in sorted(set(grids.H3_RESOLUTION)):
            ids = np.flatnonzero(grids.H3_RESOLUTION.to_numpy() == resolution)
            selected = []
            for finite in (True, False):
                candidates = [int(i) for i in ids if (count_values[i] is not None) == finite]
                selected.extend(candidates[:2] + candidates[-2:])
            for i in sorted(set(selected)):
                cell = transform(projection, grids.geometry.iloc[i])
                candidates = projected.sindex.query(cell, predicate='intersects')
                hits = []
                for j in candidates:
                    original = projected.geometry.iloc[j]; intersection = cell.intersection(original)
                    dim = int(shapely.get_dimensions(original))
                    if (dim == 2 and intersection.area > 0) or (dim == 1 and intersection.length > 0) or (dim == 0 and not intersection.is_empty):
                        hits.append((j, intersection, dim))
                expected = {'FEATURE_COUNT': len({projected.iloc[j].GOVERNANCE_FEATURE_ID for j, _, _ in hits}) if hits else None,
                            'POLYGON_COVERAGE_FRAC': None, 'LINE_LENGTH_M': None, 'POINT_COUNT': None}
                polygons = [x for _, x, dim in hits if dim == 2]
                lines = [x for _, x, dim in hits if dim == 1]
                points = {projected.iloc[j].GOVERNANCE_FEATURE_ID for j, _, dim in hits if dim == 0}
                if polygons: expected['POLYGON_COVERAGE_FRAC'] = min(1., unary_union(polygons).area / cell.area)
                if lines: expected['LINE_LENGTH_M'] = transform(lengths, unary_union(lines)).length
                if points: expected['POINT_COUNT'] = len(points)
                if not hits and manifests[group['collection']]['source_completeness'] == 'complete':
                    expected = dict.fromkeys(expected, 0)
                for name, value in expected.items():
                    actual = table[group_name + '__' + name][i].as_py()
                    if (value is None) != (actual is None) or (value is not None and not np.isclose(value, actual, rtol=1e-8, atol=1e-7)):
                        raise ValueError(f'Independent overlay mismatch: {group_name}/{grids.H3_INDEX.iloc[i]}/{name}')
                checks.append({'group': group_name, 'resolution': int(resolution), 'h3_index': grids.H3_INDEX.iloc[i], 'status': 'passed'})
    return checks


def validate_study_release(root, *, independent=True):
    """Read every final table, native companion and source; never mutate a release."""
    from jsonschema import Draft202012Validator, FormatChecker
    root = Path(root).resolve()
    contract = json.loads((root / 'study-contract.json').read_text())
    if contract.get('schema_version') != 1:
        raise ValueError('Unsupported study release contract')
    permanent = contract['permanent_release_path']
    def map_path(path):
        replaced = _replace(str(path), permanent, str(root))
        result = Path(replaced).resolve()
        if result != root and root not in result.parents:
            raise ValueError('Study member escapes generation: ' + str(path))
        return result
    for binding in contract['retained_bindings']:
        _check_binding(binding | {'path': str(map_path(binding['path']))})
    water = gpd.read_file(map_path(contract['mask_path']), layer=contract['mask_layer'])
    if water.empty or water.crs.to_epsg() != 4326 or not water.geometry.is_valid.all():
        raise ValueError('Invalid retained study mask')
    mask_provenance = json.loads(map_path(contract['mask_manifest_path']).read_text())
    if mask_provenance['source_mapped_geometry']['raw_sha256'] != sha256_file(map_path(contract['mask_path'])):
        raise ValueError('Retained mask provenance checksum mismatch')
    native_manifests = {}
    matrix_path = map_path(contract['matrix_path'])
    matrix = pq.read_table(matrix_path)
    meta = json.loads(matrix.schema.metadata[b'governance_h3_matrix'])
    with _workspace(root / 'workspace'):
        config = load_governance_config()
    if config.config_hash != meta['config_hash'] or set(config.collections) != set(meta['native_manifests']):
        raise ValueError('Study effective configuration mismatch')
    for name, record in meta['native_manifests'].items():
        native = record['manifest']
        if (native['config_hash'] != config.config_hash or
                sha256_file(map_path(native['config_path'])) != native['config_sha256'] or
                sha256_file(map_path(native['common_config_path'])) != native['common_config_sha256']):
            raise ValueError('Native configuration binding mismatch')
        artifact = map_path(native['artifact']['path'])
        if sha256_file(artifact) != native['artifact']['sha256']:
            raise ValueError('Native artifact checksum mismatch')
        frame = gpd.read_parquet(artifact)
        validate_governance_geometry(frame)
        if len(frame) != native['artifact']['rows'] or native['model_eligible'] is not False or native['h3_resolution'] is not None:
            raise ValueError('Native contract mismatch')
        manifest_path = map_path(contract['native_manifest_paths'][name])
        if sha256_file(manifest_path) != record['manifest_sha256'] or json.loads(manifest_path.read_text()) != native:
            raise ValueError('Native embedded manifest mismatch')
        for source in native['sources']:
            if source['runtime_status'] == 'available' and sha256_dataset(map_path(source['snapshot_path'])) != source['snapshot_sha256']:
                raise ValueError('Source dataset checksum mismatch')
        for related in native.get('related_artifacts', {}).values():
            if isinstance(related, dict) and related.get('path') and related.get('sha256'):
                if sha256_file(map_path(related['path'])) != related['sha256']:
                    raise ValueError('Native companion checksum mismatch')
        native_manifests[name] = native
    schema = json.loads(map_path(contract['shared_schema_path']).read_text())
    results = []
    for item in contract['tables']:
        artifact, companion = map_path(item['artifact']), map_path(item['manifest'])
        result = validate_delivery(artifact, companion)
        local = json.loads(companion.read_text())
        if local['scientific_method_version'] != METHOD_VERSION or local['data_release_id'] != root.name and local['data_release_id'] != Path(permanent).name:
            raise ValueError('Delivery identity/method mismatch')
        if local['model_eligible'] is not False or local['temporal']['type'] != 'static':
            raise ValueError('Study snapshot interpretation mismatch')
        if (local['native_manifests'] != meta['native_manifests'] or
                local['overlay']['sha256'] != sha256_file(matrix_path) or
                local['configuration_hash'] != config.config_hash):
            raise ValueError('Delivery lineage mismatch')
        grid = _grid(map_path(item['grid']))
        cells = pq.read_table(artifact, columns=['h3_index'])['h3_index'].to_pylist()
        if sha256_file(map_path(item['grid'])) != item['grid_sha256'] or cells != list(grid.H3_INDEX):
            raise ValueError('Exact frozen grid membership/order mismatch')
        subset = matrix.filter(pa.compute.equal(matrix['H3_RESOLUTION'], result['resolution']))
        if cells != subset['H3_INDEX'].to_pylist():
            raise ValueError('Matrix/delivery membership mismatch')
        delivery = pq.read_table(artifact)
        for group in meta['metric_groups']:
            for source_name, (suffix, _, _) in METRICS.items():
                name = group + '__' + suffix
                if name in delivery.column_names and not delivery[name].equals(subset[group + '__' + source_name]):
                    raise ValueError('Matrix/delivery values mismatch: ' + name)
        result['positive_area_mask_cells'] = _positive_mask_support(grid, water)
        shared = json.loads(map_path(item['shared_manifest']).read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(shared)
        if shared['artifact']['sha256'] != sha256_file(artifact):
            raise ValueError('Shared artifact mismatch')
        results.append(result)
    if matrix['MODEL_ELIGIBLE'].to_pylist() != [False] * matrix.num_rows:
        raise ValueError('Overlay model eligibility mismatch')
    return {'status': 'passed', 'tables': results, 'native_collections': len(native_manifests),
            'independent_samples': _sample_overlay(matrix_path, native_manifests, map_path) if independent else [],
            'independent_limit': 'Scalar separate join/union implementation, shared GEOS and projection libraries; no legal certification.'}


def run_study(study, grids, mask, *, mask_layer, mask_manifest, cache_workspace, output,
              permanent_release_path, release_id, software_revision, schema,
              schema_reference, staging_cap_bytes=2700000000, length_crs='EPSG:32610',
              resume_native=False):
    """Rebuild cached native products and prepare an immutable, validated study bundle.

    Output must be new. The caller explicitly publishes it; no network is accessed.
    One worker. Existing cache/config/native files are never changed.
    """
    output, cache_workspace = Path(output).resolve(), Path(cache_workspace).resolve()
    report = study_preflight(study, grids, mask, mask_layer=mask_layer, mask_manifest=mask_manifest, cache_workspace=cache_workspace)
    required = sum(p.stat().st_size for d in ('config', 'data/raw') for p in (cache_workspace / d).rglob('*') if p.is_file())
    # Conservative bound: cached raw plus native/release duplication and expanded overlay.
    estimated_peak = 2 * (required + 500000000)
    if estimated_peak > staging_cap_bytes or shutil.disk_usage(output.parent).free < estimated_peak:
        raise ValueError('Study staging estimate exceeds cap or free disk')
    report['resource_estimate'] = {'estimated_peak_staging_bytes': estimated_peak,
                                  'staging_cap_bytes': staging_cap_bytes, 'one_worker': True, 'new_acquisition_bytes': 0}
    workspace = output / 'workspace'
    support = output / 'study-support'
    if resume_native:
        if (output / 'delivery').exists() or (output / 'study-contract.json').exists():
            raise ValueError('Resume requires unassembled native staging')
        prior = json.loads((output / 'preflight.json').read_text())
        for name in ('study', 'grids', 'mask', 'mask_manifest', 'cache_generation'):
            if prior[name] != report[name]:
                raise ValueError('Resume input binding mismatch: ' + name)
        for original, retained in ((study, support / 'study.v1.json'),
                                   (mask, support / 'land-water.gpkg'),
                                   (mask_manifest, support / 'mask-source-manifest.json'),
                                   (schema, support / 'shared-schema.json')):
            if sha256_file(original) != sha256_file(retained):
                raise ValueError('Resume retained input mismatch')
        for record in report['grids']:
            expected = pq.read_table(record['path'], columns=['H3_INDEX', 'H3_RESOLUTION'])
            retained = pq.read_table(support / f"grid-r{record['resolution']}.parquet")
            if not expected.equals(retained, check_metadata=False):
                raise ValueError('Resume retained grid mismatch')
    else:
        output.mkdir(exist_ok=False)
        _write(output / 'preflight.json', report)
        shutil.copytree(cache_workspace / 'config', workspace / 'config')
        shutil.copytree(cache_workspace / 'data/raw', workspace / 'data/raw')
        support.mkdir()
        shutil.copyfile(study, support / 'study.v1.json')
        shutil.copyfile(mask, support / 'land-water.gpkg')
        shutil.copyfile(mask_manifest, support / 'mask-source-manifest.json')
        shutil.copyfile(schema, support / 'shared-schema.json')
        merged = []
        for record in report['grids']:
            grid = pq.read_table(record['path'], columns=['H3_INDEX', 'H3_RESOLUTION'])
            pq.write_table(grid, support / f"grid-r{record['resolution']}.parquet", compression='zstd')
            merged.append(grid)
        pq.write_table(pa.concat_tables(merged), support / 'grid.parquet', compression='zstd')
    with _workspace(workspace):
        config = load_governance_config()
        if not resume_native:
            for name, collection in config.collections.items():
                print('BUILD ' + name, flush=True)
                importlib.import_module(f'governance.{collection.category}.{name}.build').build(config.path, allow_partial=True)
        else:
            from .shared.artifacts import load_manifest
            for name, collection in config.collections.items():
                native = load_manifest(collection.manifest_path)
                if Path(native['artifact']['path']).resolve() != collection.artifact_path.resolve():
                    raise ValueError('Resume native path mismatch: ' + name)
            print('RESUME verified native collections: ' + str(len(config.collections)), flush=True)
        matrix = export_h3_matrix(support / 'grid.parquet', workspace / 'governance-h3-matrix.parquet', length_crs=length_crs, allow_partial=True)
        _write(output / 'postbuild-inventory.json', preflight())
    permanent = str(Path(permanent_release_path).resolve())
    # Relocate only this run's structured path references, never provider strings/URLs.
    for path in (workspace / 'data/processed').rglob('*.json'):
        value = _replace(json.loads(path.read_text()), str(output), permanent)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    table = pq.read_table(matrix)
    meta = _replace(json.loads(table.schema.metadata[b'governance_h3_matrix']), str(output), permanent)
    native_manifest_paths = {}
    for name, record in meta['native_manifests'].items():
        path = config.collections[name].manifest_path
        value = json.loads(path.read_text())
        for related in value.get('related_artifacts', {}).values():
            if isinstance(related, dict) and related.get('path') and related.get('sha256'):
                related['sha256'] = sha256_file(_replace(related['path'], permanent, str(output)))
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
        record['manifest'], record['manifest_sha256'] = value, sha256_file(path)
        native_manifest_paths[name] = _replace(str(path), str(output), permanent)
    pq.write_table(table.replace_schema_metadata({b'governance_h3_matrix': json.dumps(meta, sort_keys=True).encode()}), matrix, compression='zstd')
    written = export_delivery(matrix, output / 'delivery', release_id=release_id, software_revision=software_revision)
    tables = []
    for artifact in (p for p in written if p.suffix == '.parquet'):
        companion = artifact.with_suffix('.manifest.json')
        local = json.loads(companion.read_text())
        local['overlay']['path'] = permanent + '/workspace/governance-h3-matrix.parquet'
        local['study_binding'] = {'study_sha256': sha256_file(study), 'mask_sha256': sha256_file(mask),
                                 'selection_support': report['selection_interpretation'],
                                 'requested_time_window': report['study_configuration']['time'],
                                 'legal_effective_time_coverage': 'unavailable', 'central_registry_status': report['central_registry_status']}
        companion.write_text(json.dumps(local, indent=2, sort_keys=True) + '\n')
        shared = export_shared_manifest(artifact, companion, schema, schema_reference=schema_reference)
        resolution = local['spatial']['h3_resolution']
        record = next(r for r in report['grids'] if r['resolution'] == resolution)
        tables.append({'artifact': _replace(str(artifact), str(output), permanent),
                       'manifest': _replace(str(companion), str(output), permanent),
                       'shared_manifest': _replace(str(shared), str(output), permanent),
                       'grid': permanent + f'/study-support/grid-r{resolution}.parquet',
                       'grid_sha256': sha256_file(support / f'grid-r{resolution}.parquet'),
                       'external_grid': record['path']})
    for binding in [report['study'], report['mask'], report['mask_manifest'], _binding(schema), *report['grids']]:
        _check_binding(binding)
    _write(output / 'metric-dictionary.json', {p.name: json.loads(p.read_text())['fields'] for p in written if p.name.endswith('.manifest.json')})
    _write(output / 'study-contract.json', {'schema_version': 1, 'permanent_release_path': permanent,
            'study_path': permanent + '/study-support/study.v1.json',
            'mask_path': permanent + '/study-support/land-water.gpkg', 'mask_layer': mask_layer,
            'mask_manifest_path': permanent + '/study-support/mask-source-manifest.json',
            'shared_schema_path': permanent + '/study-support/shared-schema.json',
            'matrix_path': permanent + '/workspace/governance-h3-matrix.parquet',
            'native_manifest_paths': native_manifest_paths, 'tables': tables,
            'external_bindings': [report['study'], report['mask'], report['mask_manifest'], _binding(schema), *report['grids']],
            'retained_bindings': [_binding(p) | {'path': _replace(str(p), str(output), permanent)}
                                  for p in support.iterdir() if p.is_file()]})
    total = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if total * 2 > staging_cap_bytes:
        raise ValueError('Actual preparation plus publication exceeds staging cap')
    _write(output / 'validation.json', validate_study_release(output))
    return output
