import copy
import pyarrow as pa
import pytest
from governance.memberships import MEMBERSHIP_TYPE,RECORD_FIELDS,definition
from governance.vessel_management.presentation import (annotate_fields,annotate_catalog,add_features,
    FAMILY_KEY,FAMILY_NAME,COLLECTIONS,GROUPS,PRESENCE,PRESENCE_NAME,SHIPPING,SEPARATION)

def fixture(empty=False):
 columns={'other__value':pa.array([7,8])};fields={'other__value':{'definition':'kept'}};coverage={}
 for g in GROUPS:
  name=g+'__feature_memberships_v1';count=g+'__recorded_feature_count';rows=[[],[]] if empty else [None,None];states=['observed','observed'] if empty else ['partial','partial']
  columns.update({name:pa.array(rows,MEMBERSHIP_TYPE),name+'_status':pa.array(states),count:pa.array([0,0] if empty else [None,None],pa.int64()),count+'_status':pa.array(states)})
  fields[name]=definition(g);fields[name+'_status']={'definition':'support'};fields[count]={'units':'count','missing_reason_field':count+'_status'};fields[count+'_status']={'definition':'support'}
  coverage[g]={'geographic_inventory_coverage':{'status':'unknown'}}
 return pa.table(columns),fields,coverage

def complete(coverage):
 for g in GROUPS:coverage[g]['geographic_inventory_coverage']={'status':'complete','scope':'full_supplied_cells','evidence':'Explicit synthetic full-cell inventory qualification'}

def test_positive_advisory_reference_is_true_without_claiming_mandatory_restriction_or_changing_components():
 table,fields,coverage=fixture();g='shipping_lanes__chs_recommended_track';name=g+'__feature_memberships_v1';count=g+'__recorded_feature_count'
 record={k:None for k in RECORD_FIELDS};record.update(source_dataset_id='chs_routing_layer_5',source_feature_id='native:1',feature_name='Recommended track',feature_type='routing_component_reference',geometry_part_ids=['part:1'])
 table=table.set_column(table.column_names.index(name),name,pa.array([[{'feature_id':'reference:1','records':[record]}],None],MEMBERSHIP_TYPE));table=table.set_column(table.column_names.index(count),count,pa.array([1,None],pa.int64()))
 result=add_features(table,fields,coverage)
 assert result[PRESENCE].type==pa.bool_() and result[PRESENCE].to_pylist()==[True,None]
 assert result[PRESENCE+'_status'].to_pylist()==['partial','unknown']
 assert all(result[c].equals(table[c]) for c in table.column_names)
 assert sum(v.get('map_feature',False) and v.get('role')=='scientific_metric' for v in fields.values())==1
 assert sum(v.get('map_feature',False) and v.get('role')=='recorded_feature_identity' for v in fields.values())==2
 assert 'recommended' in fields[PRESENCE]['definition'] and 'not mean an unconditional' in fields[PRESENCE]['definition']
 assert fields[name]['source_context']['chs_routing_layer_5']['classification'].startswith('Navigation/recommended')
 assert fields['other__value']=={'definition':'kept'}
 again=add_features(result,fields,coverage);assert again.equals(result,check_metadata=False)

def test_observed_empty_arrays_alone_never_prove_absence():
 table,fields,coverage=fixture(empty=True);result=add_features(table,fields,coverage)
 assert result[PRESENCE].to_pylist()==[None,None]
 assert result[PRESENCE+'_status'].to_pylist()==['unknown','unknown']

def test_false_requires_every_component_observed_empty_and_explicit_full_cell_completeness():
 table,fields,coverage=fixture(empty=True);complete(coverage)
 result=add_features(table,fields,coverage);assert result[PRESENCE].to_pylist()==[False,False]
 assert result[PRESENCE+'_status'].to_pylist()==['observed','observed']
 coverage[GROUPS[0]]['geographic_inventory_coverage']['scope']='national_extent_only'
 assert add_features(result,fields,coverage)[PRESENCE].to_pylist()==[None,None]

def test_missing_component_cannot_be_treated_as_empty_even_with_other_complete_coverage():
 table,fields,coverage=fixture(empty=True);complete(coverage);g=GROUPS[0]
 removed=[n for n in table.column_names if n.startswith(g+'__')];table=table.drop(removed)
 for n in removed:fields.pop(n)
 assert add_features(table,fields,coverage)[PRESENCE].to_pylist()==[None,None]

def test_invalid_membership_count_support_fails_closed():
 table,fields,coverage=fixture(empty=True);name=GROUPS[0]+'__recorded_feature_count';table=table.set_column(table.column_names.index(name),name,pa.array([2,0],pa.int64()))
 with pytest.raises(ValueError,match='Membership/count mismatch'):add_features(table,fields,coverage)

def test_catalog_exposes_one_boolean_and_all_identity_columns_without_touching_other_families():
 fields={n+'__old_measure':{'units':'m','definition':'native role'} for n in COLLECTIONS};fields['exclusion_zones__value']={'units':'count'};before=copy.deepcopy(fields);annotate_fields(fields)
 for n in COLLECTIONS:assert fields[n+'__old_measure']=={**before[n+'__old_measure'],'display_family':FAMILY_NAME,'map_feature':False}
 assert fields['exclusion_zones__value']==before['exclusion_zones__value']
 catalog={'areas':{n:{'source':'unchanged'} for n in COLLECTIONS},'feature_families':{'other':{'display_name':'Kept'}}};annotate_catalog(catalog)
 f=catalog['feature_families'][FAMILY_KEY];assert f['measurement_columns']==[PRESENCE] and len(f['identity_columns'])==2 and len(f['native_identity_columns'])==16
 assert f['scientific_features'][PRESENCE]['display_name']==PRESENCE_NAME
 assert catalog['feature_families']['other']=={'display_name':'Kept'}

