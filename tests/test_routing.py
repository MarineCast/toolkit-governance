import json
from pathlib import Path
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from shapely.geometry import LineString, box
from governance.vessel_management.routing import normalize, noaa_source_frame
from governance.shared.config import load_governance_config
from governance.shared.spatial import clip_to_full_area
from governance.h3_matrix import _grid, overlay_collection, export_h3_matrix
from governance.delivery import export_delivery
from governance.workspace import initialize_workspace


def test_chart_overlap_identity_and_dates_are_preserved(tmp_path):
    config = load_governance_config()
    rows = [{'OBJECTID': i, 'MERGE_SRC': 'RECTRC_L', 'LNAM': 'same-object', 'ENC_NAME': chart,
             'DATSTA': '20260101', 'DATEND': '--1231', 'STATUS': '1', 'ORIENT': 90}
            for i, chart in [(1, 'chart-a'), (2, 'chart-b')]]
    raw = gpd.GeoDataFrame(rows, geometry=[LineString([(-123.001,48.5),(-122.999,48.5)])]*2, crs=4326)
    normalized = normalize(raw, config.sources['chs_routing_layer_5'], collection='shipping_lanes')
    assert normalized.GOVERNANCE_FEATURE_ID.nunique() == 1
    assert normalized.SOURCE_FEATURE_ID.nunique() == 2
    assert normalized.CHS_ENC_NAME.tolist() == ['chart-a','chart-b']
    assert normalized.CHS_DATEND.tolist() == ['--1231']*2
    assert normalized.EFFECTIVE_START.isna().all() and normalized.EFFECTIVE_END.isna().all()
    native, _ = clip_to_full_area(normalized, config)
    p = tmp_path/'grid.parquet'
    pq.write_table(pa.table({'H3_INDEX':[h3.latlng_to_cell(48.5,-123,6)],'H3_RESOLUTION':[6]}),p)
    grid = _grid(p)
    two = overlay_collection(grid,native,completeness='partial',length_crs='EPSG:32610')
    one = overlay_collection(grid,native.iloc[:1],completeness='partial',length_crs='EPSG:32610')
    assert two['FEATURE_COUNT'].to_pylist() == [1]
    assert two['LINE_LENGTH_M'].to_pylist() == one['LINE_LENGTH_M'].to_pylist()
    raw.loc[0,'MERGE_SRC']='FERYRT_L'
    with pytest.raises(ValueError,match='Unrecognized routing type'):
        normalize(raw,config.sources['chs_routing_layer_5'],collection='shipping_lanes')


def test_noaa_archive_preserves_fid_and_filters_nonrouting(tmp_path):
    import zipfile
    g = gpd.GeoDataFrame({'routeType':['Traffic Lane','Area To Be Avoided'],'citation':['source citation','other']},geometry=[box(-124,48,-123,49)]*2,crs=4269)
    gpkg=tmp_path/'VesselRoutingMeasure.gpkg';g.to_file(gpkg,driver='GPKG')
    z=tmp_path/'source.zip'
    with zipfile.ZipFile(z,'w') as archive:archive.write(gpkg,gpkg.name)
    raw=noaa_source_frame(z)
    assert raw.SOURCE_FID.tolist()==['1','2']
    result=normalize(raw,load_governance_config().sources['noaa_routing_2026'],collection='traffic_separation_schemes')
    assert len(result)==1 and result.ROUTING_ROLE.iloc[0]=='noaa_traffic_lane'
    assert result.NOAA_ROUTING_citation.iloc[0]=='source citation'
    assert result.LEGAL_AUTHORITY.isna().all()


def test_role_delivery_never_pools_components_sources_or_absent_roles(tmp_path,monkeypatch):
    initialize_workspace(tmp_path);monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    p=tmp_path/'config/data/governance/governance.yaml';raw=yaml.safe_load(p.read_text())
    raw['collections']={'traffic_separation_schemes':raw['collections']['traffic_separation_schemes']}
    p.write_text(yaml.safe_dump(raw));config=load_governance_config()
    source=config.sources['chs_routing_layer_4'];source.snapshot_path.parent.mkdir(parents=True)
    geom=box(-123.01,48.49,-122.99,48.51)
    features=gpd.GeoDataFrame([{'OBJECTID':1,'MERGE_SRC':'TSSLPT_A','LNAM':'a','ENC_NAME':'chart'}],geometry=[geom],crs=4326)
    source.snapshot_path.write_text(json.dumps({'snapshot_schema_version':1,'pages':[{'response':json.loads(features.to_json())}]}))
    from governance.vessel_management.traffic_separation_schemes.build import build
    build(allow_partial=True)
    gp=tmp_path/'grid.parquet';pq.write_table(pa.table({'H3_INDEX':[h3.latlng_to_cell(48.5,-123,6)],'H3_RESOLUTION':[6]}),gp)
    matrix=export_h3_matrix(gp,tmp_path/'matrix.parquet',length_crs='EPSG:32610',allow_partial=True)
    artifact,manifest=export_delivery(matrix,tmp_path/'delivery',release_id='test',software_revision='a'*40)
    table=pq.read_table(artifact);d=json.loads(manifest.read_text())
    assert 'traffic_separation_schemes__recorded_feature_count' not in table.column_names
    assert table['traffic_separation_schemes__chs_lane_part__recorded_feature_count'].to_pylist()==[1]
    assert table['traffic_separation_schemes__noaa_traffic_lane__recorded_feature_count'].to_pylist()==[None]
    assert table['traffic_separation_schemes__noaa_traffic_lane__recorded_feature_count_status'].to_pylist()==['unavailable']
    assert 'traffic_separation_schemes__chs_lane_part__recorded_line_union_length_m' not in table.column_names
    assert d['coverage']['traffic_separation_schemes__noaa_traffic_lane']['configured_source_receipt']['numerator']==0
    assert d['coverage']['traffic_separation_schemes__chs_lane_part']['configured_source_receipt']['denominator']==1
    assert d['scientific_method_version']=='native-inventory-overlay-1.3.0'
