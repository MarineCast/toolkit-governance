"""Offline correctness and public-contract regressions; no legal/regional certification."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
import yaml
from shapely.geometry import LineString, MultiPoint, Polygon, box, Point

from governance._config.document import ConfigDocument
from governance.shared import acquisition
from governance.shared.acquisition import AcquisitionBudget, CacheScopeError, SourceUnavailableError
from governance.shared.artifacts import load_manifest, publish_native_pair, manifest_payload, sha256_file
from governance.shared.config import load_governance_config
from governance.shared.normalization import date_value, source_date
from governance.shared.schema import validate_governance_geometry
from governance.shared.spatial import clip_to_full_area
from governance.workspace import initialize_workspace


def configured(tmp_path):
    initialize_workspace(tmp_path)
    return load_governance_config(workspace=tmp_path)


def cached_area(config, snapshot_fixture, *, bbox=(-180,32,-109,72), raw=None):
    source = config.sources['wdfw_recreational_marine_areas']
    if raw is None:
        raw = gpd.GeoDataFrame({'OBJECTID':[1], 'AreaName':['7']}, geometry=[box(-123.1,48.4,-122.9,48.6)], crs=4326)
    source.snapshot_path.parent.mkdir(parents=True,exist_ok=True)
    receipt = snapshot_fixture(source, raw, bbox=bbox)
    source.snapshot_path.write_text(json.dumps(receipt))
    return source, raw, receipt


def test_date_parser_declared_ms_ambiguous_and_schema_drift():
    assert date_value(1590969600000, encoding='arcgis_epoch_ms') == '2020-06-01'
    assert date_value(0, encoding='arcgis_epoch_ms') == '1970-01-01'
    assert date_value(None) is None
    for value in [1590969600000, '2020', '01/06/2020', 'nonsense', '2020-02-30']:
        with pytest.raises(ValueError): date_value(value)
    frame=gpd.GeoDataFrame(geometry=[])
    frame.attrs['layer_metadata']={'fields':[{'name':'date','type':'esriFieldTypeDouble'}]}
    with pytest.raises(ValueError,match='schema drift'):source_date(frame,'date',1590969600000,arcgis_date=True)




def test_dateline_half_line_and_multipart_points():
    config=load_governance_config()
    raw=gpd.GeoDataFrame({'SOURCE_FEATURE_ID':['dateline','points']},geometry=[LineString([(179,50),(-179,50)]),MultiPoint([(-123,48),(0,0)])],crs=4326)
    result,_=clip_to_full_area(raw,config)
    assert result.loc[result.SOURCE_FEATURE_ID.eq('dateline'),'RETAINED_MEASURE_FRACTION'].iloc[0] == pytest.approx(.5,rel=1e-3)
    assert result.loc[result.SOURCE_FEATURE_ID.eq('points'),'RETAINED_MEASURE_FRACTION'].iloc[0] == .5


def test_wrapped_hole_polygon_multipart_boundary_and_empty():
    config=replace(load_governance_config(),bounds=dict(min_lon=178.,min_lat=49.,max_lon=-178.,max_lat=54.))
    polygon=Polygon([(179,50),(-179,50),(-179,53),(179,53),(179,50)],holes=[[(-179.7,51),(179.7,51),(179.7,52),(-179.7,52),(-179.7,51)]])
    raw=gpd.GeoDataFrame({'SOURCE_FEATURE_ID':['hole','outside','touch']},geometry=[polygon,Point(0,0),box(177,50,178,51)],crs=4326)
    result,diagnostics=clip_to_full_area(raw,config)
    assert diagnostics.excluded_rows == 2 # Polygon boundary-touch has no positive-area polygon part.
    assert result.geometry.is_valid.all()
    assert result.RETAINED_MEASURE_FRACTION.tolist() == pytest.approx([1.,1.])
    assert not result.geometry.union_all().covers(Point(179.9,51.5))


def arcgis_fake(monkeypatch, ids=(1,2,3), *, short=True, duplicate=False, missing=False):
    calls=[]
    def response(url, *, params, timeout):
        calls.append(params.copy())
        if not url.endswith('/query'):
            return {'maxRecordCount':3,'objectIdField':'OBJECTID','fields':[{'name':'OBJECTID','type':'esriFieldTypeOID'}]}
        if params.get('returnIdsOnly'):
            return {'objectIds':list(ids)}
        batch=list(map(int,params['objectIds'].split(',')))
        chosen=batch[:1] if short and len(batch)>1 else batch
        if missing:chosen=[]
        if duplicate:chosen=chosen*2
        return {'features':[{'type':'Feature','properties':{'OBJECTID':i},'geometry':{'type':'Point','coordinates':[-123,48]}} for i in chosen], 'exceededTransferLimit': len(chosen)<len(batch)}
    monkeypatch.setattr(acquisition,'_response_json',response)
    return calls


def test_arcgis_short_batches_complete_and_invalid_refresh_preserves_cache(tmp_path,monkeypatch):
    source=replace(load_governance_config().sources['wdfw_recreational_marine_areas'],snapshot_path=tmp_path/'cache.json')
    arcgis_fake(monkeypatch)
    path=acquisition.download_arcgis_snapshot(source,bbox=(-124,47,-122,49))
    payload=json.loads(path.read_text());assert payload['geometry_roster_complete'] and payload['expected_object_id_count']==3
    original=path.read_bytes()
    for kwargs in [dict(duplicate=True),dict(missing=True)]:
        arcgis_fake(monkeypatch,**kwargs)
        with pytest.raises(SourceUnavailableError):acquisition.download_arcgis_snapshot(source,bbox=(-124,47,-122,49),overwrite=True)
        assert path.read_bytes()==original
    arcgis_fake(monkeypatch)
    with pytest.raises(SourceUnavailableError,match='budget'):acquisition.download_arcgis_snapshot(source,bbox=(-124,47,-122,49),overwrite=True,budget=AcquisitionBudget(max_pages=2))
    assert path.read_bytes()==original
    assert not list(tmp_path.glob('.acquisition-*'))


def test_arcgis_pagination_empty_short_pages_offset_window_and_count(tmp_path,monkeypatch):
    source=replace(load_governance_config().sources['wdfw_recreational_marine_areas'],snapshot_path=tmp_path/'cache.json')
    offsets=[]
    def response(url,*,params,timeout):
        if not url.endswith('/query'):return {'objectIdField':'OBJECTID','maxRecordCount':2,'advancedQueryCapabilities':{'supportsPagination':True,'supportsOrderBy':True}}
        if params.get('returnIdsOnly'):raise acquisition.ArcGISError(url,{'code':400})
        if params.get('returnCountOnly'):return {'count':2}
        offset=params['resultOffset'];offsets.append(offset)
        ids={0:[1],2:[],4:[2]}[offset]
        return {'features':[{'type':'Feature','properties':{'OBJECTID':i},'geometry':{'type':'Point','coordinates':[-123,48]}} for i in ids],'exceededTransferLimit':offset<4}
    monkeypatch.setattr(acquisition,'_response_json',response)
    acquisition.download_arcgis_snapshot(source,bbox=(-124,47,-122,49))
    assert offsets == [0,2,4]


def test_cache_scope_mask_pin_and_tamper(tmp_path,snapshot_fixture):
    cfg=configured(tmp_path);source,raw,receipt=cached_area(cfg,snapshot_fixture,bbox=(-124,47,-122,49))
    assert len(acquisition.read_source_frame(source,bbox=(-123.1,48.4,-122.9,48.6)))==1
    with pytest.raises(CacheScopeError,match='scope'):acquisition.read_source_frame(source,bbox=(-125,46,-121,50))
    with pytest.raises(CacheScopeError,match='selector'):acquisition.read_source_frame(replace(source,selection_where='OBJECTID=1'),bbox=(-123.1,48.4,-122.9,48.6))
    with pytest.raises(CacheScopeError,match='mask'):acquisition.read_source_frame(replace(source,requested_grid_mask_sha256='a'*64),bbox=(-123.1,48.4,-122.9,48.6))
    with pytest.raises(ValueError,match='checksum'):acquisition.read_source_frame(replace(source,expected_sha256='0'*64))
    receipt['selected_object_ids'].append(2);source.snapshot_path.write_text(json.dumps(receipt))
    with pytest.raises(CacheScopeError,match='roster'):acquisition.read_source_frame(source,bbox=(-123.1,48.4,-122.9,48.6))








def test_proposal_exclusion_marine_zero_and_source_drift(tmp_path,snapshot_fixture):
    cfg=configured(tmp_path)
    from governance.protected_areas.marine_protected_areas.normalize import normalize
    raw=gpd.GeoDataFrame({'site_id':['x'],'AreaMar':[0.],'AreaKm':[10.],'estab_yr':['2020']},geometry=[box(-124,44,-123,45)],crs=4326)
    native=normalize(raw,cfg.sources['noaa_mpa_inventory_2023'])
    assert native.SOURCE_MARINE_AREA_KM2.tolist()==[0.] and native.SOURCE_AREA_KM2.tolist()==[0.]
    assert native.SOURCE_TOTAL_SITE_AREA_KM2.tolist()==[10.] and native.EFFECTIVE_START.isna().all()
    from governance.shared.registry import normalize_collection
    source=cfg.sources['wdfw_recreational_marine_areas']
    raw=gpd.GeoDataFrame({'OBJECTID':[1]},geometry=[box(-124,47,-122,49)],crs=4326)
    with pytest.raises(ValueError,match='schema drift'):
        normalize_collection(raw,source,cfg.collections['management_areas'])






def test_config_typo_boolean_cycle(tmp_path):
    cfg=configured(tmp_path);p=cfg.path;data=yaml.safe_load(p.read_text())
    data['clipping']['typo']=True;p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError,match='Unknown clipping'):load_governance_config(workspace=tmp_path)
    del data['clipping']['typo'];data['sources']['wdfw_recreational_marine_areas']['server_filter']='false';p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError,match='boolean'):load_governance_config(workspace=tmp_path)
    p.write_text('a: ${b}\nb: ${a}\n')
    with pytest.raises(ValueError,match='reference cycle'):ConfigDocument.load(p,workspace=tmp_path)




def test_empty_mpa_builder_and_secondary_publishers(tmp_path,snapshot_fixture,monkeypatch):
    cfg=configured(tmp_path);source=cfg.sources['dfo_oceans_act_marine_protected_areas']
    source.snapshot_path.parent.mkdir(parents=True)
    raw=gpd.GeoDataFrame({'OBJECTID':pd.Series(dtype='int'),'NAME_E':pd.Series(dtype='str'),'ZONE_E':pd.Series(dtype='str')},geometry=[],crs=4326)
    source.snapshot_path.write_text(json.dumps(snapshot_fixture(source,raw)))
    config_data=yaml.safe_load(cfg.path.read_text())
    config_data['collections']={'marine_protected_areas':config_data['collections']['marine_protected_areas']}
    config_data['collections']['marine_protected_areas']['source_ids']=[source.source_id]
    cfg.path.write_text(yaml.safe_dump(config_data))
    monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    from governance.protected_areas.marine_protected_areas.build import build
    path=build(config_path=cfg.path,allow_partial=True)
    assert gpd.read_parquet(path).empty
    manifest=load_manifest(path.parent/'manifest.json')
    assert manifest['valid_empty_result'] is True
    assert gpd.read_parquet(path).empty
    assert manifest['source_authority_evaluation']['retained_us_designations'] == 0
    assert manifest['designation_counts'] == {}
    assert {item.name for item in path.parent.iterdir()} == {path.name, 'manifest.json'}






def test_pydantic_validation_remains_a_supported_configuration_extension(tmp_path):
    from pydantic import BaseModel,ConfigDict,ValidationError
    class Extension(BaseModel):
        model_config=ConfigDict(extra='forbid')
        value:int
    p=tmp_path/'extension.yaml';p.write_text('value: 7\n')
    assert ConfigDocument.load(p).validate_as(Extension).value==7
    p.write_text('value: 7\ntypo: true\n')
    with pytest.raises(ValidationError):ConfigDocument.load(p).validate_as(Extension)


def test_bare_vector_pin_is_not_a_scope_receipt(tmp_path):
    source=load_governance_config().sources['wdfw_recreational_marine_areas']
    path=tmp_path/'subset.parquet'
    gpd.GeoDataFrame({'OBJECTID':[1],'AreaName':['7']},geometry=[box(-123.1,48.4,-122.9,48.6)],crs=4326).to_parquet(path,index=False)
    source=replace(source,local_path=path,expected_sha256=sha256_file(path))
    with pytest.raises(CacheScopeError,match='scope'):acquisition.read_source_frame(source,bbox=(-124,47,-122,49))
    path.with_suffix('.parquet.metadata.json').write_text(json.dumps(dict(source_id=source.source_id,source_url=source.url,sha256=sha256_file(path),geometry_roster_complete=True,requested_bbox_wgs84=[-123.1,48.4,-122.9,48.6])))
    with pytest.raises(CacheScopeError,match='smaller'):acquisition.read_source_frame(source,bbox=(-124,47,-122,49))


def test_shapefile_dataset_pin_covers_sidecars_without_circular_receipt_hash(tmp_path):
    from governance.shared.artifacts import sha256_dataset
    source=load_governance_config().sources['wdfw_recreational_marine_areas']
    path=tmp_path/'vector.shp'
    gpd.GeoDataFrame({'OBJECTID':[1],'AreaName':['7']},geometry=[box(-123.1,48.4,-122.9,48.6)],crs=4326).to_file(path)
    digest=sha256_dataset(path)
    source=replace(source,local_path=path,expected_sha256=digest)
    path.with_suffix('.shp.metadata.json').write_text(json.dumps(dict(source_id=source.source_id,source_url=source.url,sha256=digest,full_source_dataset=True)))
    assert sha256_dataset(path)==digest
    assert len(acquisition.read_source_frame(source,bbox=(-124,47,-122,49)))==1
    with path.with_suffix('.dbf').open('ab') as handle:handle.write(b'changed')
    with pytest.raises(ValueError,match='checksum'):acquisition.read_source_frame(source,bbox=(-124,47,-122,49))


def test_native_repeated_dates_still_reject_late_invalid_values(tmp_path,snapshot_fixture):
    cfg=configured(tmp_path);source,raw,_=cached_area(cfg,snapshot_fixture)
    from governance.shared.registry import normalize_collection
    native,_=clip_to_full_area(normalize_collection(raw,source,cfg.collections['management_areas']),cfg)
    frame=gpd.GeoDataFrame(pd.concat([native]*3,ignore_index=True),crs=native.crs)
    frame['GEOMETRY_PART_ID']=['part0','part1','part2']
    frame['EFFECTIVE_START']=['2020-06-01']*3
    frame['SYSTEM_LEARNED_AT']=['2026-10-14T00:00:00Z']*3
    validate_governance_geometry(frame)
    for field,bad in [('EFFECTIVE_START','2020-02-30'),('EFFECTIVE_START',1590969600000),
                      ('SYSTEM_LEARNED_AT','badZ'),('SYSTEM_LEARNED_AT','2026-10-14T00:00:00+01:00')]:
        changed=frame.copy();changed[field]=changed[field].astype(object);changed.loc[2,field]=bad
        with pytest.raises(ValueError):validate_governance_geometry(changed)


def test_native_pair_failure_restores_prior_outputs(tmp_path,snapshot_fixture,monkeypatch):
    cfg=configured(tmp_path);source,raw,_=cached_area(cfg,snapshot_fixture)
    from governance.shared.registry import normalize_collection
    native,_=clip_to_full_area(normalize_collection(raw,source,cfg.collections['management_areas']),cfg)
    collection=cfg.collections['management_areas']
    payload=manifest_payload(config=cfg,collection=collection,frame=native,sources=[],clip_diagnostics=[],limitations=[])
    publish_native_pair(native,collection.artifact_path,collection.manifest_path,payload)
    original=(collection.artifact_path.read_bytes(),collection.manifest_path.read_bytes())
    import governance.shared.artifacts as artifacts
    original_replace=artifacts.os.replace
    def fail(source,dest):
        if str(source).endswith('.manifest.part'):raise OSError('injected manifest replacement failure')
        return original_replace(source,dest)
    monkeypatch.setattr(artifacts.os,'replace',fail)
    with pytest.raises(OSError):publish_native_pair(native,collection.artifact_path,collection.manifest_path,payload,overwrite=True)
    assert original==(collection.artifact_path.read_bytes(),collection.manifest_path.read_bytes())
    load_manifest(collection.manifest_path)
