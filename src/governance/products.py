"""Flat H3 metric Parquets, original dataset geometry, and a small update catalog.

Native intermediate products exist only in temporary build storage. Public outputs
have no releases, generation directories, pointers, or manifest sidecars.
"""
from __future__ import annotations

import importlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from datetime import UTC, datetime

import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import yaml

from .delivery import METHOD_VERSION, STATES, project_delivery
from .shared.acquisition import read_source_frame, resolve_source_path
from .shared.artifacts import load_manifest, sha256_dataset, sha256_file, source_record
from .shared.config import DEFAULT_CONFIG_PATH, load_governance_config

METADATA_KEY = b'governance'
ORIGINAL_KEY = b'governance_original'


def _json(value):
    return json.dumps(value, sort_keys=True, default=str, allow_nan=False).encode()


def _member(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or Path(name).is_absolute():
        raise ValueError('Catalog path escapes data directory')
    return path


def validate_metric_table(table, metadata):
    """Check identity, declared metric units/statuses and actual temporal grain."""
    if metadata.get('schema_version') != 1 or metadata.get('model_eligible') is not False:
        raise ValueError('Unsupported governance product metadata')
    resolution = metadata['spatial']['h3_resolution']
    cells = table['h3_index'].to_pylist()
    if not cells or any(not isinstance(c, str) or not h3.is_valid_cell(c) or h3.get_resolution(c) != resolution for c in cells):
        raise ValueError('Invalid H3 identity/resolution')
    if set(table.column_names) != set(metadata['fields']):
        raise ValueError('Metric fields do not match embedded definitions')
    keys = ['h3_index']
    if metadata['temporal']['type'] == 'dynamic':
        if 'date' not in table.column_names or not (pa.types.is_date(table['date'].type) or pa.types.is_timestamp(table['date'].type)) or table['date'].null_count:
            raise ValueError('Dynamic data requires a non-null typed date column')
        keys.append('date')
    elif metadata['temporal']['type'] != 'static' or 'date' in table.column_names:
        raise ValueError('Static data has no date column')
    if table.select(keys).to_pandas().duplicated().any():
        raise ValueError('Duplicate metric row identity')
    for name, field in metadata['fields'].items():
        if 'missing_reason_field' not in field:
            continue
        if field.get('units') not in ('1', 'm', 'count'):
            raise ValueError('Missing or unsupported metric units')
        if field['units'] == 'count' and not pa.types.is_integer(table[name].type):
            raise ValueError('Count metrics require integer columns')
        for value, status in zip(table[name].to_pylist(), table[field['missing_reason_field']].to_pylist()):
            if status not in STATES or (status == 'observed' and value is None):
                raise ValueError(f'Invalid metric status: {name}')
            if status in ('unknown', 'unavailable', 'not_applicable') and value is not None:
                raise ValueError(f'Missing metric must be null: {name}')
            if value is not None and (not math.isfinite(value) or value < 0 or (field['units'] == '1' and value > 1)):
                raise ValueError(f'Invalid metric value: {name}')


def validate_products(directory):
    """Validate the flat catalog and embedded contracts without a release record."""
    root = Path(directory).resolve()
    catalog = json.loads((root / 'catalog.json').read_text())
    if catalog.get('schema_version') != 1 or catalog.get('domain') != 'governance' or not catalog.get('tables'):
        raise ValueError('Unsupported data catalog')
    expected = {'catalog.json'}
    for resolution, variants in catalog['tables'].items():
        if not variants or set(variants).difference({'static', 'dynamic'}):
            raise ValueError('At most static and dynamic tables per resolution')
        for kind, binding in variants.items():
            name = f'governance-r{int(resolution)}-{kind}.parquet'
            if binding['path'] != name:
                raise ValueError('Unexpected metric filename')
            path = _member(root, name)
            if sha256_file(path) != binding['sha256']:
                raise ValueError('Metric checksum mismatch')
            table = pq.read_table(path)
            metadata = json.loads(table.schema.metadata[METADATA_KEY])
            validate_metric_table(table, metadata)
            if table.num_rows != binding['rows'] or metadata['spatial']['h3_resolution'] != int(resolution) or metadata['temporal']['type'] != kind:
                raise ValueError('Catalog/table grain mismatch')
            if metadata['original_data'] != catalog['original_data'] or set(metadata['collections']) != set(catalog['areas']):
                raise ValueError('Catalog/original lineage mismatch')
            expected.add(name)
    for source_id, binding in catalog['original_data'].items():
        name = f'OriginalData/{source_id}/geometry.parquet'
        if binding['path'] != name:
            raise ValueError('Unexpected original dataset filename')
        path = _member(root, name)
        if sha256_file(path) != binding['sha256']:
            raise ValueError('Original geometry checksum mismatch')
        schema = pq.read_schema(path)
        original = json.loads(schema.metadata[ORIGINAL_KEY])
        if original['source']['source_id'] != source_id or pq.read_metadata(path).num_rows != binding['rows'] or b'geo' not in schema.metadata:
            raise ValueError('Original dataset identity/geometry mismatch')
        expected.add(name)
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError('Unexpected or missing files in flat data directory')
    return {'status': 'passed', 'tables': sum(map(len, catalog['tables'].values())), 'original_datasets': len(catalog['original_data'])}


def _write_originals(config, output):
    bindings, sources = {}, {}
    # Shared sources (routing, TC, NRCan) are written only once.
    ids = sorted({s for c in config.collections.values() for s in c.source_ids})
    for source_id in ids:
        source = config.sources[source_id]
        raw = resolve_source_path(source)
        record = source_record(source, raw)
        record.pop('snapshot_path', None)
        sources[source_id] = record
        if raw is None:
            continue
        frame = read_source_frame(source, bbox=config.bbox_tuple)
        print(f'Original dataset {source_id}: {len(frame):,} features', flush=True)
        attrs = frame.attrs.copy()
        if raw.suffix.lower() in ('.parquet', '.geoparquet') and ORIGINAL_KEY in (pq.read_schema(raw).metadata or {}):
            original = json.loads(pq.read_schema(raw).metadata[ORIGINAL_KEY])
            record = original['source']
            sources[source_id] = record
            receipt = original['receipt']
        elif raw.suffix.lower() == '.json':
            receipt = attrs.get('request_receipt', {})
        else:
            receipt_path = raw.with_suffix(raw.suffix + '.metadata.json')
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'full_source_dataset': True, 'retrieved_at_utc': None, 'qualification': 'verified configured immutable full-source archive'}
        destination = output / f'OriginalData/{source_id}/geometry.parquet'
        destination.parent.mkdir(parents=True)
        # Frame attrs contain large ID receipts; store them once in Parquet metadata.
        frame.attrs = {}
        frame.to_parquet(destination, index=False, compression='zstd')
        table = pq.read_table(destination)
        original = {'schema_version': 1, 'source': record, 'receipt': receipt,
                    'frame_attributes': {k: v for k, v in attrs.items() if k not in ('request_receipt', 'layer_metadata')},
                    'selection_where': source.selection_where,
                    'requested_grid_mask_sha256': source.requested_grid_mask_sha256,
                    'geometry_support': 'Original retrieved feature extents, before toolkit clipping; source query selection still applies',
                    'crs': 'EPSG:4326', 'rows': len(frame)}
        pq.write_table(table.replace_schema_metadata({**table.schema.metadata, ORIGINAL_KEY: _json(original)}), destination, compression='zstd')
        restored = gpd.read_parquet(destination)
        if list(restored.columns) != list(frame.columns) or restored.geometry.to_wkb().tolist() != frame.geometry.to_wkb().tolist():
            raise ValueError(f'Original geometry readback mismatch: {source_id}')
        # Arrow independently checks every original attribute, including nulls.
        if not table.equals(pq.read_table(destination), check_metadata=False):
            raise ValueError(f'Original attribute readback mismatch: {source_id}')
        bindings[source_id] = {'path': str(destination.relative_to(output)), 'sha256': sha256_file(destination),
                               'rows': len(frame), 'retrieved_at_utc': attrs.get('retrieved_at_utc')}
    return bindings, sources


