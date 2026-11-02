"""Bounded, receipt-verified acquisition; incomplete replacements never become caches."""
from __future__ import annotations

import json
from contextvars import ContextVar
import os
import tempfile
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests

from .artifacts import atomic_write_json, sha256_dataset, sha256_file
from .config import GovernanceConfig, GovernanceSource
from .spatial import bbox_parts, validate_bbox

HEADERS = {"User-Agent": "MarineCastGovernance/0.2 (+https://github.com/MarineCast/toolkit-governance)", "Accept": "application/json, application/geo+json, */*"}

@dataclass
class _ResponseBudget:
    maximum: int
    received: int = 0

_RESPONSE_BUDGET = ContextVar('governance_response_budget', default=None)


class SourceUnavailableError(RuntimeError):
    """No qualified runtime source is available (never a verified zero)."""

class CacheScopeError(ValueError):
    """Cached receipt cannot satisfy the requested source/selector/support."""

class ArcGISError(SourceUnavailableError):
    def __init__(self, url, error):
        self.code = error.get('code') if isinstance(error, dict) else None
        super().__init__(f"ArcGIS error from {url}: {error}")

@dataclass(frozen=True)
class AcquisitionBudget:
    max_bytes: int = 64_000_000
    max_features: int = 50_000
    max_pages: int = 2_000
    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in (self.max_bytes, self.max_features, self.max_pages)):
            raise ValueError('Acquisition budgets must be positive integers')


def resolve_source_path(source: GovernanceSource) -> Path | None:
    for path in (source.local_path, source.snapshot_path):
        if path is not None and path.exists():
            return path
    return None


def _response_json(url: str, *, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    """Bound each decoded response and retry only transient network/service failures."""
    for attempt in range(3):
        try:
            with requests.get(url, params=params, headers=HEADERS, timeout=(10, timeout), stream=True) as response:
                response.raise_for_status()
                chunks = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    shared_budget = _RESPONSE_BUDGET.get()
                    if shared_budget is not None:
                        shared_budget.received += len(chunk)
                        if shared_budget.received > shared_budget.maximum:
                            raise SourceUnavailableError('ArcGIS aggregate byte budget exceeded')
                    chunks.extend(chunk)
                    if len(chunks) > 16_000_000:
                        raise SourceUnavailableError('ArcGIS response exceeds 16000000 byte cap; use smaller batches')
                payload = json.loads(chunks)
            if not isinstance(payload, dict):
                raise ValueError(f'ArcGIS response is not an object: {url}')
            if payload.get('error'):
                raise ArcGISError(url, payload['error'])
            return payload
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ArcGISError) as error:
            code = getattr(error, 'code', None) or getattr(getattr(error, 'response', None), 'status_code', None)
            transient = isinstance(error, (requests.Timeout, requests.ConnectionError)) or code in {429, 500, 502, 503, 504}
            if not transient or attempt == 2:
                raise
            time.sleep(0.25 * 2 ** attempt)
    raise AssertionError('unreachable')


def _validate_expected_checksum(source: GovernanceSource, path: Path) -> None:
    if source.expected_sha256 is not None:
        actual = sha256_dataset(path)
        if actual != source.expected_sha256:
            raise ValueError(f'Governance source checksum mismatch for {source.source_id}: expected {source.expected_sha256}, received {actual}.')


def _ids(features, field):
    values = []
    for feature in features:
        props = feature.get('properties', {})
        identity = next((v for k, v in props.items() if k.casefold() == field.casefold()), None)
        if identity is None or isinstance(identity, bool) or not isinstance(identity, int):
            raise ValueError(f'ArcGIS required integer object ID field {field!r} is missing or changed')
        values.append(identity)
    if len(set(values)) != len(values):
        raise SourceUnavailableError('Duplicate object IDs in ArcGIS response')
    return values


