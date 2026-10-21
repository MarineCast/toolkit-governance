import copy
import json
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from shapely.geometry import box
from governance.memberships import RECORD_FIELDS, MEMBERSHIP_TYPE, definition
from governance.administrative_context.coast_guard_sectors.interface import ASSIGNMENT, COUNT, COMPONENTS, GROUP, RETAINED, compact_features


def fixture():
    columns, fields = {'other__unchanged': [10, 20, 30, 40]}, {'other__unchanged': {'definition': 'unchanged'}}
    for group, source, name in zip(COMPONENTS, ['ccg_western_region', 'uscg_app_sectors'], ['Western', 'Sector Puget Sound']):
        record = dict.fromkeys(RECORD_FIELDS)
        record.update(source_dataset_id=source, source_feature_id=source+':1', feature_name=name, geometry_part_ids=['part-a'])
        member = {'feature_id': source+':1', 'records': [record]}
        col = group+'__feature_memberships_v1'; count = group+'__recorded_feature_count'
        values = [[member], None, [], None]; states = ['partial', 'unknown', 'observed', 'unavailable']
        columns.update({col: pa.array(values, MEMBERSHIP_TYPE), col+'_status': states, count: pa.array([1,None,0,None],pa.int64()), count+'_status': states,
                        group+'__recorded_polygon_union_area_fraction': [.1,None,0,None]})
        fields.update({n: {} for n in columns if n not in fields}); fields[col] = definition(group)
    return pa.table(columns), fields, {group: {'source_distinction': group} for group in COMPONENTS}


def test_compact_union_retains_all_records_support_and_unrelated_data():
    table, fields, coverage = fixture(); before = copy.deepcopy(coverage)
    expected = [table[group+'__feature_memberships_v1'][0].as_py()[0] for group in COMPONENTS]
    result = compact_features(table, fields, coverage)
    assert set(n for n in result.column_names if n.startswith(GROUP+'__')) == set(RETAINED)
    assert result[COUNT].to_pylist() == [2,None,0,None]
    assert result[ASSIGNMENT+'_status'].to_pylist() == ['partial','unknown','observed','unavailable']
    assert result[ASSIGNMENT][0].as_py() == sorted(expected, key=lambda entry:entry['feature_id'])
    assert result['other__unchanged'].equals(table['other__unchanged'])
    assert set(fields) == set(result.column_names)
    for group in COMPONENTS: assert coverage[group] == before[group]
    assert result.equals(compact_features(result, fields, coverage))
    assert [n for n,f in fields.items() if f.get('map_feature')] == [ASSIGNMENT]


def test_missing_component_does_not_infer_empty_or_zero_and_corruption_fails():
    table, fields, coverage = fixture()
    changed = table.set_column(table.column_names.index(COMPONENTS[0]+'__recorded_feature_count'), COMPONENTS[0]+'__recorded_feature_count',pa.array([9,None,0,None],pa.int64()))
    with pytest.raises(ValueError,match='count mismatch'):compact_features(changed,copy.deepcopy(fields),copy.deepcopy(coverage))
    removed=[n for n in table.column_names if n.startswith(COMPONENTS[1]+'__')]
    for name in removed: fields.pop(name)
    result=compact_features(table.drop(removed),fields,coverage)
    assert result[COUNT].to_pylist()==[1,None,None,None]


def test_normal_build_and_offline_originals_rebuild_keep_only_combined_fields(tmp_path,monkeypatch,snapshot_fixture):
    from governance.workspace import initialize_workspace
    from governance.shared.config import load_governance_config
    from governance.products import build_products, validate_products
    workspace=tmp_path/'workspace';initialize_workspace(workspace);monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(workspace))
    path=workspace/'config/data/governance/governance.yaml';values=yaml.safe_load(path.read_text())
    values['collections']={GROUP:values['collections'][GROUP]};ids=values['collections'][GROUP]['source_ids']
    values['sources']={sid:values['sources'][sid] for sid in ids};path.write_text(yaml.safe_dump(values))
    config=load_governance_config()
    for sid in ids:
        attrs={'OBJECTID':[1], 'FID':[23], 'NAME':['Sector Puget Sound']} if sid=='uscg_app_sectors' else {'OBJECTID':[1], 'OBJECTID_1':[1], 'Name':['Western']}
        frame=gpd.GeoDataFrame(attrs,geometry=[box(-124,48,-123,49)],crs=4326)
        source=config.sources[sid];source.snapshot_path.parent.mkdir(parents=True,exist_ok=True)
        source.snapshot_path.write_text(json.dumps(snapshot_fixture(source,frame)))
    grid=tmp_path/'grid.parquet';pq.write_table(pa.table({'H3_INDEX':[h3.latlng_to_cell(48.5,-123.5,r) for r in (6,8)],'H3_RESOLUTION':[6,8]}),grid)
    output=build_products([grid],tmp_path/'Governance',config_path=path,allow_partial=True)
    assert validate_products(output)['status']=='passed'
    replay=build_products([grid],tmp_path/'replay',config_path=path,original_data=output,allow_partial=True)
    for res in (6,8):
        table=pq.read_table(output/f'governance-r{res}-static.parquet')
        assert set(table.column_names)=={'h3_index',*RETAINED}
        assert table[COUNT].to_pylist()==[2]
        assert table.equals(pq.read_table(replay/f'governance-r{res}-static.parquet'),check_metadata=False)


