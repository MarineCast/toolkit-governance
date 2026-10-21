"""Independent geometric and public-cache regressions for the reviewed defects."""
import json
import math
import zipfile
from dataclasses import replace

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from pyproj import Geod, Transformer
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon, box
from shapely.ops import transform, unary_union

from governance.shared import acquisition
from governance.shared.acquisition import CacheScopeError
from governance.shared.artifacts import sha256_file
from governance.shared.config import load_governance_config
from governance.shared.spatial import clip_to_full_area
from governance.workspace import initialize_workspace

AREA = Transformer.from_crs(4326, 6933, always_xy=True).transform

def area(geometry):
    return transform(AREA, geometry).area


def native(geometry):
    return gpd.GeoDataFrame(dict(SOURCE_DATASET_ID=['fixture'],GOVERNANCE_FEATURE_ID=['feature'],SOURCE_FEATURE_ID=['record'],GEOMETRY_PART_ID=['record:part-001']),geometry=[geometry],crs=4326)












def repaired_polygon():
    # Ring has a retraced spike outside the square: make_valid yields polygon + line.
    return Polygon([(0,0),(2,0),(2,2),(1,2),(1,3),(1,2),(0,2),(0,0)])


@pytest.mark.parametrize('east,expected_shape',[(4,box(0,0,2,2)),(1,box(0,0,1,2))])
def test_repaired_fraction_uses_polygon_units_only(east,expected_shape):
    cfg=replace(load_governance_config(),bounds=dict(min_lon=-1,min_lat=-1,max_lon=east,max_lat=4))
    frame=gpd.GeoDataFrame(dict(SOURCE_FEATURE_ID=['spike']),geometry=[repaired_polygon()],crs=4326)
    result,diagnostics=clip_to_full_area(frame,cfg)
    fraction=area(expected_shape)/area(box(0,0,2,2))
    assert result.RETAINED_MEASURE_FRACTION.iloc[0]==pytest.approx(fraction,rel=1e-10)
    assert bool(result.CLIPPED_TO_FULL_AREA.iloc[0])==(east==1)
    assert result.GEOMETRY_REPAIR_STATUS.iloc[0]=='repaired_lower_dimension_remnants_reported'
    assert diagnostics.repair_dimension_remnant_rows==1
    assert result.REPAIR_MEASURE_UNIT.iloc[0]=='square_metres'
    assert math.isfinite(result.REPAIR_MEASURE_DELTA.iloc[0])
    assert result.RETAINED_MEASURE_FRACTION.between(0,1).all()


def zip_source(tmp_path):
    shape=box(-123.1,48.4,-122.9,48.6)
    path=tmp_path/'subset.zip'
    payload=json.loads(gpd.GeoDataFrame(dict(OBJECTID=[1],AreaName=['7']),geometry=[shape],crs=4326).to_json())
    with zipfile.ZipFile(path,'w') as archive:archive.writestr('areas.geojson',json.dumps(payload))
    cfg=load_governance_config()
    source=replace(cfg.sources['wdfw_recreational_marine_areas'],local_path=None,snapshot_path=path,archive_member='areas.geojson',archive_layer=None,acquisition_type='direct_archive',expected_sha256=None)
    return source


def test_receiptless_unpinned_zip_rejected_public_read_and_acquire(tmp_path):
    source=zip_source(tmp_path)
    with pytest.raises(CacheScopeError,match='receipt'):
        acquisition.read_source_frame(source,bbox=(-124,47,-122,49))
    with pytest.raises(CacheScopeError,match='receipt'):
        acquisition.download_direct_snapshot(source)
    cfg=replace(load_governance_config(),sources={source.source_id:source})
    with pytest.raises(CacheScopeError,match='receipt'):acquisition.acquire_source(cfg,source.source_id)
    local=replace(source,local_path=source.snapshot_path)
    with pytest.raises(CacheScopeError,match='receipt'):
        acquisition.acquire_source(replace(cfg,sources={local.source_id:local}),local.source_id)


def test_receiptless_pin_alone_does_not_establish_full_source(tmp_path):
    source=zip_source(tmp_path);source=replace(source,expected_sha256=sha256_file(source.snapshot_path))
    with pytest.raises(CacheScopeError,match='receipt'):
        acquisition.read_source_frame(source,bbox=(-124,47,-122,49))


def qualified_zip(tmp_path):
    source=zip_source(tmp_path)
    return replace(source,expected_sha256=sha256_file(source.snapshot_path),server_filter=False,immutable_full_source_archive=True)


def receipt(source,**changes):
    data=dict(source_id=source.source_id,source_url=source.url,sha256=sha256_file(source.snapshot_path),provider=source.provider,source_as_of=source.source_as_of,full_source_dataset=True,selection_where=source.selection_where,requested_grid_mask_sha256=None)
    data.update(changes)
    path=source.snapshot_path.with_suffix('.zip.metadata.json');path.write_text(json.dumps(data))
    return path


