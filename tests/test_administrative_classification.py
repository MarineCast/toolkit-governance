import json
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from shapely.geometry import box
from governance.administrative_context.coast_guard_sectors.normalize import normalize as coast
from governance.protected_areas.conservation_designations.normalize import normalize as conservation, evidence_key
from governance.shared.config import load_governance_config
from governance.shared.artifacts import source_record
from governance.workspace import initialize_workspace
from governance.h3_matrix import export_h3_matrix
from governance.delivery import export_delivery


def classification(**overrides):
    row=dict(OBJECTID=1,PARENT_ID=10,ZONE_ID=11,BIOME='M',PA_OECM_DF=5,STATUS=1,NAME_E='Source name',ESTYEAR=1970,IPCA=0)
    row.update(overrides)
    return gpd.GeoDataFrame([row],geometry=[box(-123.01,48.49,-122.99,48.51)],crs=4326)


def test_coast_agencies_remain_distinct_with_no_legal_dates():
    cfg=load_governance_config()
    for source,fields,role in [('uscg_app_sectors',{'FID':23,'NAME':'Columbia River'},'uscg_sector'),('ccg_western_region',{'OBJECTID_1':1,'Name':'Western'},'ccg_administrative_region')]:
        result=coast(gpd.GeoDataFrame([fields],geometry=[box(-124,48,-123,49)],crs=4326),cfg.sources[source])
        assert result.ADMIN_UNIT_ROLE.tolist()==[role]
        assert result[['EFFECTIVE_START','EFFECTIVE_END','LEGAL_AUTHORITY','LEGAL_SOURCE_URL','JURISDICTION']].isna().all().all()
        assert not result.MODEL_ELIGIBLE.any()


def test_provider_classification_is_fail_closed_and_preserves_evidence():
    source=load_governance_config().sources['eccc_marine_classification']
    frame=conservation(classification(),source)
    assert frame.PROVIDER_CLASS_LABEL.tolist()==['Not applicable']
    assert frame.ECCC_ESTYEAR.tolist()==['1970']
    assert frame.ECCC_IPCA.tolist()==['0']
    assert frame.GOVERNANCE_FEATURE_ID.tolist()==[evidence_key(10,11)]
    assert frame.EFFECTIVE_START.isna().all() and frame.LEGAL_AUTHORITY.isna().all()
    for overrides in ({'BIOME':'T'},{'PA_OECM_DF':4},{'STATUS':2},{'ZONE_ID':None},{'PARENT_ID':10.5}):
        with pytest.raises(ValueError): conservation(classification(**overrides),source)


def test_classification_view_has_typed_metrics_and_not_applicable_is_observed(tmp_path,monkeypatch):
    initialize_workspace(tmp_path);monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    p=tmp_path/'config/data/governance/governance.yaml';cfg=yaml.safe_load(p.read_text())
    cfg['collections']={'conservation_designations':cfg['collections']['conservation_designations']};p.write_text(yaml.safe_dump(cfg))
    source=load_governance_config().sources['eccc_marine_classification'];source.snapshot_path.parent.mkdir(parents=True)
    snapshot={'snapshot_schema_version':1,'retrieved_at_utc':None,'receipt_times_by_page':True,'temporal_note':'mixed receipts','requested_grid_mask_sha256':'b'*64,'selection_where':"BIOME='M'",'selected_object_ids':[1],'pages':[{'retrieved_at_utc':'2026-10-04T15:11:49Z','cached_source':{'path':'original.json','sha256':'a'*64},'response':json.loads(classification().to_json())}]}
    source.snapshot_path.write_text(json.dumps(snapshot))
    receipt=source_record(source,source.snapshot_path)
    assert receipt['retrieved_at_utc'] is None
    assert receipt['page_receipts'][0]['retrieved_at_utc']=='2026-10-04T15:11:49Z'
    assert 'response' not in receipt['page_receipts'][0]
    assert receipt['requested_grid_mask_sha256']=='b'*64
    assert receipt['selection_where']=="BIOME='M'"
    assert receipt['selected_object_id_count']==1
    from governance.protected_areas.conservation_designations.build import build
    build(allow_partial=True)
    grid=tmp_path/'grid.parquet';pq.write_table(pa.table({'H3_INDEX':[h3.latlng_to_cell(48.5,-123,6)],'H3_RESOLUTION':[6]}),grid)
    matrix=export_h3_matrix(grid,tmp_path/'matrix.parquet',length_crs='EPSG:32610',allow_partial=True)
    artifact,manifest=export_delivery(matrix,tmp_path/'delivery',release_id='test',software_revision='a'*40)
    table=pq.read_table(artifact);meta=json.loads(manifest.read_text())
    group='conservation_designations__reported_not_applicable_designated'
    assert table[group+'__recorded_feature_count'].to_pylist()==[1]
    assert table[group+'__recorded_feature_count_status'].to_pylist()==['partial']
    assert table['conservation_designations__reported_pa_designated__recorded_feature_count'].to_pylist()==[None]
    assert 'conservation_designations__recorded_feature_count' not in table.column_names
    assert 'Non-additive classification view' in meta['coverage'][group]['overlap_policy']


def test_map_layers_preserve_agency_and_provider_class_distinctions():
    from governance.administrative_context.coast_guard_sectors.inspect import layer_descriptors as coast_layers
    from governance.protected_areas.conservation_designations.inspect import layer_descriptors as classification_layers
    a=coast_layers();b=classification_layers()
    assert len(a)==2 and len(b)==4
    assert len({x.layer_id for x in a+b})==6
    assert all(len(x.filters)==2 for x in a+b)
    assert all('SOURCE_DATASET_ID' in dict(x.filters) for x in a+b)