def test_grouped_shipping_preserves_each_source_record_and_part_without_inflating_same_feature():
 table,fields,coverage=fixture();groups=['shipping_lanes__chs_recommended_track','shipping_lanes__chs_navigation_line']
 for i,g in enumerate(groups):
  record={k:None for k in RECORD_FIELDS};record.update(source_dataset_id='chs_routing_layer_5',source_feature_id=f'native:{i}',feature_name='Original source name',geometry_part_ids=[f'part:{i}'])
  name=g+'__feature_memberships_v1';count=g+'__recorded_feature_count'
  table=table.set_column(table.column_names.index(name),name,pa.array([[{'feature_id':'logical:1','records':[record]}],None],MEMBERSHIP_TYPE));table=table.set_column(table.column_names.index(count),count,pa.array([1,None],pa.int64()))
 result=add_features(table,fields,coverage);name=SHIPPING+'__feature_memberships_v1';row=result[name].to_pylist()[0]
 assert len(row)==1 and len(row[0]['records'])==2
 assert result[SHIPPING+'__recorded_feature_count'].to_pylist()==[1,None]
 assert {tuple(r['geometry_part_ids']) for r in row[0]['records']}=={('part:0',),('part:1',)}
 assert all(result[c].equals(table[c]) for c in table.column_names)
 assert fields[name]['display_name']=='Shipping Lanes'
 assert fields[name]['source_record_context']['native:0']['routing_role']=='chs_recommended_track'
 assert fields[name]['source_record_context']['native:1']['routing_role']=='chs_navigation_line'

def test_all_seven_tss_roles_are_grouped_and_native_roles_records_and_parts_remain_exact():
 table,fields,coverage=fixture()
 groups=[g for g in GROUPS if g.startswith('traffic_separation_schemes__')]
 from governance.vessel_management.routing import ROLES
 assert len(groups)==7
 for g in groups:
  role=g.rpartition('__')[2];record={k:None for k in RECORD_FIELDS}
  record.update(source_dataset_id=ROLES[role][1],source_feature_id='native:'+role,feature_name='Original '+role,geometry_part_ids=['part:'+role])
  name=g+'__feature_memberships_v1';count=g+'__recorded_feature_count'
  table=table.set_column(table.column_names.index(name),name,pa.array([[{'feature_id':'logical:'+role,'records':[record]}],None],MEMBERSHIP_TYPE))
  table=table.set_column(table.column_names.index(count),count,pa.array([1,None],pa.int64()))
 result=add_features(table,fields,coverage);name=SEPARATION+'__feature_memberships_v1'
 assert fields[name]['display_name']=='Shipping Lanes & Traffic Separation Zones'
 assert result[SEPARATION+'__recorded_feature_count'].to_pylist()==[7,None]
 assert result[name+'_status'].to_pylist()==['partial','unknown']
 assert {m['feature_id'] for m in result[name].to_pylist()[0]}=={'logical:'+g.rpartition('__')[2] for g in groups}
 for g in groups:
  role=g.rpartition('__')[2];assert not fields[g+'__feature_memberships_v1']['map_feature']
  detail=fields[name]['source_record_context']['native:'+role]
  assert detail['routing_role']==role and detail['source_object_type']==ROLES[role][2]
 assert set(fields[name]['source_context'])=={'chs_routing_layer_2','chs_routing_layer_3','chs_routing_layer_4','chs_routing_layer_5','noaa_routing_2026'}
 assert all(result[c].equals(table[c]) for c in table.column_names)


def test_shipping_and_tss_union_keeps_distinct_types_records_parts_and_unknown_support():
 table,fields,coverage=fixture()
 groups=['shipping_lanes__chs_recommended_track','traffic_separation_schemes__noaa_traffic_lane']
 for i,g in enumerate(groups):
  record={k:None for k in RECORD_FIELDS};record.update(source_dataset_id=['chs_routing_layer_5','noaa_routing_2026'][i],source_feature_id=f'original:{i}',feature_name='Native name',geometry_part_ids=[f'part:{i}'])
  name=g+'__feature_memberships_v1';count=g+'__recorded_feature_count'
  table=table.set_column(table.column_names.index(name),name,pa.array([[{'feature_id':f'source-qualified:{i}','records':[record]}],None],MEMBERSHIP_TYPE))
  table=table.set_column(table.column_names.index(count),count,pa.array([1,None],pa.int64()))
 result=add_features(table,fields,coverage);name=SEPARATION+'__feature_memberships_v1'
 assert result[SEPARATION+'__recorded_feature_count'].to_pylist()==[2,None]
 assert result[name+'_status'].to_pylist()==['partial','unknown']
 assert {m['feature_id'] for m in result[name].to_pylist()[0]}=={'source-qualified:0','source-qualified:1'}
 assert not fields[SHIPPING+'__feature_memberships_v1']['map_feature']
 assert fields[name]['map_feature']
 assert len(coverage[SEPARATION]['component_groups'])==15
 assert {v['routing_role'] for v in fields[name]['source_record_context'].values()}=={'chs_recommended_track','noaa_traffic_lane'}
 assert all(result[c].equals(table[c]) for c in table.column_names)
 catalog={'areas':dict.fromkeys(COLLECTIONS,{})};annotate_catalog(catalog)
 assert catalog['feature_families'][FAMILY_KEY]['saved_identity_aliases'][SHIPPING+'__feature_memberships_v1']==name