def cleanup_workspace_data(output_directory, *, config_path=DEFAULT_CONFIG_PATH, protected_paths=()):
    """Remove disposable workspace data only after verifying retained originals.

    A shared workspace, symlink, unretained source or protected input keeps the
    entire directory intact. Custom caches outside workspace/data are untouched.
    """
    config = load_governance_config(config_path)
    root = config.document.workspace / 'data'
    output = Path(output_directory).resolve()
    validate_products(output)
    if not root.exists() and not root.is_symlink():
        return False

    def keep(reason):
        print(f'Kept workspace data {root}: {reason}', flush=True)
        return False

    if root.is_symlink():
        return keep('contains a symbolic link')
    entries = list(root.rglob('*'))
    if any(p.is_symlink() for p in entries):
        return keep('contains a symbolic link')
    protected = [output, *config.document.include_chain, config.common_config_path,
                 config.catalog_path, config.presentation_config_path, *protected_paths]
    if any(Path(p).resolve().is_relative_to(root) for p in protected):
        return keep('contains output, configuration or a protected build input')
    catalog = json.loads((output / 'catalog.json').read_text())
    retained = {}
    for source_id, binding in catalog['original_data'].items():
        metadata = pq.read_schema(_member(output, binding['path'])).metadata
        retained[source_id] = json.loads(metadata[ORIGINAL_KEY])
    allowed = set()
    for source_id, source in config.sources.items():
        for candidate in (source.local_path, source.snapshot_path):
            if candidate is None or not candidate.exists() or not candidate.is_relative_to(root):
                continue
            original = retained.get(source_id, {})
            if original.get('source', {}).get('snapshot_sha256') != sha256_dataset(candidate):
                return keep(f'source {source_id} is not retained in the validated output')
            receipt = candidate.with_suffix(candidate.suffix + '.metadata.json')
            if receipt.exists():
                if candidate.suffix.lower() == '.json' or json.loads(receipt.read_text()) != original.get('receipt'):
                    return keep(f'acquisition metadata for {source_id} is not retained in the validated output')
                allowed.add(receipt)
            if candidate.is_dir():
                allowed.update(p for p in candidate.rglob('*') if p.is_file())
            elif candidate.suffix.lower() == '.shp':
                allowed.update(candidate.parent.glob(f'{candidate.stem}.*'))
            else:
                allowed.add(candidate)
    for path in entries:
        if path.is_file() and path.name != '.DS_Store' and path not in allowed:
            if not (config.processed_root == root / 'processed/domain/governance'
                    and path.is_relative_to(config.processed_root)):
                return keep(f'unrecognized file {path.relative_to(root)}')
        elif not path.is_file() and not path.is_dir():
            return keep(f'unrecognized entry {path.relative_to(root)}')
    shutil.rmtree(root)
    print(f'Removed workspace data {root}; originals are retained in {output}', flush=True)
    return True