def validate_snapshot(source, snapshot, *, bbox=None):
    """Validate identity and completeness, then containment and exact selectors."""
    if snapshot.get('source_id') != source.source_id or snapshot.get('source_url', '').rstrip('/') != source.url.rstrip('/'):
        raise CacheScopeError(f'{source.source_id}: cache provider/layer identity mismatch')
    contract = snapshot.get('request_contract', {})
    if contract.get('provider', source.provider) != source.provider or contract.get('source_as_of', source.source_as_of) != source.source_as_of:
        raise CacheScopeError(f'{source.source_id}: cache source/version mismatch')
    if snapshot.get('selection_where', '1=1') != source.selection_where or snapshot.get('requested_grid_mask_sha256') != source.requested_grid_mask_sha256:
        raise CacheScopeError(f'{source.source_id}: cache selector/mask mismatch')
    if snapshot.get('geometry_roster_complete') is not True:
        raise CacheScopeError(f'{source.source_id}: no verified complete acquisition receipt; reacquire into a new workspace')
    field = snapshot.get('object_id_field') or snapshot.get('metadata_response', {}).get('objectIdField') or 'OBJECTID'
    received = []
    for page in snapshot.get('pages', []):
        received.extend(_ids(page.get('response', {}).get('features', []), field))
    expected = snapshot.get('selected_object_ids')
    if len(set(received)) != len(received) or snapshot.get('unreceived_object_ids'):
        raise CacheScopeError(f'{source.source_id}: duplicate/missing cached object IDs')
    if expected is not None and (len(set(expected)) != len(expected) or set(received) != set(expected)):
        raise CacheScopeError(f'{source.source_id}: cached roster does not reconcile')
    if snapshot.get('expected_object_id_count') != len(received):
        raise CacheScopeError(f'{source.source_id}: cached feature count does not reconcile')
    if bbox is not None and snapshot.get('server_filtered') is not False:
        cached = snapshot.get('requested_bbox_wgs84')
        if cached is None:
            raise CacheScopeError(f'{source.source_id}: cache has unknown spatial support')
        from shapely.ops import unary_union
        cached_shape = unary_union(bbox_parts(validate_bbox(cached)))
        requested_shape = unary_union(bbox_parts(validate_bbox(bbox)))
        if not cached_shape.covers(requested_shape):
            raise CacheScopeError(f'{source.source_id}: cache spatial scope is smaller than request')


