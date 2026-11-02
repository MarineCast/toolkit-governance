"""One combined Coast Guard assignment with paired support, preserving source roles."""
import json
import copy

import geopandas as gpd
import pyarrow as pa

from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, validate_memberships

GROUP = 'coast_guard_sectors'
ASSIGNMENT = GROUP + '__feature_memberships_v1'
COUNT = GROUP + '__recorded_feature_count'
COMPONENTS = (GROUP + '__ccg_administrative_region', GROUP + '__uscg_sector')
SOURCE_CONTEXT = {
    'ccg_western_region': {'country': 'Canada', 'agency': 'Canadian Coast Guard',
                          'boundary_type': 'CCG administrative region reference'},
    'uscg_app_sectors': {'country': 'United States', 'agency': 'United States Coast Guard',
                         'boundary_type': 'USCG sector reference'},
}
DEFINITION = ('All recorded Canadian Coast Guard administrative regions and US Coast Guard sectors '
              'intersecting each native cell, shown together with every overlapping name and source-qualified ID. '
              'These are different organizational unit types, not equivalent sectors or operational/legal jurisdiction. '
              'Missing component support remains unknown; no dominant unit or new spatial coverage is inferred.')
WATER_METHOD = 'coast-guard-western-model-water-assignment-1'
BC_ASSIGNMENT = 'state_provincial_waters__assignment__feature_memberships_v1'
WATER_DEFINITION = ('Coast Guard administrative assignment: retained CCG region and USCG sector polygon memberships, '
    'supplemented by Western over explicit British Columbia model-water support. Added water assignments are derived, '
    'not intersections with the original CCG polygon or a legal/operational boundary. Every existing unit and overlap '
    'is retained; unmatched cells remain unknown. Counts describe distinct assigned units, not equivalent jurisdictions.')


def _merge(rows):
    features = {}
    for row in rows:
        for member in row or []:
            records = features.setdefault(member['feature_id'], {})
            for record in member['records']:
                key = tuple(record[name] for name in RECORD_FIELDS)
                records.setdefault(key, set()).update(record['geometry_part_ids'])
    return [{'feature_id': identity, 'records': [dict(zip(RECORD_FIELDS, key), geometry_part_ids=sorted(parts))
            for key, parts in sorted(records.items(), key=lambda item: json.dumps(item[0], ensure_ascii=True))]}
            for identity, records in sorted(features.items())]


def compact_features(table, fields, coverage):
    """Combine typed memberships and remove obsolete component diagnostics.

    Original source geometry/attributes and source-distinct coverage records remain
    retained. The support count is administrative feature identity, not jurisdiction.
    """
    if not any(name.startswith(GROUP + '__') for name in table.column_names):
        return table
    validate_memberships(table, fields)
    if not any(group + '__feature_memberships_v1' in table.column_names for group in COMPONENTS):
        if ASSIGNMENT not in table.column_names:
            raise ValueError('Coast Guard compaction requires source membership evidence')
        return _compact(table, fields, coverage)
    rows, statuses = [], []
    for group in COMPONENTS:
        column = group + '__feature_memberships_v1'
        rows.append(table[column].to_pylist() if column in table.column_names else [None] * table.num_rows)
        statuses.append(table[column + '_status'].to_pylist() if column in table.column_names else ['unavailable'] * table.num_rows)
    combined, states = [], []
    for i in range(table.num_rows):
        entries = _merge([row[i] for row in rows])
        observed = all(row[i] is not None for row in rows) and all(status[i] == 'observed' for status in statuses)
        if entries:
            combined.append(entries); states.append('observed' if observed else 'partial')
        elif observed and all(row[i] == [] for row in rows):
            combined.append([]); states.append('observed')
        else:
            combined.append(None)
            states.append('unavailable' if all(status[i] == 'unavailable' for status in statuses) else 'unknown')
    values = {ASSIGNMENT: pa.array(combined, MEMBERSHIP_TYPE), ASSIGNMENT + '_status': pa.array(states, pa.string()),
              COUNT: pa.array([len(row) if row is not None else None for row in combined], pa.int64()),
              COUNT + '_status': pa.array(states, pa.string())}
    for column, value in values.items():
        table = (table.set_column(table.column_names.index(column), column, value) if column in table.column_names
                 else table.append_column(column, value))
    fields[ASSIGNMENT] = {'definition': DEFINITION, 'units': None, 'membership_schema_version': 1,
        'coverage_reference': GROUP, 'count_field': COUNT, 'missing_reason_field': ASSIGNMENT + '_status',
        'source_context': SOURCE_CONTEXT, 'derivation': 'Union of the two retained typed membership arrays; no spatial recalculation',
        'scientific_method_version': 'coast-guard-membership-union-1'}
    fields[COUNT] = {'definition': 'Count of distinct displayed administrative feature IDs, not unique jurisdiction or operational coverage',
                     'units': 'count', 'missing_reason_field': COUNT + '_status'}
    for column in (ASSIGNMENT, COUNT):
        fields[column + '_status'] = {'definition': 'Combined recorded support; unresolved component absence remains unknown', 'units': None}
    return _compact(table, fields, coverage)


SCIENTIFIC_FEATURES = {ASSIGNMENT: {'display_name': 'Coast Guard Assignment'}}
RETAINED = (ASSIGNMENT, ASSIGNMENT + '_status', COUNT, COUNT + '_status')


