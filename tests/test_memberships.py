"""Paired categorical identities share the exact existing metric intersections."""
import json

import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import LineString, Point, box

from governance.h3_matrix import overlay_collection
from governance.memberships import MEMBERSHIP_TYPE, definition, validate_memberships
from governance.shared.schema import CANONICAL_FIELDS


def frame(rows):
    records = []
    for i, values in enumerate(rows):
        row = dict.fromkeys(CANONICAL_FIELDS)
        row.update(GOVERNANCE_FEATURE_ID='wdfw:7', SOURCE_DATASET_ID='wdfw',
                   SOURCE_FEATURE_ID='7', FEATURE_NAME='Area Seven', FEATURE_TYPE='marine_area',
                   AUTHORITY='WDFW', JURISDICTION='Washington', GEOMETRY_PART_ID=f'part-{i}',
                   MODEL_ELIGIBLE=False, MEASUREMENT_STATUS='observed', SOURCE_COVERAGE_STATUS='partial',
                   LEGAL_BINDING_STATUS='reference_geometry', CLIPPED_TO_FULL_AREA=False,
                   RETAINED_MEASURE_FRACTION=1., geometry=box(0, 0, 1, 1))
        row.update(values)
        row['RETAINED_GEOMETRY_TYPE'] = row['geometry'].geom_type
        records.append(row)
    return gpd.GeoDataFrame(records, crs=4326)


def overlay(native, completeness='partial'):
    grid = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1), box(10, 10, 11, 11)], crs=4326)
    return overlay_collection(grid, native, completeness=completeness, length_crs='EPSG:32631', include_attributes=False)


def test_paired_overlapping_multipart_agency_identity_codes_and_nulls(tmp_path):
    native = frame([
        {'AREA_CODE': '7'}, {'AREA_CODE': '7'},
        {'GOVERNANCE_FEATURE_ID': 'dfo:7', 'SOURCE_DATASET_ID': 'dfo', 'AUTHORITY': 'DFO', 'AREA_CODE': '7', 'FEATURE_NAME': None},
        {'GOVERNANCE_FEATURE_ID': 'dfo:19-11', 'SOURCE_DATASET_ID': 'dfo', 'SOURCE_FEATURE_ID': '19-11', 'AREA_CODE': '19-11', 'PARENT_AREA_CODE': '19', 'AREA_SYSTEM_ID': 'dfo.pfma', 'AREA_HIERARCHY_LEVEL': 'subarea', 'REGION': 'Pacific'},
        {'GOVERNANCE_FEATURE_ID': 'dfo:21-0', 'SOURCE_DATASET_ID': 'dfo', 'SOURCE_FEATURE_ID': '21-0', 'AREA_CODE': '21-0', 'PARENT_AREA_CODE': '21'},
    ])
    columns = overlay(native)
    members = columns['FEATURE_MEMBERSHIPS_V1']
    assert members.type == MEMBERSHIP_TYPE
    entries, missing = members.to_pylist()
    assert missing is None
    assert len(entries) == columns['FEATURE_COUNT'][0].as_py() == 4
    by_id = {entry['feature_id']: entry['records'] for entry in entries}
    assert by_id['wdfw:7'][0]['geometry_part_ids'] == ['part-0', 'part-1']
    assert by_id['dfo:7'][0]['feature_name'] is None
    assert by_id['dfo:7'][0]['region'] is None
    assert by_id['dfo:19-11'][0]['area_code'] == '19-11'
    assert by_id['dfo:21-0'][0]['area_code'] == '21-0'
    # Input traversal order does not affect serialized membership values.
    reversed_members = overlay(native.iloc[::-1])['FEATURE_MEMBERSHIPS_V1']
    assert members.equals(reversed_members)
    assert json.dumps(members.to_pylist(), sort_keys=True) == json.dumps(reversed_members.to_pylist(), sort_keys=True)
    path = tmp_path / 'members.parquet'
    pq.write_table(pa.table({'members': members}), path)
    assert pq.read_table(path)['members'].type == MEMBERSHIP_TYPE
    assert pq.read_table(path)['members'].to_pylist() == members.to_pylist()


