import json
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from shapely.geometry import box, Point
from governance.jurisdiction.tribal_first_nations_areas.normalize import normalize
from governance.shared.config import load_governance_config
from governance.workspace import initialize_workspace
from governance.h3_matrix import export_h3_matrix
from governance.delivery import export_delivery


def frame(**fields):
    return gpd.GeoDataFrame([fields],geometry=[box(-123.01,48.49,-122.99,48.51)],crs=4326)


def test_bia_identifies_provider_area_and_preserves_undecoded_class():
    source=load_governance_config().sources['bia_administrative_lar']
    raw=frame(OBJECTID=1,LARID='area-a',LARNAME='Provider name',CLASSIFICATION='1')
    result=normalize(raw,source)
    assert result.GOVERNANCE_FEATURE_ID.tolist()==['bia_administrative_lar:area:area-a']
    assert result.BIA_CLASSIFICATION.tolist()==['1']
    assert result[['LEGAL_AUTHORITY','LEGAL_SOURCE_URL','JURISDICTION','EFFECTIVE_START','EFFECTIVE_END']].isna().all().all()
    assert not result.MODEL_ELIGIBLE.any()
    raw.loc[0,'LARID']=None
    with pytest.raises(ValueError,match='identities'):normalize(raw,source)


def test_nrcan_reported_legal_purpose_does_not_become_legal_certification():
    source=load_governance_config().sources['nrcan_indian_reserves']
    raw=frame(OBJECTID=1,adminAreaId='a',adminAreaNameEng='Source name',distributionTypeEng='Indian Reserve',jurisdictionEng='British Columbia',representationPurposeEng='Legal')
    result=normalize(raw,source)
    assert result.NRCAN_representationPurposeEng.tolist()==['Legal']
    assert result.LEGAL_BINDING_STATUS.tolist()==['reference_geometry']
    assert result.LEGAL_AUTHORITY.isna().all()
    for field,value in [('distributionTypeEng','Sechelt Land'),('jurisdictionEng','Ontario')]:
        changed=raw.copy();changed.loc[0,field]=value
        with pytest.raises(ValueError,match='Qualified NRCan scope'):normalize(changed,source)


def test_invalid_geometry_and_duplicate_source_records_fail_closed():
    source=load_governance_config().sources['bia_administrative_lar'];raw=frame(OBJECTID=1,LARID='a')
    raw.loc[0,'geometry']=Point(-123,48.5)
    with pytest.raises(ValueError,match='polygon'):normalize(raw,source)
    raw=frame(OBJECTID=1,LARID='a');raw=gpd.GeoDataFrame(raw.loc[[0,0]].reset_index(drop=True),crs=4326)
    with pytest.raises(ValueError,match='Unique'):normalize(raw,source)


def test_provider_area_identity_deduplicates_parts_without_pooling_agencies(tmp_path,monkeypatch):
    initialize_workspace(tmp_path);monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    p=tmp_path/'config/data/governance/governance.yaml';cfg=yaml.safe_load(p.read_text())
    cfg['collections']={'tribal_first_nations_areas':cfg['collections']['tribal_first_nations_areas']};p.write_text(yaml.safe_dump(cfg))
    cfg=load_governance_config();source=cfg.sources['bia_administrative_lar'];source.snapshot_path.parent.mkdir(parents=True)
    raw=gpd.GeoDataFrame([{'OBJECTID':1,'LARID':'same-area','LARNAME':'name','CLASSIFICATION':'1'},{'OBJECTID':2,'LARID':'same-area','LARNAME':'name','CLASSIFICATION':'1'}],geometry=[box(-123.01,48.49,-122.99,48.51)]*2,crs=4326)
    source.snapshot_path.write_text(json.dumps({'snapshot_schema_version':1,'pages':[{'response':json.loads(raw.to_json())}]}))
    from governance.jurisdiction.tribal_first_nations_areas.build import build
    native=gpd.read_parquet(build(allow_partial=True));assert native.SOURCE_FEATURE_ID.nunique()==2;assert native.GOVERNANCE_FEATURE_ID.nunique()==1
    grid=tmp_path/'grid.parquet';pq.write_table(pa.table({'H3_INDEX':[h3.latlng_to_cell(48.5,-123,6)],'H3_RESOLUTION':[6]}),grid)
    matrix=export_h3_matrix(grid,tmp_path/'matrix.parquet',length_crs='EPSG:32610',allow_partial=True)
    artifact,manifest=export_delivery(matrix,tmp_path/'delivery',release_id='test',software_revision='a'*40)
    table=pq.read_table(artifact);meta=json.loads(manifest.read_text())
    prefix='tribal_first_nations_areas__'
    assert prefix+'recorded_feature_count' not in table.column_names
    assert table[prefix+'bia_land_area_reference__recorded_feature_count'].to_pylist()==[1]
    assert table[prefix+'nrcan_indian_reserve_reference__recorded_feature_count'].to_pylist()==[None]
    assert table[prefix+'nrcan_indian_reserve_reference__recorded_feature_count_status'].to_pylist()==['unavailable']
    assert 'sovereignty' in meta['coverage'][prefix+'bia_land_area_reference']['overlap_policy']
    from governance.jurisdiction.tribal_first_nations_areas.inspect import layer_descriptors
    descriptors=layer_descriptors();assert len(descriptors)==2;assert descriptors[0].filters!=descriptors[1].filters
