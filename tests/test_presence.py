import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from governance.app_only import compact_table
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition
from governance.products import validate_metric_table


@pytest.fixture(params=[
    ('vessel_routing_regulations__recorded_reference', 'vessel_routing_regulations__traffic_separation_zones'),
    ('tribal_first_nations_areas__mapped_area', 'tribal_first_nations_areas'),
    ('federal_waters__international_boundary', 'federal_waters__international_boundary'),
])
def presence_table(request):
    flag, group = request.param
    members, count = group+'__feature_memberships_v1', group+'__recorded_feature_count'
    record = dict.fromkeys(RECORD_FIELDS)
    record.update(source_dataset_id='fixture',source_feature_id='record:1',feature_name='Reference',geometry_part_ids=['part:1'])
    cells = [h3.latlng_to_cell(lat,-123,6) for lat in (48,49)]
    table = pa.table({'h3_index':cells,
        members:pa.array([[{'feature_id':'feature:1','records':[record]}],None],MEMBERSHIP_TYPE),
        members+'_status':['partial','unknown'],count:pa.array([1,None],pa.int64()),count+'_status':['partial','unknown'],
        flag:pa.array([True,None],pa.bool_()),flag+'_status':['partial','unknown']})
    fields = {'h3_index':{},members:definition(group),members+'_status':{},
        count:{'units':'count','missing_reason_field':count+'_status'},count+'_status':{},
        flag:{'units':'1','value_semantics':'boolean_overlap','missing_reason_field':flag+'_status'},flag+'_status':{}}
    metadata = {'schema_version':1,'model_eligible':False,'spatial':{'h3_resolution':6},'temporal':{'type':'static'},
        'fields':fields,'original_data':{},'collections':{},'coverage':{}}
    return table, metadata, flag


def test_positive_and_unknown_presence_validate_in_final_file(presence_table, tmp_path):
    table, metadata, _ = presence_table
    validate_metric_table(table, metadata)
    public, context = compact_table(table, metadata)
    path = tmp_path/'final.parquet'
    pq.write_table(public,path)
    validate_metric_table(pq.read_table(path), context)


@pytest.mark.parametrize('values', [[False,None],[None,None],[True,False],[True,True]])
def test_rejects_presence_contradictions_before_and_after_projection(presence_table, values):
    table, metadata, flag = presence_table
    # A partial status permits finite values in the generic scalar validator;
    # membership and absence checks must reject the contradictions independently.
    table = table.set_column(table.column_names.index(flag),flag,pa.array(values,pa.bool_()))
    table = table.set_column(table.column_names.index(flag+'_status'),flag+'_status',pa.array(['partial','partial']))
    with pytest.raises(ValueError,match='Boolean'):
        validate_metric_table(table, metadata)
    public, context = compact_table(table, metadata)
    with pytest.raises(ValueError,match='Boolean'):
        validate_metric_table(public, context)


def test_routing_false_requires_every_component_qualified_and_observed_empty():
    from governance.vessel_management.presentation import add_features, GROUPS, PRESENCE
    from governance.app_contract import project_app_contract
    cells = [h3.latlng_to_cell(48,-123,6)]
    columns, fields, coverage = {'h3_index':pa.array(cells)}, {'h3_index':{}}, {}
    for group in GROUPS:
        member, count = group+'__feature_memberships_v1',group+'__recorded_feature_count'
        columns.update({member:pa.array([[]],MEMBERSHIP_TYPE),member+'_status':pa.array(['observed']),
                        count:pa.array([0],pa.int64()),count+'_status':pa.array(['observed'])})
        fields.update({member:definition(group),member+'_status':{},count:{'units':'count','missing_reason_field':count+'_status'},count+'_status':{}})
        coverage[group] = {'geographic_inventory_coverage':{'status':'complete','scope':'full_supplied_cells','evidence':'synthetic full-cell qualification'}}
    table = add_features(pa.table(columns),fields,coverage)
    metadata = {'schema_version':1,'model_eligible':False,'spatial':{'h3_resolution':6},'temporal':{'type':'static'},
        'fields':fields,'coverage':coverage,'collections':{},'original_data':{}}
    table = project_app_contract(table,metadata)
    assert table[PRESENCE][0].as_py() is False
    validate_metric_table(table,metadata)
    public, context = compact_table(table,metadata)
    validate_metric_table(public,context)
    coverage[GROUPS[0]]['geographic_inventory_coverage']['scope'] = 'national_roster'
    with pytest.raises(ValueError,match='complete observed empty'):
        validate_metric_table(table,metadata)
