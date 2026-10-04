"""Single-resolution wide inventory tables and explicit toolkit-local manifests.

Governance is not a quantity_kind in shared manifest 0.1. This envelope therefore
makes no shared-schema conformance claim and does not repurpose another quantity.
"""
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .shared.artifacts import sha256_file

METHOD_VERSION = 'native-inventory-overlay-1.1.0'
METRICS = {
    'FEATURE_COUNT': ('recorded_feature_count', 'count', 'Distinct source-backed feature IDs with positive-dimensional intersections'),
    'POLYGON_COVERAGE_FRAC': ('recorded_polygon_union_area_fraction', '1', 'Unioned polygon intersection area / full H3 cell area, EPSG:6933'),
    'LINE_LENGTH_M': ('recorded_line_union_length_m', 'm', 'Unioned line intersection length in declared metre-based projected CRS'),
    'POINT_COUNT': ('recorded_point_feature_count', 'count', 'Distinct recorded point feature IDs inside/on full H3 cell'),
}
STATES = ['observed', 'unknown', 'unavailable', 'not_applicable', 'partial']


def export_delivery(matrix_path: str | Path, output_directory: str | Path, *,
                    release_id: str, software_revision: str) -> list[Path]:
    """Project a validated overlay into separate resolution tables, retaining lineage.

    The caller must publish the complete output directory as one immutable generation.
    Existing output directories are refused; a failed run is never a published release.
    """
    if not release_id or not re.fullmatch('[0-9a-f]{40}', software_revision):
        raise ValueError('Release identity and full software revision required')
    matrix_path = Path(matrix_path).resolve()
    table = pq.read_table(matrix_path)
    metadata = json.loads(table.schema.metadata[b'governance_h3_matrix'])
    if metadata.get('schema_version') != 1:
        raise ValueError('Unsupported overlay schema')
    keys = table.select(['H3_INDEX', 'H3_RESOLUTION']).to_pandas()
    if keys.empty or keys.isna().any().any() or keys.duplicated().any():
        raise ValueError('Invalid overlay identity')
    import h3
    for cell, resolution in keys.itertuples(index=False, name=None):
        if not h3.is_valid_cell(cell) or h3.get_resolution(cell) != resolution:
            raise ValueError('Invalid H3 identity')
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=False)
    written = []
    for resolution in sorted(set(keys.H3_RESOLUTION)):
        selected = table.filter(pc.equal(table['H3_RESOLUTION'], resolution))
        columns = {'h3_index': selected['H3_INDEX']}
        fields = {'h3_index': {'units': None, 'definition': 'H3 cell identity', 'nullable': False}}
        coverage = {}
        groups = metadata.get('metric_groups') or {name: {'collection': name} for name in metadata['native_manifests']}
        for collection, group in groups.items():
            native_record = metadata['native_manifests'][group['collection']]
            native = native_record['manifest']
            completeness = native.get('source_completeness', 'unknown')
            state = 'observed' if completeness == 'complete' else 'partial' if completeness in ('partial', 'complete_current_noaa_west_coast_sanctuary_roster') else completeness
            if state not in STATES:
                raise ValueError('Invalid completeness')
            records = [s for s in native['sources'] if 'source_id' not in group or s['source_id'] == group['source_id']]
            if not records:
                raise ValueError(f'Metric group has no source lineage: {collection}')
            available = sum(s['runtime_status'] == 'available' for s in records)
            if 'source_id' in group and available == 0:
                state = 'unavailable'
            coverage[collection] = {
                'configured_source_receipt': {'numerator': available, 'denominator': len(records),
                    'unit': 'configured source entries', 'method': 'Count available native-manifest source records / collection configured source records; equal weights',
                    'meaning': 'Input receipt only; NOT geographic completeness or feature recall'},
                'geographic_inventory_coverage': {'numerator': None, 'denominator': None, 'status': 'unknown',
                    'meaning': 'No independently established exhaustive regional feature inventory; no geographic completeness fraction can be inferred'},
                'scope': metadata['grid'], 'native_source_completeness': completeness,
                'component_group': group,
                'metric_support_state': state,
                'overlap_policy': ('Union geometry within this source/role; never add component or source groups as a unique route/scheme total. CHS object LNAM identifies repeated chart records when present; no inference of cross-source identity.' if 'role' in group else 'Established collection-level union across received native geometry; source-backed feature identity counts. Overlapping areas/lines are unioned, not summed.'),
                'gaps': [s['source_id'] for s in records if s['runtime_status'] != 'available'],
                'effect': 'Finite values summarize received records only. Empty intersections and absent geometry types stay null under incomplete support.',
            }
            for original, (suffix, units, definition) in METRICS.items():
                if 'geometry_family' in group:
                    applicable = 'POLYGON_COVERAGE_FRAC' if group['geometry_family'] == 'polygon' else 'LINE_LENGTH_M'
                    if original not in ('FEATURE_COUNT', applicable):
                        continue
                    definition = group['description'] + ': ' + definition + '. ' + group['identity']
                name = f'{collection}__{suffix}'
                values = selected[f'{collection}__{original}']
                statuses = []
                for value in values.to_pylist():
                    if state in ('unavailable', 'not_applicable', 'unknown') and value is not None:
                        raise ValueError(f'Finite value contradicts source status: {name}')
                    statuses.append(state if value is not None or state != 'observed' else 'unknown')
                columns[name] = values
                columns[name + '_status'] = pa.array(statuses)
                fields[name] = {'units': units, 'definition': definition, 'nullable': True,
                                'missing_reason_field': name + '_status', 'coverage_reference': collection,
                                'interpretation': 'Recorded inventory geometry; not law, regulatory compliance, complete jurisdiction or effective-date history'}
                fields[name + '_status'] = {'units': None, 'definition': 'Metric support state; observed means valid derived result', 'nullable': False, 'enum': STATES}
        artifact = output / f'governance-inventory-r{resolution}.parquet'
        pq.write_table(pa.table(columns), artifact, compression='zstd')
        manifest = {
            'governance_delivery_schema_version': 1,
            'shared_contract_conformance': {'status': 'not_claimed_by_local_envelope', 'reason': 'v0.1 has no reference_geometry category. An optional separately validated shared manifest can declare adoption of an explicitly supplied approved extension.'},
            'product_id': f'governance.inventory_geometry_r{resolution}', 'semantic_product_version': '1.1.0',
            'scientific_method_version': METHOD_VERSION, 'software': {'package': 'toolkit-governance', 'version': '0.1.0', 'git_sha': software_revision},
            'data_release_id': release_id, 'created_at_utc': datetime.now(UTC).isoformat(),
            'identity': {'primary_key': ['h3_index'], 'grain': 'One row per supplied cell, static inventory snapshot'},
            'spatial': {'h3_resolution': int(resolution), 'support': 'Full H3 cell', 'grid': metadata['grid'],
                        'area_crs': metadata['area_crs'], 'length_crs': metadata['length_crs']},
            'temporal': {'type': 'static', 'meaning': metadata['temporal_support']},
            'fields': fields, 'coverage': coverage, 'model_eligible': False, 'readiness': 'research_only',
            'native_manifests': metadata['native_manifests'], 'configuration_hash': metadata['config_hash'],
            'overlay': {'path': str(matrix_path), 'sha256': sha256_file(matrix_path)},
            'artifact': {'path': artifact.name, 'format': 'parquet', 'sha256': sha256_file(artifact), 'row_count': selected.num_rows},
            'limitations': ['Retained snapshots do not establish current law or legal effective dates.',
                            'Partial source receipt and unknown geographic coverage are distinct.',
                            'Attribute relations remain in native companion records; no inferred legal authority.',
                            'No antimeridian support; resolution is preserved from the explicit supplied grid.'],
        }
        companion = artifact.with_suffix('.manifest.json')
        companion.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n')
        validate_delivery(artifact, companion)
        written.extend([artifact, companion])
    return written