def download_arcgis_snapshot(source: GovernanceSource, *, bbox, overwrite=False, budget: AcquisitionBudget | None = None, transfer_budget=None) -> Path:
    bbox = validate_bbox(source.selection_bbox or bbox)
    if source.requested_grid_mask_sha256 is not None:
        raise SourceUnavailableError('Masked acquisition requires explicit qualified mask geometry; a hash alone cannot apply a mask')
    budget = budget or AcquisitionBudget()
    if source.snapshot_path is None:
        raise ValueError(f'ArcGIS source {source.source_id!r} has no snapshot_path')
    destination = source.snapshot_path
    if destination.exists() and not overwrite:
        _validate_expected_checksum(source, destination)
        validate_snapshot(source, json.loads(destination.read_text()), bbox=bbox)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    used_bytes = pages = features_count = 0
    response_budget = transfer_budget or _ResponseBudget(budget.max_bytes)
    starting_bytes = response_budget.received
    def request(url, params):
        nonlocal used_bytes, pages
        pages += 1
        if pages > budget.max_pages:
            raise SourceUnavailableError('ArcGIS request/page budget exceeded')
        previous_bytes = response_budget.received
        token = _RESPONSE_BUDGET.set(response_budget)
        try:
            value = _response_json(url, params=params, timeout=60)
        finally:
            _RESPONSE_BUDGET.reset(token)
        # Offline mocks bypass byte-stream accounting; retain the same aggregate contract.
        if response_budget.received == previous_bytes:
            response_budget.received += len(json.dumps(value).encode())
        used_bytes = response_budget.received - starting_bytes
        if used_bytes > budget.max_bytes:
            raise SourceUnavailableError('ArcGIS aggregate byte budget exceeded')
        return value
    url = source.url.rstrip('/')
    metadata = request(url, {'f': 'json'})
    field = metadata.get('objectIdField') or metadata.get('objectIdFieldName')
    if not field:
        field = next((f['name'] for f in metadata.get('fields', []) if f.get('type') == 'esriFieldTypeOID'), None)
    if not field:
        raise SourceUnavailableError('ArcGIS layer does not declare a stable object ID field')
    size = min(int(metadata.get('maxRecordCount') or 1000), source.page_size or 1000)
    if size <= 0:
        raise ValueError('Invalid service page size')
    selectors = []
    for part in bbox_parts(bbox) if source.server_filter else [None]:
        params = {'where': source.selection_where}
        if part is not None:
            params.update(geometry=','.join(str(v) for v in part.bounds), geometryType='esriGeometryEnvelope', inSR=4326, spatialRel='esriSpatialRelIntersects')
        selectors.append(params)
    query_url = url + '/query'
    roster = set()
    roster_supported = True
    for selector in selectors:
        try:
            receipt = request(query_url, {**selector, 'f': 'json', 'returnIdsOnly': 'true'})
        except ArcGISError as error:
            if error.code != 400:
                raise
            roster_supported = False
            break
        ids = receipt.get('objectIds')
        if not isinstance(ids, list) or receipt.get('exceededTransferLimit') is True:
            raise SourceUnavailableError('ArcGIS ID roster is missing or truncated')
        if len(set(ids)) != len(ids) or any(type(v) is not int for v in ids):
            raise SourceUnavailableError('Duplicate or malformed IDs in expected roster')
        roster.update(ids)
        if len(roster) > budget.max_features:
            raise SourceUnavailableError('ArcGIS feature budget exceeded')
    if not roster_supported and (len(selectors) != 1 or (metadata.get('advancedQueryCapabilities', {}).get('supportsPagination') is not True or metadata.get('advancedQueryCapabilities', {}).get('supportsOrderBy') is not True)):
        raise SourceUnavailableError('Layer supports neither complete ID roster nor qualified pagination')
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.acquisition-') as temporary_dir:
        spool = Path(temporary_dir) / 'pages.jsonl'
        seen = set()
        with spool.open('w') as stream:
            def archive(params, payload):
                nonlocal features_count
                features = payload.get('features')
                if not isinstance(features, list):
                    raise ValueError('ArcGIS features schema drift: expected list')
                ids = _ids(features, field)
                if seen.intersection(ids):
                    raise SourceUnavailableError('Repeated page or duplicate object IDs; acquisition made no progress')
                seen.update(ids)
                features_count += len(ids)
                if features_count > budget.max_features:
                    raise SourceUnavailableError('ArcGIS feature budget exceeded')
                stream.write(json.dumps({'request_params': params, 'retrieved_at_utc': datetime.now(UTC).isoformat(), 'response': payload}) + '\n')
                return ids
            base = {'f': 'geojson', 'outFields': '*', 'returnGeometry': 'true', 'outSR': 4326}
            if roster_supported:
                def batch(ids):
                    params = {**base, 'where': source.selection_where, 'objectIds': ','.join(map(str, ids))}
                    payload = request(query_url, params)
                    returned = _ids(payload.get('features', []), field)
                    if not set(returned).issubset(ids):
                        raise SourceUnavailableError('ArcGIS batch returned unexpected IDs')
                    if set(returned) != set(ids) or payload.get('exceededTransferLimit') is True:
                        if len(ids) <= 1:
                            raise SourceUnavailableError(f'ArcGIS missing/truncated object ID {ids}')
                        midpoint = len(ids)//2
                        batch(ids[:midpoint]); batch(ids[midpoint:])
                    else:
                        archive(params, payload)
                ordered = sorted(roster)
                for start in range(0, len(ordered), size):
                    batch(ordered[start:start+size])
                # Reconcile the selected roster again to catch mutations during acquisition.
                after = set()
                for selector in selectors:
                    receipt = request(query_url, {**selector, 'f': 'json', 'returnIdsOnly': 'true'})
                    if not isinstance(receipt.get('objectIds'), list) or receipt.get('exceededTransferLimit') is True:
                        raise SourceUnavailableError('Final ID receipt is incomplete')
                    if len(set(receipt['objectIds'])) != len(receipt['objectIds']) or any(type(v) is not int for v in receipt['objectIds']):
                        raise SourceUnavailableError('Final roster has duplicate or malformed IDs')
                    after.update(receipt['objectIds'])
                if after != roster or seen != roster:
                    raise SourceUnavailableError('ArcGIS roster changed or geometry IDs are missing')
            else:
                selector = selectors[0]
                count = request(query_url, {**selector, 'f': 'json', 'returnCountOnly': 'true'}).get('count')
                if type(count) is not int or count > budget.max_features:
                    raise SourceUnavailableError('ArcGIS expected count missing or exceeds budget')
                offset = empty_pages = 0
                last_id = None
                while True:
                    params = {**selector, **base, 'orderByFields': field + ' ASC', 'resultRecordCount': size, 'resultOffset': offset}
                    payload = request(query_url, params)
                    returned = archive(params, payload)
                    if returned and (returned != sorted(returned) or (last_id is not None and min(returned) <= last_id)):
                        raise SourceUnavailableError('ArcGIS pagination ordering is unstable')
                    if returned:
                        last_id = max(returned)
                    empty_pages = empty_pages + 1 if not returned else 0
                    if empty_pages > 3:
                        raise SourceUnavailableError('ArcGIS pagination has no progress')
                    if payload.get('exceededTransferLimit') is False:
                        break
                    if 'exceededTransferLimit' not in payload:
                        raise SourceUnavailableError('Pagination completion flag unavailable')
                    # Service offset is the requested record window, not returned spatial hits.
                    offset += size
                final_count = request(query_url, {**selector, 'f': 'json', 'returnCountOnly': 'true'}).get('count')
                if len(seen) != count or final_count != count:
                    raise SourceUnavailableError('ArcGIS paginated count does not reconcile')
                roster = seen
        header = dict(snapshot_schema_version=2, source_id=source.source_id, source_url=source.url,
            request_contract={'provider': source.provider, 'source_as_of': source.source_as_of},
            retrieved_at_utc=datetime.now(UTC).isoformat(), server_filtered=source.server_filter,
            requested_bbox_wgs84=list(bbox), selection_where=source.selection_where,
            requested_grid_mask_sha256=source.requested_grid_mask_sha256,
            metadata_request={'url': url, 'params': {'f':'json'}}, metadata_response=metadata,
            query_url=query_url, object_id_field=field, selected_object_ids=sorted(roster),
            expected_object_id_count=len(roster), unreceived_object_ids=[], geometry_roster_complete=True,
            completeness_method='stable_id_roster' if roster_supported else 'stable_order_count_reconciliation',
            receipt_times_by_page=True, acquisition_budget=vars(budget), response_bytes=used_bytes)
        temporary = Path(temporary_dir) / 'snapshot.json'
        with temporary.open('w') as stream:
            stream.write(json.dumps(header)[:-1] + ', "pages": [')
            with spool.open() as archived:
                for index, line in enumerate(archived):
                    stream.write((',' if index else '') + line.strip())
            stream.write(']}\n')
        _validate_expected_checksum(source, temporary)
        os.replace(temporary, destination)
    return destination


