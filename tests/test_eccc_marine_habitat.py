from copy import deepcopy
import hashlib
import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import MultiPolygon, box, Point
from governance.shared.config import load_governance_config
from governance.shared.spatial import clip_to_full_area
from governance.shared.registry import normalize_collection
from governance.memberships import prepare_records, memberships, MEMBERSHIP_TYPE, RECORD_FIELDS
from governance.protected_areas.critical_habitat.eccc import SOURCE, MARINE_AREAS, CONDITIONS
from governance.protected_areas.critical_habitat.normalize import normalize
from governance.protected_areas.critical_habitat.interface import annotate_product, COUNT, ASSIGNMENT


def raw():
    return gpd.GeoDataFrame([{'OBJECTID':21712,'COSEWIC_ID':39,'SciName':'Brachyramphus marmoratus',
        'CommName_E':'Marbled Murrelet','SiteName_E':'Sidney','ProvTerr_E':'British Columbia',
        'RD_Status':1,'RDoc_Name_E':'Amended Recovery Strategy for the Marbled Murrelet (Brachyramphus marmoratus) in Canada',
        'SiteID':None,'SARA_Status':3,'Taxon':3,'Population_E':None,'Sensitive_E':None,
        'geometry':MultiPolygon([box(-123.5,48.4,-123.4,48.5),box(-123.3,48.4,-123.2,48.5)])}],crs=4326)


def test_reviewed_marine_reference_preserves_identity_parts_attributes_and_conditions():
    config=load_governance_config();source=config.sources[SOURCE]
    assert len(MARINE_AREAS)==11 and len(set(MARINE_AREAS.values()))==11
    frame=raw();result=normalize(frame,source)
    assert result.FEATURE_NAME.iloc[0]=='Marbled Murrelet [Sidney]'
    assert result.SOURCE_FEATURE_ID.iloc[0]==SOURCE+':21712'
    assert result.ECCC_RD_Status.iloc[0]=='1' and result.ECCC_SARA_Status.iloc[0]=='3'
    assert result.ECCC_SiteID.isna().all() and result.ECCC_Population_E.isna().all()
    assert result.HABITAT_CONDITIONS.iloc[0]==CONDITIONS
    assert result.EFFECTIVE_START.isna().all() and result.EFFECTIVE_END.isna().all()
    assert not result.MODEL_ELIGIBLE.any()
    native,_=clip_to_full_area(result,config)
    members=memberships(prepare_records(native),range(len(native)))
    assert len(native)==2 and len(members)==1
    assert len(members[0]['records'][0]['geometry_part_ids'])==2


@pytest.mark.parametrize('field,value,message',[
    ('OBJECTID',21706,'marine ID/site roster'), ('OBJECTID',21708,'marine ID/site roster'),
    ('OBJECTID',21713,'marine ID/site roster'), ('OBJECTID',21714,'marine ID/site roster'),
    ('SiteName_E','Terrestrial nesting area','marine ID/site roster'),
    ('COSEWIC_ID',42,'species identity'), ('SciName','Other species','species identity'),
    ('RD_Status',2,'Posted Final'), ('RDoc_Name_E','Unreviewed document','document identity'),
    ('geometry',Point(-123.3,48.5),'polygon geometry')])
def test_unapproved_components_and_source_drift_fail_closed(field,value,message):
    frame=raw();frame.at[0,field]=value
    with pytest.raises(ValueError,match=message):
        normalize(frame,load_governance_config().sources[SOURCE])


def test_registry_rejects_missing_provider_status_before_normalization():
    config=load_governance_config()
    with pytest.raises(ValueError,match='missing required fields.*RD_Status'):
        normalize_collection(raw().drop(columns='RD_Status'),config.sources[SOURCE],config.collections['critical_habitat'])


def test_original_context_join_keeps_codes_names_and_conditional_scope(tmp_path):
    identity=SOURCE+':21712';record=dict.fromkeys(RECORD_FIELDS)
    record.update(source_dataset_id=SOURCE,source_feature_id=identity,feature_name='Marbled Murrelet [Sidney]',geometry_part_ids=['part-a'])
    table=pa.table({COUNT:pa.array([1,None],pa.int64()),ASSIGNMENT:pa.array([[{'feature_id':identity,'records':[record]}],None],MEMBERSHIP_TYPE)})
    path=tmp_path/'OriginalData'/SOURCE/'geometry.parquet';path.parent.mkdir(parents=True)
    raw().to_parquet(path,index=False)
    metadata={'fields':{name:{} for name in table.column_names},'original_data':{SOURCE:{'path':str(path.relative_to(tmp_path)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}}
    before=deepcopy(table.to_pydict());result=annotate_product(table,metadata,tmp_path)
    assert result.to_pydict()==before
    ctx=metadata['fields'][ASSIGNMENT]['source_record_context'][identity]
    assert ctx['habitat_reference_area']=='Sidney' and ctx['source_site_id'] is None
    assert ctx['recovery_document_status_code']=='1' and ctx['listing_status_code']=='3'
    assert ctx['habitat_conditions']==CONDITIONS
    assert 'conditional' in ctx['habitat_status']
    assert metadata['fields'][ASSIGNMENT]['source_context'][SOURCE]['country']=='Canada'
    assert any('withheld' in gap for gap in metadata['coverage']['critical_habitat']['scope_gaps'])


def test_existing_interpretation_upgrades_once_without_duplicating_old_qualification():
    from governance.protected_areas.critical_habitat.interface import annotate_fields, COUNT, PREVIOUS_LIMITATION, LIMITATION
    fields = {COUNT: {'interpretation': 'Original inventory definition. ' + PREVIOUS_LIMITATION}}
    annotate_fields(fields)
    assert fields[COUNT]['interpretation'] == 'Original inventory definition. ' + LIMITATION
    once = deepcopy(fields)
    annotate_fields(fields)
    assert fields == once
