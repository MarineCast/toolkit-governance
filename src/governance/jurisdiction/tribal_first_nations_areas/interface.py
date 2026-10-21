"""Two map features over retained, source-distinct administrative references.

This combines membership evidence, never polygon areas or legal jurisdictions.
"""
from __future__ import annotations
import json
import pyarrow as pa
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition, validate_memberships

FAMILY = 'tribal_first_nations_areas'
AREA = FAMILY + '__mapped_area'
ASSIGNMENT = FAMILY + '__feature_memberships_v1'
COUNT = FAMILY + '__recorded_feature_count'
COMPONENTS = (FAMILY + '__bia_land_area_reference', FAMILY + '__nrcan_indian_reserve_reference')
SOURCE_CONTEXT = {
    'bia_administrative_lar': {'country': 'United States', 'agency': 'Bureau of Indian Affairs',
        'boundary_type': 'BIA land-area reference',
        'classification': 'Original BIA CLASSIFICATION codes retained undecoded in OriginalData; no inferred legal land class'},
    'nrcan_indian_reserves': {'country': 'Canada', 'agency': 'Natural Resources Canada, Canada Lands Survey System',
        'boundary_type': 'Indian Reserve administrative reference', 'scope': 'British Columbia Indian Reserve records only; Sechelt Land and other classes excluded'},
}
SEMANTICS = ('Positive-area intersection with a received BIA land-area reference or qualified BC NRCan Indian Reserve. '
    'True requires at least one qualifying overlap. False requires verified complete mapped-inventory coverage of every supplied full cell '
    'for both component sources and observed empty memberships; otherwise no-hit support is null (unknown/unavailable). '
    'All overlapping names and source-qualified area/record IDs are retained; no dominant area is chosen. '
    'These are different provider administrative/reserve categories, not Tribes or Nations as entities, sovereign/traditional territories, '
    'ownership, treaty rights or broader legal jurisdiction. Query receipts and national extents do not establish completeness.')
SCIENTIFIC_FEATURES = {AREA: {'display_name': 'Tribal / First Nations Area'},
    ASSIGNMENT: {'display_name': 'Tribal / First Nations Assignment'}}


def _complete(coverage, group):
    """An explicit geographic qualification, separate from source receipt/status.

    Current producer coverage is unknown. A future qualifier must supply evidence
    covering the full cells of this product, not merely a country/selector roster.
    """
    support = coverage.get(group, {}).get('geographic_inventory_coverage', {})
    return (support.get('status') == 'complete' and support.get('scope') == 'full_supplied_cells'
            and isinstance(support.get('evidence'), str) and bool(support['evidence'].strip()))


def _merge(rows):
    features = {}
    for entries in rows:
        for entry in entries or []:
            records = features.setdefault(entry['feature_id'], {})
            for record in entry['records']:
                key = tuple(record[name] for name in RECORD_FIELDS)
                records.setdefault(key, set()).update(record['geometry_part_ids'])
    return [{'feature_id': feature, 'records': [dict(zip(RECORD_FIELDS, key), geometry_part_ids=sorted(parts))
        for key, parts in sorted(records.items(), key=lambda pair: json.dumps(pair[0], ensure_ascii=True))]}
        for feature, records in sorted(features.items())]


def add_features(table, fields, coverage):
    """Derive only this family from validated existing memberships, no re-overlay.

    Idempotent for narrow migration/readback. Component columns remain byte-value
    equivalent. A legacy table without membership evidence gets no invented choices.
    """
    if not any(group + '__feature_memberships_v1' in table.column_names for group in COMPONENTS):
        return table
    validate_memberships(table, fields)
    rows, statuses = [], []
    for group in COMPONENTS:
        name = group + '__feature_memberships_v1'
        rows.append(table[name].to_pylist() if name in table.column_names else [None] * table.num_rows)
        statuses.append(table[name + '_status'].to_pylist() if name in table.column_names else ['unavailable'] * table.num_rows)
    complete = all(_complete(coverage, group) for group in COMPONENTS)
    combined, states, areas = [], [], []
    for i in range(table.num_rows):
        entries = _merge([values[i] for values in rows])
        known_empty = complete and all(values[i] == [] for values in rows) and all(values[i] == 'observed' for values in statuses)
        state = 'observed' if complete and all(values[i] == 'observed' for values in statuses) else 'partial'
        if not entries and not known_empty:
            state = 'unavailable' if all(values[i] == 'unavailable' for values in statuses) else 'unknown' if all(values[i] in ('unknown', 'unavailable', 'not_applicable') for values in statuses) else 'partial'
        combined.append(entries if entries or known_empty else None)
        states.append(state)
        areas.append(True if entries else False if known_empty else None)
    values = {AREA: pa.array(areas, pa.bool_()), AREA + '_status': pa.array(states),
        COUNT: pa.array([None if row is None else len(row) for row in combined], pa.int64()), COUNT + '_status': pa.array(states),
        ASSIGNMENT: pa.array(combined, MEMBERSHIP_TYPE), ASSIGNMENT + '_status': pa.array(states)}
    for name, array in values.items():
        table = table.set_column(table.column_names.index(name), name, array) if name in table.column_names else table.append_column(name, array)
    coverage[FAMILY] = {'component_groups': list(COMPONENTS), 'source_context': SOURCE_CONTEXT,
        'geographic_inventory_coverage': {'status': 'complete' if complete else 'unknown',
            'meaning': 'No absence inferred from source receipts or national extents; see each component qualification'},
        'overlap_policy': 'Combine distinct source-qualified memberships only; do not pool area/territory measures',
        'effect': SEMANTICS}
    fields[AREA] = {'units': '1', 'nullable': True, 'definition': SEMANTICS, 'value_semantics': 'boolean_overlap',
        'missing_reason_field': AREA + '_status', 'coverage_reference': FAMILY}
    fields[COUNT] = {'units': 'count', 'nullable': True, 'definition': 'Distinct source-qualified mapped area IDs across both components; not a count of Tribes or Nations',
        'missing_reason_field': COUNT + '_status', 'coverage_reference': FAMILY}
    fields[ASSIGNMENT] = {**definition(FAMILY), 'definition': SEMANTICS, 'source_context': SOURCE_CONTEXT}
    for name in (AREA, COUNT, ASSIGNMENT):
        fields[name + '_status'] = {'units': None, 'nullable': False, 'definition': 'Combined membership support; does not establish geographic completeness',
            'enum': ['observed', 'unknown', 'unavailable', 'not_applicable', 'partial']}
    for name, field in fields.items():
        if name.startswith(FAMILY + '__'):
            field.update(map_feature=name in SCIENTIFIC_FEATURES)
            field.update(SCIENTIFIC_FEATURES.get(name, {}))
    validate_memberships(table, fields)
    return table