def download_direct_snapshot(source, *, overwrite=False, max_bytes=64_000_000, transfer_budget=None):
    if source.snapshot_path is None:
        raise ValueError(f'Direct source {source.source_id!r} has no snapshot_path')
    destination = source.snapshot_path
    if destination.exists() and not overwrite:
        _validate_expected_checksum(source, destination)
        _validate_direct_receipt(source, destination, bbox=None)
        return destination
    if source.selection_where != '1=1' or source.requested_grid_mask_sha256 is not None:
        raise CacheScopeError(f'{source.source_id}: direct download cannot apply selector/mask')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=destination.parent, prefix='.' + destination.name, suffix='.part')
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            with requests.get(source.url, headers=HEADERS, stream=True, timeout=(10, 60)) as response:
                response.raise_for_status()
                received = 0
                for chunk in response.iter_content(chunk_size=1024*1024):
                    received += len(chunk)
                    if transfer_budget is not None:
                        transfer_budget.received += len(chunk)
                        if transfer_budget.received > transfer_budget.maximum:
                            raise SourceUnavailableError('Aggregate query acquisition byte budget exhausted')
                    if received > (max_bytes or 64_000_000):
                        raise SourceUnavailableError(f'Download exceeds {max_bytes} byte cap: {source.source_id}')
                    stream.write(chunk)
        _validate_expected_checksum(source, temporary)
        # Stage and rollback both members on handled replacement failures. Hash readers
        # reject disagreement after a crash; this remains per-source, not workspace atomicity.
        metadata_path = destination.with_suffix(destination.suffix + '.metadata.json')
        with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.direct-') as directory:
            stage = Path(directory)
            staged_metadata = atomic_write_json(stage / 'metadata.json',
                dict(snapshot_schema_version=2, source_id=source.source_id, source_url=source.url,
                     retrieved_at_utc=datetime.now(UTC).isoformat(), bytes=received, sha256=sha256_file(temporary),
                     archive_member=source.archive_member, archive_layer=source.archive_layer,
                     provider=source.provider, source_as_of=source.source_as_of, full_source_dataset=True,
                     selection_where=source.selection_where, requested_grid_mask_sha256=source.requested_grid_mask_sha256))
            backups = {}
            for index, path in enumerate((destination, metadata_path)):
                if path.exists():
                    backup = stage / f'backup-{index}'
                    shutil.copy2(path, backup)
                    backups[path] = backup
            try:
                os.replace(temporary, destination)
                os.replace(staged_metadata, metadata_path)
            except BaseException:
                for path in (destination, metadata_path):
                    if path in backups:
                        os.replace(backups[path], path)
                    else:
                        path.unlink(missing_ok=True)
                raise
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def acquire_source(config: GovernanceConfig, source_id: str, *, overwrite=False):
    source = config.sources[source_id]
    requested_bbox = source.selection_bbox or config.bbox_tuple
    if source.local_path is not None and source.local_path.exists():
        _validate_expected_checksum(source, source.local_path)
        if source.local_path.suffix.lower() == '.json':
            validate_snapshot(source, json.loads(source.local_path.read_text()), bbox=requested_bbox)
        else:
            _validate_direct_receipt(source, source.local_path, bbox=requested_bbox)
        return source.local_path
    if source.acquisition_type == 'direct_archive':
        return download_direct_snapshot(source, overwrite=overwrite)
    if source.acquisition_type in {'arcgis', 'local_vector_or_arcgis'}:
        return download_arcgis_snapshot(source, bbox=requested_bbox, overwrite=overwrite)
    if source.source_status == 'unavailable' or source.acquisition_type == 'reference_only':
        return None
    raise SourceUnavailableError(f'Unsupported governance acquisition type: {source.acquisition_type}')