def export_products(matrix_path, output_directory, *, config_path=DEFAULT_CONFIG_PATH,
                    software_revision=None, overwrite=False):
    """Write one static metric Parquet per supplied resolution and original shapes.

    All values use the existing overlay calculation. No effective-date history is
    inferred from a static source inventory. Replacement is staged, validated, and
    rolled back on handled installation errors; readers also check catalog hashes.
    """
    config = load_governance_config(config_path)
    if software_revision is not None and not re.fullmatch('[0-9a-f]{40}', software_revision):
        raise ValueError('Software revision must be a full lowercase Git SHA')
    output = Path(output_directory).resolve()
    inputs = [Path(matrix_path).resolve(), config.path.resolve(), config.common_config_path.resolve()]
    if any(p == output or p.is_relative_to(output) for p in inputs):
        raise ValueError('Output cannot contain or replace input data')
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    if output.exists():
        validate_products(output)
    for source in config.sources.values():
        raw = resolve_source_path(source)
        if raw and raw.resolve().is_relative_to(output):
            if raw.suffix.lower() != '.parquet' or ORIGINAL_KEY not in (pq.read_schema(raw).metadata or {}):
                raise ValueError('Output cannot replace raw source inputs')
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / f'.{output.name}.update.lock'
    with lock.open('x'):
        pass
    staging = Path(tempfile.mkdtemp(prefix=f'.{output.name}.build-', dir=output.parent))
    backup = staging.with_name(staging.name + '.previous')
    try:
        table = pq.read_table(matrix_path)
        overlay = json.loads(table.schema.metadata[b'governance_h3_matrix'])
        if overlay.get('schema_version') != 1:
            raise ValueError('Unsupported overlay schema')
        if overlay.get('config_hash') != config.config_hash or set(overlay['native_manifests']) != set(config.collections):
            raise ValueError('Overlay configuration/collection mismatch')
        for name, collection in config.collections.items():
            binding = overlay['native_manifests'][name]
            if sha256_file(collection.manifest_path) != binding['manifest_sha256'] or load_manifest(collection.manifest_path) != binding['manifest']:
                raise ValueError('Overlay native input mismatch')
            for record in binding['manifest']['sources']:
                raw = resolve_source_path(config.sources[record['source_id']])
                if (raw is None) != (record['runtime_status'] != 'available') or (raw is not None and sha256_dataset(raw) != record['snapshot_sha256']):
                    raise ValueError('Overlay original source mismatch')
        keys = table.select(['H3_INDEX', 'H3_RESOLUTION']).to_pandas()
        if keys.empty or keys.isna().any().any() or keys.duplicated().any():
            raise ValueError('Invalid overlay identity')
        originals, sources = _write_originals(config, staging)
        updated = datetime.now(UTC).replace(microsecond=0).isoformat()
        catalog = {'schema_version': 1, 'domain': 'governance', 'last_updated_utc': updated,
                   'areas': {n: {'last_updated_utc': updated} for n in config.collections},
                   'tables': {}, 'original_data': originals}
        for resolution in sorted(set(keys.H3_RESOLUTION)):
            selected = table.filter(pc.equal(table['H3_RESOLUTION'], int(resolution)))
            product, envelope = project_delivery(selected, overlay, int(resolution), software_revision)
            metadata = {key: envelope[key] for key in ('fields', 'coverage', 'spatial', 'temporal', 'software', 'limitations')}
            metadata.update(schema_version=1, domain='governance', last_updated_utc=updated,
                            scientific_method_version=METHOD_VERSION, model_eligible=False,
                            readiness='research_only', sources=sources, configuration_hash=config.config_hash,
                            original_data=originals,
                            collections={n: {'source_ids': list(c.source_ids), 'normalization_profile': c.normalization_profile,
                                             'native_method': overlay['native_manifests'][n]['manifest'].get('scientific_method_version'),
                                             'clipping': overlay['native_manifests'][n]['manifest'].get('clipping')}
                                         for n, c in config.collections.items()})
            metadata['spatial']['grid'].pop('path', None)
            metadata['temporal']['meaning'] = 'Static recorded inventory; source dates and receipt times remain in OriginalData, not a legal history'
            metadata['limitations'] = [s.replace('Attribute relations remain in native companion records', 'Source attributes remain in OriginalData') for s in metadata['limitations']]
            validate_metric_table(product, metadata)
            name = f'governance-r{int(resolution)}-static.parquet'
            destination = staging / name
            pq.write_table(product.replace_schema_metadata({METADATA_KEY: _json(metadata)}), destination, compression='zstd')
            if not product.equals(pq.read_table(destination), check_metadata=False):
                raise ValueError('Metric readback mismatch')
            catalog['tables'][str(int(resolution))] = {'static': {'path': name, 'sha256': sha256_file(destination), 'rows': product.num_rows}}
        (staging / 'catalog.json').write_bytes(_json(catalog) + b'\n')
        validate_products(staging)
        if output.exists():
            output.rename(backup)
        try:
            staging.rename(output)
        except BaseException:
            if backup.exists():
                backup.rename(output)
            raise
        shutil.rmtree(backup, ignore_errors=True)
        return output
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        lock.unlink(missing_ok=True)