def validate_delivery(artifact: str | Path, manifest_path: str | Path) -> dict:
    """Verify round-trip identity, checksums and per-metric value/status associations."""
    import h3
    import math
    artifact = Path(artifact)
    manifest = json.loads(Path(manifest_path).read_text())
    if sha256_file(artifact) != manifest['artifact']['sha256']:
        raise ValueError('Delivery artifact checksum mismatch')
    table = pq.read_table(artifact)
    if table.num_rows != manifest['artifact']['row_count'] or set(table.column_names) != set(manifest['fields']):
        raise ValueError('Delivery shape mismatch')
    cells = table['h3_index'].to_pylist()
    resolution = manifest['spatial']['h3_resolution']
    if not cells or len(set(cells)) != len(cells) or any(not h3.is_valid_cell(c) or h3.get_resolution(c) != resolution for c in cells):
        raise ValueError('Delivery H3 keys/resolution mismatch')
    for name, field in manifest['fields'].items():
        if 'missing_reason_field' not in field:
            continue
        for value, status in zip(table[name].to_pylist(), table[field['missing_reason_field']].to_pylist()):
            if status not in STATES or (status == 'observed' and value is None):
                raise ValueError(f'Invalid status for {name}')
            if status in ('unknown', 'unavailable', 'not_applicable') and value is not None:
                raise ValueError(f'Non-null missing value for {name}')
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f'Invalid metric value for {name}')
            if 'area_fraction' in name and value is not None and value > 1:
                raise ValueError('Invalid area fraction')
    return {'rows': len(cells), 'resolution': resolution, 'sha256': manifest['artifact']['sha256'], 'status': 'passed'}