def acquire_collection_sources(config, collection_id, *, overwrite=False):
    return [path for sid in config.collections[collection_id].source_ids if (path := acquire_source(config, sid, overwrite=overwrite)) is not None]


def _validate_direct_receipt(source, path, *, bbox):
    receipt_path = path.with_suffix(path.suffix + '.metadata.json')
    if not receipt_path.exists() and not receipt_path.is_symlink():
        if (source.immutable_full_source_archive is True and source.acquisition_type == 'direct_archive'
            and path.suffix.lower() == '.zip' and source.expected_sha256 is not None
            and source.selection_where == '1=1' and source.requested_grid_mask_sha256 is None
            and source.server_filter is False):
            # Verify here as well as in callers: a qualification flag alone is insufficient.
            _validate_expected_checksum(source, path)
            return {}  # Missing retrieval evidence remains unknown; no receipt fabricated.
        raise CacheScopeError(f'{source.source_id}: vector/archive cache lacks a provider/scope/completeness receipt')
    if not receipt_path.is_file():
        raise CacheScopeError(f'{source.source_id}: malformed direct/vector cache receipt')
    try:
        receipt = json.loads(receipt_path.read_text())
    except (ValueError, UnicodeError) as error:
        raise CacheScopeError(f'{source.source_id}: malformed direct/vector cache receipt') from error
    if not isinstance(receipt, dict):
        raise CacheScopeError(f'{source.source_id}: malformed direct/vector cache receipt')
    if receipt.get('sha256') != sha256_dataset(path) or receipt.get('source_id') != source.source_id or receipt.get('source_url') != source.url:
        raise CacheScopeError(f'{source.source_id}: direct/vector cache receipt mismatch')
    if receipt.get('provider', source.provider) != source.provider or receipt.get('source_as_of', source.source_as_of) != source.source_as_of:
        raise CacheScopeError(f'{source.source_id}: direct/vector source/version mismatch')
    if receipt.get('selection_where', '1=1') != source.selection_where or receipt.get('requested_grid_mask_sha256') != source.requested_grid_mask_sha256:
        raise CacheScopeError(f'{source.source_id}: direct/vector selector/mask mismatch')
    if receipt.get('archive_member', source.archive_member) != source.archive_member or receipt.get('archive_layer', source.archive_layer) != source.archive_layer:
        raise CacheScopeError(f'{source.source_id}: direct archive member/layer mismatch')
    if receipt.get('full_source_dataset') is not True:
        if receipt.get('geometry_roster_complete') is not True or receipt.get('requested_bbox_wgs84') is None:
            raise CacheScopeError(f'{source.source_id}: vector support/completeness is unverified')
        if bbox is None:
            raise CacheScopeError(f'{source.source_id}: bounded receipt cannot establish full-source support')
        from shapely.ops import unary_union
        if not unary_union(bbox_parts(receipt['requested_bbox_wgs84'])).covers(unary_union(bbox_parts(bbox))):
            raise CacheScopeError(f'{source.source_id}: vector cache scope is smaller than request')
    return receipt