def _compact(table, fields, coverage):
    removed = [name for name in table.column_names if name.startswith(GROUP + '__') and name not in RETAINED]
    for name in removed:
        fields.pop(name, None)
    table = table.drop(removed)
    for name in RETAINED:
        fields[name].update(map_feature=name in SCIENTIFIC_FEATURES, **SCIENTIFIC_FEATURES.get(name, {}))
    coverage.setdefault(GROUP, {}).update(
        component_groups=list(COMPONENTS), source_context=SOURCE_CONTEXT,
        interpretation=DEFINITION, scientific_method_version='coast-guard-membership-union-1',
        overlap_policy='All source-qualified administrative unit memberships retained; units are not equivalent jurisdictions; no area summation',
        effect='Positive combined matches retain recorded support; unresolved no-hit cells remain null; zero requires both observed empty components')
    validate_memberships(table, fields)
    return table


def populate_water_features(table, metadata, original_root):
    """Extend Western only over checksum-bound, explicitly typed BC water support.

    The CCG original establishes the unit identity; the retained water original
    supplies the geometry lineage for additions. No source polygon is modified.
    """
    from governance.jurisdiction.geographic_water import WATER, METHOD, _original
    if ASSIGNMENT not in table.column_names or BC_ASSIGNMENT not in table.column_names:
        return table
    fields = metadata['fields']
    descriptor = fields[BC_ASSIGNMENT]
    if descriptor.get('scientific_method_version') != METHOD or descriptor.get('assignment_semantics') != 'geographic':
        return table
    ccg = _original(original_root, metadata, 'ccg_western_region')
    water = _original(original_root, metadata, WATER)
    if ccg is None or water is None:
        return table
    if descriptor.get('original_source_bindings', {}).get(WATER) != metadata['original_data'][WATER]:
        raise ValueError('Western water assignment requires matching BC original source binding')
    region = gpd.read_parquet(ccg[0])
    if len(region) != 1 or region.iloc[0].get('Name') != 'Western':
        raise ValueError('Western water assignment requires one explicit Western source identity')
    identity = 'ccg_western_region:' + str(region.iloc[0]['OBJECTID_1'])
    support = gpd.read_parquet(water[0])
    # Match the geographic-water producer's source row IDs, without a second
    # spatial overlay or assuming every Canadian source row represents BC.
    from governance.jurisdiction.water_assignments import normalize_country
    counts, bc_ids = {}, set()
    for _, source in support.iterrows():
        country = normalize_country(source.get('NAME'))
        if country is None:
            continue
        counts[country] = counts.get(country, 0) + 1
        if country == 'CAN' and source.get('AREA') == 'BRITISH_COLUMBIA' and source.get('TYPE') == 'TERRITORIAL':
            bc_ids.add(f'{WATER}:CAN:{counts[country]:02d}')
    validate_memberships(table, fields)
    rows = table[ASSIGNMENT].to_pylist()
    statuses = table[ASSIGNMENT + '_status'].to_pylist()
    for i, water_members in enumerate(table[BC_ASSIGNMENT].to_pylist()):
        if any(entry['feature_id'] == identity for entry in rows[i] or []):
            continue
        records = [dict(record, feature_name='Western', feature_type='derived_ccg_region_model_water_assignment',
            authority='Derived model assignment; Canadian Coast Guard region identity', region='Western',
            area_system_id='ccg_western_region', area_code=None, area_title='Western')
            for entry in water_members or [] if entry['feature_id'] == 'geographic_state_province:CAN:BC'
            for record in entry['records'] if record['source_dataset_id'] == WATER
            and record['source_feature_id'] in bc_ids and record['jurisdiction'] == 'CAN'
            and record['region'] == 'BC' and record['feature_type'] == 'geographic_province_water_polygon']
        if records:
            rows[i] = _merge([rows[i], [{'feature_id': identity, 'records': records}]])
            statuses[i] = 'partial'
    values = {ASSIGNMENT: pa.array(rows, MEMBERSHIP_TYPE), ASSIGNMENT + '_status': pa.array(statuses, pa.string()),
              COUNT: pa.array([len(row) if row is not None else None for row in rows], pa.int64()),
              COUNT + '_status': pa.array(statuses, pa.string())}
    for column, value in values.items():
        table = table.set_column(table.column_names.index(column), column, value)
    bindings = {source: copy.deepcopy(metadata['original_data'][source]) for source in ('ccg_western_region', WATER)}
    context = {**SOURCE_CONTEXT, WATER: {'country': 'Canada', 'agency': 'Canadian Coast Guard',
        'boundary_type': 'Derived Western assignment over BC model-water support'}}
    fields[ASSIGNMENT].update(definition=WATER_DEFINITION, source_context=context,
        scientific_method_version=WATER_METHOD, original_source_bindings=bindings,
        derivation='Retained source polygon memberships plus Western for explicit BC geographic model-water memberships',
        geometry_lineage='Added Western records retain water source IDs and intersecting water part IDs, not CCG polygon intersection IDs. CCG original supplies the assigned unit identity.',
        assignment_semantics='recorded_polygons_plus_derived_bc_model_water')
    fields[COUNT]['definition'] = 'Count of distinct assigned Coast Guard unit IDs, including derived Western water assignments; not jurisdiction or operational coverage'
    metadata['coverage'][GROUP].update(interpretation=WATER_DEFINITION, source_context=context,
        scientific_method_version=WATER_METHOD, original_source_bindings=bindings,
        water_assignment_rule='Western only for positive-area BC geographic model-water support; no nearest-shore or country complement',
        effect='Added water assignments are partial; existing memberships and unresolved support outside BC water remain unchanged')
    # This is a current derivation total, not the number changed on this replay.
    metadata['coverage'][GROUP]['derived_western_water_cells'] = sum(any(
        r['feature_type'] == 'derived_ccg_region_model_water_assignment'
        for entry in row or [] for r in entry['records']) for row in rows)
    validate_memberships(table, fields)
    return table
