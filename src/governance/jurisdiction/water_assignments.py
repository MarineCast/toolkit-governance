"""One categorical map interface per water family; no jurisdiction inferred from lines.

Only an explicitly qualified polygon membership can enter an assignment. Current
sources have no such qualification; their scientific diagnostics remain intact.
"""
from __future__ import annotations
import json
import pyarrow as pa
from governance.memberships import MEMBERSHIP_TYPE, definition, validate_memberships

FAMILIES = {
    'state_provincial_waters': {
        'display_name': 'State / Province Assignment',
        'categories': {'WA': 'Washington (WA)', 'BC': 'British Columbia (BC)', 'OR': 'Oregon (OR)'},
        'boundary_types': ('state_water_polygon', 'provincial_water_polygon', 'geographic_state_water_polygon', 'geographic_province_water_polygon'),
        'gap': 'WA, BC and OR assignments unavailable: BOEM supplies unassigned state-seaward lines only. Country-water support and Canadian country areas/limit lines do not define state/province waters.',
    },
    'federal_waters': {
        'display_name': 'Federal Water Assignment',
        'categories': {'USA': 'United States', 'CAN': 'Canada', 'INT': 'International'},
        'boundary_types': ('federal_administrative_water_polygon', 'high_seas_polygon', 'geographic_country_water_polygon'),
        'gap': 'Federal assignments unavailable: NOAA territorial-sea, contiguous-zone and EEZ limits and Canadian archived EEZ references are lines. No federal administrative-water or high-seas polygons are qualified. International occurrence is unresolved.',
    },
}


def assignment_group(family):
    return family + '__assignment'


def scientific_features(family):
    fields = {assignment_group(family) + '__feature_memberships_v1': {'display_name': FAMILIES[family]['display_name']}}
    if family == 'federal_waters':
        fields['federal_waters__international_boundary'] = {'display_name': 'International Boundary'}
    return fields


def normalize_country(value):
    key = str(value or '').strip().upper().replace('_', ' ')
    return {'US': 'USA', 'USA': 'USA', 'UNITED STATES': 'USA', 'UNITED STATES OF AMERICA': 'USA',
            'CA': 'CAN', 'CAN': 'CAN', 'CANADA': 'CAN'}.get(key)


def category(family, record):
    """Use explicit typed country/region evidence, never names or nearby land."""
    spec = FAMILIES[family]
    if record['feature_type'] not in spec['boundary_types']:
        return None
    country = normalize_country(record['jurisdiction'])
    if family == 'federal_waters':
        if record['feature_type'] == 'high_seas_polygon':
            return 'INT' if str(record['jurisdiction'] or '').strip().upper() == 'INTERNATIONAL' else None
        return country
    region = str(record['region'] or '').strip().upper().replace('_', ' ')
    code = {'WASHINGTON': 'WA', 'WA': 'WA', 'US-WA': 'WA', 'OREGON': 'OR', 'OR': 'OR', 'US-OR': 'OR',
            'BRITISH COLUMBIA': 'BC', 'BC': 'BC', 'CA-BC': 'BC'}.get(region)
    return code if (country, code) in {('USA', 'WA'), ('USA', 'OR'), ('CAN', 'BC')} else None


def _qualified(family, fields):
    """A future source acceptance must explicitly certify polygon semantics.

    These product metadata are written by the producer after source acceptance,
    never synthesized by the explorer. Current line/country sources lack them.
    """
    name = family + '__feature_memberships_v1'
    q = fields.get(name, {}).get('water_assignment_qualification', {})
    definition_key = 'state_province_water_jurisdiction' if family == 'state_provincial_waters' else 'federal_administrative_waters_and_high_seas_beyond_national_jurisdiction'
    return (q.get('geometry_support') == 'positive_area_water_polygons' and q.get('jurisdiction_definition') == definition_key
            and isinstance(q.get('evidence'), str) and bool(q['evidence'].strip())
            and isinstance(q.get('source_dataset_ids'), list) and bool(q['source_dataset_ids'])), q


def add_features(table, fields, coverage):
    """Add separate assignment columns; preserve every original value and record."""
    validate_memberships(table, fields)
    for family, spec in FAMILIES.items():
        if not any(name.startswith(family + '__') for name in table.column_names):
            continue
        group = assignment_group(family)
        name, count = group + '__feature_memberships_v1', group + '__recorded_feature_count'
        source = family + '__feature_memberships_v1'
        qualified, q = _qualified(family, fields)
        rows = table[source].to_pylist() if qualified and source in table.column_names else [None] * table.num_rows
        source_states = table[source + '_status'].to_pylist() if qualified and source in table.column_names else ['unavailable'] * table.num_rows
        geo = coverage.get(family, {}).get('geographic_inventory_coverage', {})
        complete = qualified and geo.get('status') == 'complete' and geo.get('scope') == 'full_supplied_cells' and bool(geo.get('evidence'))
        combined, states = [], []
        for entries, state in zip(rows, source_states):
            selected = []
            for entry in entries or []:
                records = [r for r in entry['records'] if r['source_dataset_id'] in q.get('source_dataset_ids', []) and category(family, r)]
                if records:
                    selected.append(dict(entry, records=records))
            known_empty = complete and entries == [] and state == 'observed'
            combined.append(selected if selected or known_empty else None)
            states.append(('observed' if complete and state == 'observed' else 'partial') if selected else 'observed' if known_empty else 'unknown' if qualified else 'unavailable')
        values = {name: pa.array(combined, MEMBERSHIP_TYPE), name + '_status': pa.array(states),
                  count: pa.array([None if row is None else len(row) for row in combined], pa.int64()), count + '_status': pa.array(states)}
        for column, value in values.items():
            table = table.set_column(table.column_names.index(column), column, value) if column in table.column_names else table.append_column(column, value)
        semantics = ('All positive-area qualified water-polygon memberships; preserve overlapping source-qualified IDs, paired source records and part lineage. '
                     'No dominant assignment. Null means unresolved or unavailable support; empty means verified no assignment. '
                     'Country references, maritime limits, EEZ and federal administration are distinct. '
                     'International requires a qualified high-seas polygon outside national jurisdiction including EEZs, never a no-hit fallback. ' + spec['gap'])
        fields[name] = {**definition(group), 'definition': semantics, 'categorical_assignment': family,
                        'category_labels': spec['categories'], 'support_limitation': spec['gap'] if not qualified else 'Qualified source polygons remain reference geometry; see source acceptance evidence.'}
        fields[count] = {'units': 'count', 'nullable': True, 'definition': 'Distinct qualified source water-polygon IDs; supporting record count, not a map choice',
                         'missing_reason_field': count + '_status', 'coverage_reference': group}
        for column in (name, count):
            fields[column + '_status'] = {'units': None, 'nullable': False, 'definition': 'Qualified polygon assignment support; unrelated line hits never establish water assignment',
                                         'enum': ['observed', 'unknown', 'unavailable', 'not_applicable', 'partial']}
        coverage[group] = {'qualification': q if qualified else None, 'geographic_inventory_coverage': geo if qualified else {'status': 'unavailable'},
                           'effect': semantics, 'support_limitation': fields[name]['support_limitation']}
        for column, field in fields.items():
            if column.startswith(family + '__'):
                field['map_feature'] = column == name
        fields[name].update(scientific_features(family)[name])
    validate_memberships(table, fields)
    return table