def read_source_frame(source: GovernanceSource, *, bbox=None) -> gpd.GeoDataFrame:
    # A declared partial selection is an input subset, never a full-AOI receipt.
    # Validate that exact configured scope; geometry outside it remains unknown.
    bbox = source.selection_bbox or bbox
    path = resolve_source_path(source)
    if path is None:
        raise SourceUnavailableError(f'No runtime snapshot is available for {source.source_id}')
    _validate_expected_checksum(source, path)
    if path.suffix.lower() in {'.parquet', '.geoparquet'}:
        import pyarrow.parquet as pq
        metadata = pq.read_schema(path).metadata or {}
        if b'governance_original' in metadata:
            return _read_original_frame(source, path, metadata, bbox=bbox)
    if source.source_id in {'odfw_marine_reserves_2016', 'tc_srkw_interim_order_2026', 'uscg_lockheed_rna_20261015', 'uscg_theafoss_rna_20261015', 'dnd_wg_active_reference_20261020'}:
        receipt = _validate_direct_receipt(source, path, bbox=bbox)
        if source.source_id == 'odfw_marine_reserves_2016':
            from governance.protected_areas.marine_protected_areas.oregon import source_frame
        elif source.source_id == 'dnd_wg_active_reference_20261020':
            from governance.vessel_management.exclusion_zones.nanoose import source_frame
        elif source.source_id == 'uscg_theafoss_rna_20261015':
            from governance.vessel_management.exclusion_zones.theafoss import source_frame
        elif source.source_id == 'uscg_lockheed_rna_20261015':
            from governance.vessel_management.exclusion_zones.washington import source_frame
        else:
            from governance.vessel_management.fixed_rules import source_frame
        frame = source_frame(path)
        frame.attrs['retrieved_at_utc'] = receipt.get('retrieved_at_utc')
        return frame
    if path.suffix.lower() != '.json':
        receipt = _validate_direct_receipt(source, path, bbox=bbox)
        if path.suffix.lower() == '.zip' and source.archive_member and source.archive_layer:
            frame = gpd.read_file(f'/vsizip/{path.resolve()}/{source.archive_member}', layer=source.archive_layer)
        elif path.suffix.lower() == '.zip' and source.archive_member:
            frame = gpd.read_file(f'zip://{path.resolve()}!{source.archive_member}')
        elif path.suffix.lower() in {'.parquet', '.geoparquet'}:
            frame = gpd.read_parquet(path)
        else:
            frame = gpd.read_file(path)
        if frame.crs is None:
            raise ValueError(f'Governance source has no CRS: {path}')
        frame.attrs['retrieved_at_utc'] = receipt.get('retrieved_at_utc')
        return frame.to_crs(4326)
    snapshot = json.loads(path.read_text())
    if snapshot.get('snapshot_schema_version') not in {1, 2}:
        raise ValueError(f'Unsupported governance ArcGIS snapshot: {path}')
    # Raw legacy readers remain usable for migration inspection. Request-aware builds/getters require receipts.
    if bbox is not None or snapshot.get('snapshot_schema_version') == 2:
        validate_snapshot(source, snapshot, bbox=bbox)
    features = [feature for page in snapshot.get('pages', []) for feature in page.get('response', {}).get('features', [])]
    if features:
        frame = gpd.GeoDataFrame.from_features(features, crs=4326)
    else:
        fields = [f['name'] for f in snapshot.get('metadata_response', {}).get('fields', [])]
        frame = gpd.GeoDataFrame(columns=[*fields, 'geometry'], geometry='geometry', crs=4326)
    frame.attrs['retrieved_at_utc'] = snapshot.get('retrieved_at_utc')
    frame.attrs['layer_metadata'] = snapshot.get('metadata_response', {})
    frame.attrs['request_receipt'] = {k: v for k, v in snapshot.items() if k != 'pages'}
    frame.attrs['receipts_by_id'] = {
        str(next((v for k, v in feature.get('properties', {}).items() if k.casefold() == str(snapshot.get('object_id_field', 'OBJECTID')).casefold()), '')): page.get('retrieved_at_utc', snapshot.get('retrieved_at_utc'))
        for page in snapshot.get('pages', []) for feature in page.get('response', {}).get('features', [])}
    return frame