def test_qualified_receiptless_pinned_archive_public_paths(tmp_path):
    source=qualified_zip(tmp_path)
    assert len(acquisition.read_source_frame(source,bbox=(-124,47,-122,49)))==1
    assert acquisition.download_direct_snapshot(source)==source.snapshot_path
    cfg=replace(load_governance_config(),sources={source.source_id:source})
    assert acquisition.acquire_source(cfg,source.source_id)==source.snapshot_path
    assert acquisition.read_source_frame(source).attrs['retrieved_at_utc'] is None
    with pytest.raises(ValueError,match='checksum'):
        acquisition.read_source_frame(replace(source,expected_sha256='0'*64),bbox=(-124,47,-122,49))
    for changes in [dict(selection_where='OBJECTID=1'),dict(requested_grid_mask_sha256='a'*64),dict(server_filter=True),dict(immutable_full_source_archive='true')]:
        with pytest.raises(CacheScopeError):
            acquisition.read_source_frame(replace(source,**changes),bbox=(-124,47,-122,49))


@pytest.mark.parametrize('changes',[dict(full_source_dataset=True),dict(full_source_dataset=False,geometry_roster_complete=True,requested_bbox_wgs84=[-125,46,-121,50])])
def test_valid_compatible_zip_receipt_accepted(tmp_path,changes):
    source=zip_source(tmp_path);receipt(source,**changes)
    assert len(acquisition.read_source_frame(source,bbox=(-124,47,-122,49)))==1


@pytest.mark.parametrize('changes',[dict(full_source_dataset=False,geometry_roster_complete=True,requested_bbox_wgs84=[-123.1,48.4,-122.9,48.6]),dict(selection_where='OBJECTID=2'),dict(requested_grid_mask_sha256='a'*64),dict(archive_member='wrong.geojson'),dict(source_as_of='wrong')])
def test_incompatible_zip_receipt_rejected(tmp_path,changes):
    source=qualified_zip(tmp_path);receipt(source,**changes)
    with pytest.raises(CacheScopeError):acquisition.read_source_frame(source,bbox=(-124,47,-122,49))


@pytest.mark.parametrize('payload',['{','[]','null',json.dumps(dict(source_id='wrong',sha256='0'*64))])
def test_bad_existing_receipt_never_uses_legacy_exception(tmp_path,payload):
    source=qualified_zip(tmp_path);path=receipt(source);path.write_text(payload)
    with pytest.raises(CacheScopeError):acquisition.read_source_frame(source,bbox=(-124,47,-122,49))
    with pytest.raises(CacheScopeError):acquisition.download_direct_snapshot(source)


@pytest.mark.parametrize('kind',['directory','broken_symlink'])
def test_nonfile_existing_receipt_never_uses_legacy_exception(tmp_path,kind):
    source=qualified_zip(tmp_path)
    path=source.snapshot_path.with_suffix('.zip.metadata.json')
    if kind == 'directory':path.mkdir()
    else:path.symlink_to(tmp_path/'missing-receipt')
    with pytest.raises(CacheScopeError):acquisition.read_source_frame(source,bbox=(-124,47,-122,49))


def test_direct_failed_refresh_preserves_pair(tmp_path,monkeypatch):
    source=qualified_zip(tmp_path);metadata=receipt(source);before=(source.snapshot_path.read_bytes(),metadata.read_bytes())
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_content(self,chunk_size):yield before[0]
    monkeypatch.setattr(acquisition.requests,'get',lambda *args,**kwargs:Response())
    original=acquisition.os.replace
    def fail(staged,destination):
        if str(staged).endswith('metadata.json'):raise OSError('injected metadata failure')
        return original(staged,destination)
    monkeypatch.setattr(acquisition.os,'replace',fail)
    with pytest.raises(OSError,match='injected'):acquisition.download_direct_snapshot(source,overwrite=True)
    assert before==(source.snapshot_path.read_bytes(),metadata.read_bytes())
    assert len(acquisition.read_source_frame(source,bbox=(-124,47,-122,49)))==1
    source=replace(source,expected_sha256='0'*64)
    with pytest.raises(ValueError,match='checksum'):acquisition.download_direct_snapshot(source,overwrite=True)
    assert before==(source.snapshot_path.read_bytes(),metadata.read_bytes())


def test_nested_dimension_measure_excludes_other_units():
    from governance.shared.spatial import _measure, _parts
    polygon=box(.2,.2,1,1)
    shape=GeometryCollection([GeometryCollection([MultiPolygon([polygon]),Point(0,0)]),LineString([(0,0),(1,0)])])
    assert len(_parts(shape,'polygon'))==1
    assert _measure(shape,family='polygon')==pytest.approx(area(polygon))
    assert _measure(shape,family='line')==pytest.approx(Geod(ellps='WGS84').inv(0,0,1,0)[2])
    assert _measure(shape,family='point')==1
    with pytest.raises(ValueError,match='explicit'): _measure(shape)