def test_western_water_fill_is_bounded_paired_idempotent_and_preserves_units(tmp_path):
    from governance.administrative_context.coast_guard_sectors.interface import BC_ASSIGNMENT, WATER_METHOD, populate_water_features
    from governance.jurisdiction.geographic_water import WATER, METHOD
    from governance.shared.artifacts import sha256_file
    table, fields, coverage = fixture()
    table = compact_features(table, fields, coverage)
    originals = {}
    for source, attrs in [('ccg_western_region', {'Name': ['Western'], 'OBJECTID_1': [1]}),
                          (WATER, {'NAME': ['CANADA'], 'AREA': ['BRITISH_COLUMBIA'], 'TYPE': ['TERRITORIAL']})]:
        path = tmp_path/'OriginalData'/source/'geometry.parquet'; path.parent.mkdir(parents=True)
        gpd.GeoDataFrame(attrs, geometry=[box(-125,48,-123,50)], crs=4326).to_parquet(path)
        original = pq.read_table(path)
        pq.write_table(original.replace_schema_metadata({**original.schema.metadata,
            b'governance_original': json.dumps({'source': {'source_id': source}}).encode()}), path)
        originals[source] = {'path': str(path.relative_to(tmp_path)), 'sha256': sha256_file(path)}
    record = dict.fromkeys(RECORD_FIELDS)
    record.update(source_dataset_id=WATER, source_feature_id=WATER+':CAN:01', jurisdiction='CAN', region='BC',
                  feature_type='geographic_province_water_polygon', geometry_part_ids=['water-part'])
    member = {'feature_id': 'geographic_state_province:CAN:BC', 'records': [record]}
    # Row 0 already has Western + USCG; row 1 gains Western; row 2 has no BC;
    # row 3 has a USCG sector and gains Western without losing that sector.
    us = table[ASSIGNMENT][0].as_py()[1]
    table = table.set_column(table.column_names.index(ASSIGNMENT), ASSIGNMENT,
                            pa.array([table[ASSIGNMENT][0].as_py(), None, [], [us]], MEMBERSHIP_TYPE))
    table = table.set_column(table.column_names.index(COUNT), COUNT, pa.array([2,None,0,1],pa.int64()))
    for col in (ASSIGNMENT+'_status', COUNT+'_status'):
        table = table.set_column(table.column_names.index(col), col, pa.array(['partial','unknown','observed','partial']))
    bc_group = BC_ASSIGNMENT.rpartition('__')[0]; bc_count = bc_group+'__recorded_feature_count'
    for col, values in {BC_ASSIGNMENT: pa.array([[member],[member],None,[member]], MEMBERSHIP_TYPE),
                        bc_count: pa.array([1,1,None,1],pa.int64()), BC_ASSIGNMENT+'_status': ['partial','partial','unknown','partial'],
                        bc_count+'_status': ['partial','partial','unknown','partial']}.items():
        table = table.append_column(col, values if isinstance(values, pa.Array) else pa.array(values)); fields[col] = {}
    fields[BC_ASSIGNMENT] = {**definition(bc_group), 'scientific_method_version': METHOD, 'assignment_semantics': 'geographic',
                             'original_source_bindings': {WATER: originals[WATER]}}
    metadata = {'fields': fields, 'coverage': coverage, 'original_data': originals}
    before = copy.deepcopy(metadata)
    result = populate_water_features(table, metadata, tmp_path)
    assert result[COUNT].to_pylist() == [2,1,0,2]
    assert result[ASSIGNMENT+'_status'].to_pylist() == ['partial','partial','observed','partial']
    assert result[ASSIGNMENT][0] == table[ASSIGNMENT][0]
    derived = result[ASSIGNMENT][1].as_py()[0]
    assert derived['feature_id'] == 'ccg_western_region:1'
    assert derived['records'][0]['source_dataset_id'] == WATER
    assert derived['records'][0]['geometry_part_ids'] == ['water-part']
    assert derived['records'][0]['feature_type'] == 'derived_ccg_region_model_water_assignment'
    assert result[ASSIGNMENT][3].as_py()[1] == us
    assert metadata['fields'][ASSIGNMENT]['scientific_method_version'] == WATER_METHOD
    assert metadata['coverage'][GROUP]['derived_western_water_cells'] == 2
    for col in table.column_names:
        if col not in RETAINED:
            assert result[col].equals(table[col]); assert metadata['fields'][col] == before['fields'][col]
    replay_metadata = copy.deepcopy(metadata)
    assert result.equals(populate_water_features(result, replay_metadata, tmp_path))
    assert metadata == replay_metadata
    missing = copy.deepcopy(before); missing['original_data'].pop('ccg_western_region')
    assert table.equals(populate_water_features(table, missing, tmp_path))
    untyped = copy.deepcopy(before); untyped['fields'][BC_ASSIGNMENT].pop('assignment_semantics')
    assert table.equals(populate_water_features(table, untyped, tmp_path))
    corrupt = copy.deepcopy(before); corrupt['fields'][BC_ASSIGNMENT]['original_source_bindings'][WATER]['sha256'] = 'wrong'
    with pytest.raises(ValueError, match='binding mismatch'):
        populate_water_features(table, corrupt, tmp_path)
    # A Canada name or BC label alone cannot qualify a nonmatching source record.
    bad = copy.deepcopy(member); bad['records'][0]['source_feature_id'] = WATER+':CAN:02'
    other = table.set_column(table.column_names.index(BC_ASSIGNMENT), BC_ASSIGNMENT,
                             pa.array([[bad],[bad],None,[bad]], MEMBERSHIP_TYPE))
    assert table[ASSIGNMENT].equals(populate_water_features(other, copy.deepcopy(before), tmp_path)[ASSIGNMENT])