def test_same_feature_preserves_different_paired_records():
    members = overlay(frame([{}, {'SOURCE_FEATURE_ID': 'chart-2', 'FEATURE_NAME': 'Alternate provider name'}]))['FEATURE_MEMBERSHIPS_V1'][0].as_py()
    assert len(members) == 1
    assert len(members[0]['records']) == 2
    assert {(r['source_feature_id'], r['feature_name']) for r in members[0]['records']} == {('7', 'Area Seven'), ('chart-2', 'Alternate provider name')}


@pytest.mark.parametrize('state', ['partial', 'unknown', 'unavailable', 'not_applicable', 'complete'])
def test_boundary_contact_and_support(state):
    native = frame([{'geometry': box(1, 0, 2, 1)}, {'geometry': LineString([(1, .5), (2, .5)]), 'GOVERNANCE_FEATURE_ID': 'line:7'}, {'geometry': Point(1, .5), 'GOVERNANCE_FEATURE_ID': 'point:7'}])
    result = overlay(native, state)
    assert result['FEATURE_COUNT'].to_pylist() == [1, 0 if state == 'complete' else None]
    assert [m['feature_id'] for m in result['FEATURE_MEMBERSHIPS_V1'][0].as_py()] == ['point:7']
    assert result['FEATURE_MEMBERSHIPS_V1'][1].as_py() == ([] if state == 'complete' else None)


def test_validator_reconciles_and_rejects_corruption():
    members = overlay(frame([{}, {}]))['FEATURE_MEMBERSHIPS_V1']
    name = 'test__feature_memberships_v1'
    fields = {name: definition('test')}
    table = pa.table({name: members, name + '_status': ['partial', 'partial'],
                      'test__recorded_feature_count': pa.array([1, None], pa.int64()),
                      'test__recorded_feature_count_status': ['partial', 'partial']})
    validate_memberships(table, fields)
    wrong = table.set_column(2, 'test__recorded_feature_count', pa.array([2, None], pa.int64()))
    with pytest.raises(ValueError, match='count mismatch'):
        validate_memberships(wrong, fields)
    values = members.to_pylist()
    values[0][0]['records'][0]['geometry_part_ids'] = ['part-1', 'part-0']
    with pytest.raises(ValueError, match='part lineage'):
        validate_memberships(table.set_column(0, name, pa.array(values, MEMBERSHIP_TYPE)), fields)


@pytest.mark.parametrize('change', ['version', 'binding', 'type', 'null_support'])
def test_validator_rejects_unsupported_contract_or_support(change):
    name = 'test__feature_memberships_v1'
    field = definition('test')
    table = pa.table({name: overlay(frame([{}]))['FEATURE_MEMBERSHIPS_V1'],
                      name + '_status': ['partial', 'partial'],
                      'test__recorded_feature_count': pa.array([1, None], pa.int64()),
                      'test__recorded_feature_count_status': ['partial', 'partial']})
    if change == 'version':
        field['membership_schema_version'] = 2
    elif change == 'binding':
        field['count_field'] = 'other__recorded_feature_count'
    elif change == 'type':
        table = table.set_column(0, name, pa.array(['bad', None]))
    else:
        table = table.set_column(0, name, pa.array([None, None], MEMBERSHIP_TYPE))
    with pytest.raises(ValueError, match='membership|Membership'):
        validate_memberships(table, {name: field})


def test_partial_null_habitat_and_exclusion_support_replays_as_unknown(tmp_path):
    import importlib
    from governance.memberships import MEMBERSHIP_TYPE
    for module in ('protected_areas.critical_habitat', 'vessel_management.exclusion_zones'):
        interface = importlib.import_module('governance.' + module + '.interface')
        count, assignment = interface.COUNT, interface.ASSIGNMENT
        table = pa.table({count: pa.array([None, 0, None], pa.int64()),
            assignment: pa.array([None, [], None], MEMBERSHIP_TYPE),
            count + '_status': ['partial', 'partial', 'unavailable'],
            assignment + '_status': ['partial', 'partial', 'unavailable']})
        metadata = {'fields': {name: {} for name in table.column_names}, 'original_data': {}}
        result = interface.annotate_product(table, metadata, tmp_path)
        assert result[count].equals(table[count])
        assert result[assignment].equals(table[assignment])
        for name in (count, assignment):
            assert result[name + '_status'].to_pylist() == ['unknown', 'partial', 'unavailable']
        assert interface.annotate_product(result, metadata, tmp_path).equals(result)
