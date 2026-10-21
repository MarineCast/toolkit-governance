"""Project native overlay metrics into per-resolution tables and metadata."""
from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa

from . import __version__
from .memberships import SUFFIX, definition as membership_definition, validate_memberships

METHOD_VERSION = 'native-inventory-overlay-1.3.0'
METRICS = {
    'FEATURE_COUNT': ('recorded_feature_count', 'count', 'Distinct source-backed feature IDs with positive-dimensional intersections'),
    'POLYGON_COVERAGE_FRAC': ('recorded_polygon_union_area_fraction', '1', 'Unioned polygon intersection area / full H3 cell area, EPSG:6933'),
    'LINE_LENGTH_M': ('recorded_line_union_length_m', 'm', 'Unioned line intersection length in declared metre-based projected CRS'),
    'POINT_COUNT': ('recorded_point_feature_count', 'count', 'Distinct recorded point feature IDs inside/on full H3 cell'),
}
STATES = ['observed', 'unknown', 'unavailable', 'not_applicable', 'partial']


def project_delivery(selected: pa.Table, metadata: dict, resolution: int, software_revision: str | None = None) -> tuple[pa.Table, dict]:
    """Project metrics and statuses without writing companions or release records."""
    columns = {'h3_index': selected['H3_INDEX']}
    fields = {'h3_index': {'units': None, 'definition': 'H3 cell identity', 'nullable': False}}
    coverage = {}
    groups = metadata.get('metric_groups') or {name: {'collection': name} for name in metadata['native_manifests']}
    for collection, group in groups.items():
        if group['collection'] == 'ports':
            continue  # Physical port locations now belong to toolkit-human.
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
            'overlap_policy': group.get('overlap_policy', ('Union geometry within this source/role; never add component or source groups as a unique route/scheme total. CHS object LNAM identifies repeated chart records when present; no inference of cross-source identity.' if 'role' in group else 'Established collection-level union across received native geometry; source-backed feature identity counts. Overlapping areas/lines are unioned, not summed.')),
            'gaps': [s['source_id'] for s in records if s['runtime_status'] != 'available'],
            'effect': 'Finite values summarize received records only. Empty intersections and absent geometry types stay null under incomplete support.',
        }
        for original, (suffix, units, definition) in METRICS.items():
            if f'{collection}__{original}' not in selected.column_names:
                continue  # Production computes membership/count support only.
            if collection == 'management_areas' and original != 'FEATURE_COUNT':
                continue
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
        membership_key = f'{collection}__FEATURE_MEMBERSHIPS_V1'
        if membership_key in selected.column_names:
            name = f'{collection}__{SUFFIX}'
            columns[name] = selected[membership_key]
            columns[name + '_status'] = columns[f'{collection}__recorded_feature_count_status']
            fields[name] = membership_definition(collection)
            fields[name + '_status'] = {'units': None, 'definition': 'Same support state as the distinct feature count', 'nullable': False, 'enum': STATES}
    from .protected_areas.wildlife_refuges.interface import annotate_fields
    annotate_fields(fields)
    from .protected_areas.critical_habitat.interface import annotate_fields as annotate_habitat
    annotate_habitat(fields)
    from .vessel_management.exclusion_zones.interface import annotate_fields as annotate_exclusions
    annotate_exclusions(fields)
    from .jurisdiction.tribal_first_nations_areas.interface import add_features
    projected = add_features(pa.table(columns), fields, coverage)
    from .jurisdiction.water_assignments import add_features as add_water_assignments
    projected = add_water_assignments(projected, fields, coverage)
    from .jurisdiction.international_boundary import populate_features as add_boundary
    projected = add_boundary(projected, {'fields': fields, 'coverage': coverage}, None)
    from .jurisdiction.county_regional_boundaries.interface import compact_features
    projected = compact_features(projected, fields, coverage)
    from .fisheries_management.management_areas.interface import compact_features as compact_management
    projected = compact_management(projected, fields, coverage)
    from .administrative_context.coast_guard_sectors.interface import compact_features as compact_coast_guard
    projected = compact_coast_guard(projected, fields, coverage)
    from .vessel_management.presentation import add_features as add_routing
    projected = add_routing(projected, fields, coverage)
    from .jurisdiction.presentation import annotate_fields as annotate_administrative
    annotate_administrative(fields)
    manifest = {
        'governance_delivery_schema_version': 1,
        'shared_contract_conformance': {'status': 'not_claimed_by_local_envelope', 'reason': 'v0.1 has no reference_geometry category. An optional separately validated shared manifest can declare adoption of an explicitly supplied approved extension.'},
        'product_id': f'governance.inventory_geometry_r{resolution}', 'semantic_product_version': '1.3.0',
        'scientific_method_version': METHOD_VERSION, 'software': {'package': 'toolkit-governance', 'version': __version__, 'git_sha': software_revision},
        'created_at_utc': datetime.now(UTC).isoformat(),
        'identity': {'primary_key': ['h3_index'], 'grain': 'One row per supplied cell, static inventory snapshot'},
        'spatial': {'h3_resolution': int(resolution), 'support': 'Full H3 cell', 'grid': metadata['grid'],
                    'area_crs': metadata['area_crs'], 'length_crs': metadata['length_crs']},
        'temporal': {'type': 'static', 'meaning': metadata['temporal_support']},
        'fields': fields, 'coverage': coverage, 'model_eligible': False, 'readiness': 'research_only',
        'native_manifests': metadata['native_manifests'], 'configuration_hash': metadata['config_hash'],


        'limitations': ['Retained snapshots do not establish current law or legal effective dates.',
                        'Partial source receipt and unknown geographic coverage are distinct.',
                        'Paired categorical memberships retain source records and native part lineage; no inferred legal authority.',
                        'No antimeridian support; resolution is preserved from the explicit supplied grid.'],
    }
    validate_memberships(projected, fields)
    return projected, manifest