def build_products(grid_paths, output_directory, *, config_path=DEFAULT_CONFIG_PATH,
                   original_data=None, length_crs='EPSG:32610', allow_partial=False,
                   software_revision=None, overwrite=False, keep_workspace_data=False):
    """Build flat data offline, cleaning disposable workspace data after success.

    Inputs are explicit H3 grids and qualified local agency snapshots, or a prior
    flat OriginalData catalog. Acquisition remains a separate explicit operation.
    Failed builds preserve source caches. Set keep_workspace_data to retain them
    after success as well; temporary native/overlay files are always removed.
    """
    from .h3_matrix import export_h3_matrix
    from .shared.grid import read_grid
    grid_paths = list(grid_paths)
    config = load_governance_config(config_path)
    output = Path(output_directory).resolve()
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    original_root = Path(original_data).resolve() if original_data else None
    original_catalog = None
    if original_root:
        validate_products(original_root)
        original_catalog = json.loads((original_root / 'catalog.json').read_text())
    with tempfile.TemporaryDirectory(prefix='governance-build-') as temporary:
        work = Path(temporary)
        values = dict(config.document.data)
        values['common_config_path'] = str(config.common_config_path)
        values['catalog_path'] = str(config.catalog_path)
        values['inspection'] = dict(values['inspection'], presentation_config_path=str(config.presentation_config_path))
        values['output'] = {'processed_root': str(work / 'native'), 'coverage_matrix_path': str(work / 'coverage.json')}
        values['collections'] = {n: dict(values['collections'][n], artifact_path=str(work / 'native' / n / 'geometry.parquet'),
                                        manifest_path=str(work / 'native' / n / 'manifest.json')) for n in config.collections}
        values['sources'] = {n: dict(v) for n, v in values['sources'].items()}
        for name, source in config.sources.items():
            v = values['sources'][name]
            if original_catalog is not None and name in original_catalog['original_data']:
                binding = original_catalog['original_data'][name]
                v.update(local_path=str(_member(original_root, binding['path'])), snapshot_path=None,
                         expected_sha256=binding['sha256'], immutable_full_source_archive=False)
            elif original_catalog is not None:
                v.update(local_path=None, snapshot_path=None)
            else:
                v.update(local_path=str(source.local_path) if source.local_path else None,
                         snapshot_path=str(source.snapshot_path) if source.snapshot_path else None)
        staged_config = work / 'governance.yaml'
        staged_config.write_text(yaml.safe_dump(values))
        for name, collection in config.collections.items():
            print(f'Normalize {name}', flush=True)
            module = importlib.import_module(f'governance.{collection.category}.{name}.build')
            module.build(staged_config, allow_partial=allow_partial)
        grids = [read_grid(p) for p in grid_paths]
        combined = pa.concat_tables([pa.table({'H3_INDEX': g.H3_INDEX, 'H3_RESOLUTION': g.H3_RESOLUTION}) for g in grids])
        grid = work / 'grid.parquet'
        pq.write_table(combined, grid)
        matrix = work / 'metrics.parquet'
        export_h3_matrix(grid, matrix, config_path=staged_config, length_crs=length_crs,
                         allow_partial=allow_partial, include_attributes=False)
        result = export_products(matrix, output, config_path=staged_config,
                                 software_revision=software_revision, overwrite=overwrite)
    if not keep_workspace_data:
        protected = [*grid_paths, *([original_root] if original_root else [])]
        cleanup_workspace_data(result, config_path=config.path, protected_paths=protected)
    return result