def test_measurement_errors_not_hidden_and_lost_dimension_fails(monkeypatch):
    import governance.shared.spatial as spatial
    cfg=replace(load_governance_config(),bounds=dict(min_lon=-1,min_lat=-1,max_lon=4,max_lat=4))
    frame=gpd.GeoDataFrame(dict(SOURCE_FEATURE_ID=['x']),geometry=[Polygon([(0,0),(1,0),(2,0)])],crs=4326)
    with pytest.raises(ValueError,match='loses source dimension'):clip_to_full_area(frame,cfg)
    frame.geometry=[box(0,0,1,1)]
    values=iter([1.,2.])
    monkeypatch.setattr(spatial,'_measure',lambda *args,**kwargs:next(values))
    with pytest.raises(ValueError,match='exceeds'):clip_to_full_area(frame,cfg)






def test_archive_qualification_config_validation(tmp_path):
    import yaml
    initialize_workspace(tmp_path);cfg=load_governance_config(workspace=tmp_path)
    base=yaml.safe_load(cfg.path.read_text())
    for changes in [dict(expected_sha256=None),dict(immutable_full_source_archive='true'),dict(selection_where='id=1'),dict(server_filter=True),dict(requested_grid_mask_sha256='a'*64),dict(acquisition_type='arcgis')]:
        data=json.loads(json.dumps(base));data['sources']['census_counties_2025'].update(changes);cfg.path.write_text(yaml.safe_dump(data))
        with pytest.raises(ValueError):load_governance_config(workspace=tmp_path)


@pytest.mark.parametrize('area_code',[21,22,103,109,110,111])
def test_qualified_dfo_zero_subarea_is_known_provider_identifier(tmp_path,snapshot_fixture,area_code):
    initialize_workspace(tmp_path);cfg=load_governance_config(workspace=tmp_path)
    source=cfg.sources['dfo_pacific_fishery_management_areas']
    # Synthetic geometry/UUID; only the small published area/subarea identifier is reproduced.
    raw=gpd.GeoDataFrame(dict(OBJECTID=[1],MGNT_AREA=[area_code],SUBAREA_=[0],GLOBALID=['{01234567-89ab-cdef-0123-456789abcdef}'],NAME=[f'Subarea {area_code}-0']),geometry=[box(-123.1,48.4,-122.9,48.6)],crs=4326)
    source.snapshot_path.parent.mkdir(parents=True);source.snapshot_path.write_text(json.dumps(snapshot_fixture(source,raw)))
    from governance.fisheries_management.management_areas.pacific import normalize
    result=normalize(raw,source)
    assert result.AREA_CODE.tolist()==[f'{area_code}-0']
    assert result.PARENT_AREA_CODE.tolist()==[str(area_code)]
    assert result.DFO_PFMA_SUBAREA_.tolist()==['0']
    assert result.AREA_HIERARCHY_LEVEL.tolist()==['subarea']


@pytest.mark.parametrize('field,value',[('MGNT_AREA',0),('MGNT_AREA',-1),('MGNT_AREA',True),('MGNT_AREA',np.bool_(True)),('MGNT_AREA',21.5),('MGNT_AREA',None),('SUBAREA_',None),('SUBAREA_',-1),('SUBAREA_',False),('SUBAREA_',np.bool_(False)),('SUBAREA_',.5),('SUBAREA_','invalid')])
def test_dfo_identifiers_reject_unknown_or_malformed(field,value):
    from governance.fisheries_management.management_areas.pacific import normalize
    source=load_governance_config().sources['dfo_pacific_fishery_management_areas']
    raw=gpd.GeoDataFrame(dict(OBJECTID=[1],MGNT_AREA=[21],SUBAREA_=[0],GLOBALID=['{01234567-89ab-cdef-0123-456789abcdef}']),geometry=[box(-123,48,-122,49)],crs=4326)
    raw[field]=value
    with pytest.raises(ValueError):normalize(raw,source)
    raw['MGNT_AREA']=19;raw['SUBAREA_']=0
    with pytest.raises(ValueError,match='unqualified'):normalize(raw,source)






def test_fully_retained_dateline_line_uses_consistent_split_vertices():
    cfg=replace(load_governance_config(),bounds=dict(min_lon=178,min_lat=49,max_lon=-178,max_lat=51))
    frame=gpd.GeoDataFrame(dict(SOURCE_FEATURE_ID=['line']),geometry=[LineString([(179,50),(-179,50)])],crs=4326)
    result,_=clip_to_full_area(frame,cfg)
    assert result.RETAINED_MEASURE_FRACTION.tolist()==pytest.approx([1.,1.],rel=1e-10)
    assert not result.CLIPPED_TO_FULL_AREA.any()
