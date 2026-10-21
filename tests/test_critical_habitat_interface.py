import copy
from governance.protected_areas.critical_habitat.interface import (
    annotate_fields,annotate_catalog,COUNT,ASSIGNMENT,SCIENTIFIC_FEATURES,LIMITATION)


def test_exactly_two_features_keep_native_binding_units_status_and_definitions():
    names=[COUNT,ASSIGNMENT,COUNT+'_status',ASSIGNMENT+'_status','critical_habitat__recorded_polygon_union_area_fraction','critical_habitat__recorded_line_union_length_m','critical_habitat__recorded_point_feature_count']
    fields={name:{'definition':'Original source-based meaning','units':'count','missing_reason_field':'original_status','count_field':COUNT} for name in names}
    fields['other__value']={'definition':'Untouched'}
    before=copy.deepcopy(fields);annotate_fields(fields)
    assert {name for name,f in fields.items() if f.get('map_feature')}==set(SCIENTIFIC_FEATURES)
    for name,field in before.items():
        for key,value in field.items():assert fields[name][key]==value
    assert fields['other__value']==before['other__value']
    assert all(LIMITATION in fields[name]['interpretation'] for name in SCIENTIFIC_FEATURES)
    assert 'never zero' in LIMITATION
    replay=copy.deepcopy(fields);annotate_fields(fields);assert fields==replay
    catalog={'areas':{'critical_habitat':{'last_updated_utc':'Original'},'other':{'source':'Untouched'}}}
    annotate_catalog(catalog)
    assert catalog['areas']['critical_habitat']['scientific_features']==SCIENTIFIC_FEATURES
    assert catalog['areas']['critical_habitat']['last_updated_utc']=='Original'
    assert catalog['areas']['other']=={'source':'Untouched'}


def test_retained_classifications_join_by_source_id_without_metric_changes(tmp_path):
    import hashlib,json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from governance.memberships import MEMBERSHIP_TYPE,RECORD_FIELDS
    from governance.protected_areas.critical_habitat.interface import annotate_product
    source='noaa_critical_habitat_polygon';identity=source+':7'
    record=dict.fromkeys(RECORD_FIELDS);record.update(source_dataset_id=source,source_feature_id=identity,feature_name='Killer whale',geometry_part_ids=['part-a','part-b'])
    table=pa.table({COUNT:pa.array([1,None],pa.int64()),ASSIGNMENT:pa.array([[{'feature_id':identity,'records':[record]}],None],MEMBERSHIP_TYPE)})
    path=tmp_path/'OriginalData'/source/'geometry.parquet';path.parent.mkdir(parents=True)
    pq.write_table(pa.table({'OBJECTID':[7],'CHSTATUS':['Final'],'LISTENTITY':['Southern Resident'],'UNIT':['Unit 1'],'EFFECTDATE':['02/11/2015']}),path)
    metadata={'fields':{name:{'definition':'Original meaning'} for name in table.column_names},'original_data':{source:{'path':str(path.relative_to(tmp_path)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}}
    result=annotate_product(table,metadata,tmp_path)
    assert result.equals(table,check_metadata=True)
    context=metadata['fields'][ASSIGNMENT]['source_record_context'][identity]
    assert context['habitat_status']=='Final' and context['habitat_unit']=='Unit 1'
    assert context['source_effective_date']=='02/11/2015'
    assert metadata['fields'][ASSIGNMENT]['source_context'][source]['country']=='United States'
    assert 'Canadian SARA' in metadata['coverage']['critical_habitat']['scope_gaps'][0]
    metadata['original_data'][source]['sha256']='wrong'
    import pytest
    with pytest.raises(ValueError,match='checksum'):annotate_product(table,metadata,tmp_path)


def test_dfo_bilingual_population_status_unknown_dates_and_multipart_feature_identity():
    import geopandas as gpd
    from shapely.geometry import MultiPolygon,box
    from governance.shared.config import load_governance_config
    from governance.protected_areas.critical_habitat.normalize import normalize
    from governance.shared.spatial import clip_to_full_area
    from governance.memberships import prepare_records,memberships
    config=load_governance_config();source=config.sources['dfo_aquatic_critical_habitat']
    raw=gpd.GeoDataFrame([{'OBJECTID':149,'COMMON_E':'Killer Whale','POP_E':'Northeast Pacific Southern Resident',
        'COMMON_F':'Épaulard','POP_F':'résidente du sud du Pacifique Nord-Est','SCIENTIFIC':'Orcinus orca',
        'CH_STATUS_E':'Final/Proposed','ECO_TYPE_E':'Marine','Waterbody':'Pacific Ocean','LEAD_REG_E':'Pacific',
        'geometry':MultiPolygon([box(-124,48,-123.8,48.2),box(-123.5,48,-123.3,48.2)])}],crs=4326)
    normalized=normalize(raw,source)
    assert normalized.FEATURE_NAME.iloc[0]=='Killer Whale [Northeast Pacific Southern Resident]'
    assert normalized.DFO_COMMON_F.iloc[0]=='Épaulard'
    assert normalized.AREA_HIERARCHY_LEVEL.iloc[0]=='Final/Proposed'
    assert normalized.JURISDICTION.iloc[0]=='Canada'
    assert normalized.EFFECTIVE_START.isna().all() and normalized.EFFECTIVE_END.isna().all()
    assert normalized.LEGAL_BINDING_STATUS.iloc[0]=='reference_geometry'
    assert not normalized.MODEL_ELIGIBLE.any()
    native,_=clip_to_full_area(normalized,config);members=memberships(prepare_records(native),range(len(native)))
    assert len(native)==2 and len(members)==1 and len(members[0]['records'][0]['geometry_part_ids'])==2


def test_declared_partial_selection_validates_its_own_receipt_without_claiming_full_aoi(tmp_path):
    from dataclasses import replace
    import json
    from governance.shared.config import load_governance_config
    from governance.shared.acquisition import read_source_frame,CacheScopeError
    import pytest
    source=load_governance_config().sources['dfo_aquatic_critical_habitat'];path=tmp_path/'snapshot.json'
    source=replace(source,local_path=None,snapshot_path=path)
    snapshot={'snapshot_schema_version':2,'source_id':source.source_id,'source_url':source.url,'server_filtered':True,
        'requested_bbox_wgs84':list(source.selection_bbox),'geometry_roster_complete':True,'selected_object_ids':[1],
        'expected_object_id_count':1,'unreceived_object_ids':[],'object_id_field':'OBJECTID','selection_where':'1=1',
        'pages':[{'response':{'features':[{'type':'Feature','properties':{'OBJECTID':1},'geometry':{'type':'Polygon','coordinates':[[[-124,48],[-123,48],[-123,49],[-124,49],[-124,48]]]}}]}}]}
    path.write_text(json.dumps(snapshot))
    assert len(read_source_frame(source,bbox=(-180,32,-109,72)))==1
    snapshot['requested_bbox_wgs84']=[-124,48,-123,49];path.write_text(json.dumps(snapshot))
    with pytest.raises(CacheScopeError,match='smaller than request'):read_source_frame(source,bbox=(-180,32,-109,72))