def _read_original_frame(source, path, metadata, *, bbox):
    """Read a checksum-pinned OriginalData dataset with its original scope receipt."""
    original = json.loads(metadata[b'governance_original'])
    record, receipt = original['source'], original['receipt']
    if original.get('schema_version') != 1 or any(record.get(k) != v for k, v in (
        ('source_id', source.source_id), ('provider', source.provider),
        ('url', source.url), ('source_as_of', source.source_as_of))):
        raise CacheScopeError('OriginalData provider/version mismatch')
    if original.get('selection_where') != source.selection_where or original.get('requested_grid_mask_sha256') != source.requested_grid_mask_sha256:
        raise CacheScopeError('OriginalData selector/mask mismatch')
    frame = gpd.read_parquet(path)
    if len(frame) != original['rows'] or frame.crs is None:
        raise CacheScopeError('OriginalData row/CRS mismatch')
    if source.acquisition_type == 'arcgis':
        field = receipt.get('object_id_field', 'OBJECTID')
        actual = next((c for c in frame.columns if c.casefold() == field.casefold()), None)
        if actual is None:
            raise CacheScopeError('OriginalData lacks source object IDs')
        # Reconcile the roster without converting large geometries back to JSON.
        reconstructed = dict(receipt, pages=[{'response': {'features': [
            {'properties': {field: v}} for v in frame[actual].tolist()]}}])
        validate_snapshot(source, reconstructed, bbox=bbox)
    elif receipt.get('full_source_dataset') is not True:
        if receipt.get('geometry_roster_complete') is not True or bbox is None or receipt.get('requested_bbox_wgs84') is None:
            raise CacheScopeError('OriginalData lacks full-source or bounded support')
        from shapely.ops import unary_union
        if not unary_union(bbox_parts(receipt['requested_bbox_wgs84'])).covers(unary_union(bbox_parts(bbox))):
            raise CacheScopeError('OriginalData scope is smaller than request')
    frame.attrs = original['frame_attributes']
    if source.acquisition_type == 'arcgis':
        frame.attrs['request_receipt'] = receipt
        frame.attrs['layer_metadata'] = receipt.get('metadata_response', {})
    return frame.to_crs(4326)
