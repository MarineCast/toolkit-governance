"""Synthetic regional/provider contracts plus an opt-in bounded live smoke."""
import io
import json
import os
import zipfile
from dataclasses import replace
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon, box
from governance.shared.acquisition import AcquisitionBudget
from governance.shared.config import load_governance_config
from governance.shared.registry import normalize_collection
from governance.shared.spatial import clip_to_full_area
from governance.workspace import initialize_workspace

REGIONS=json.loads((Path(__file__).parent/'fixtures/regional_queries.json').read_text())['regions']

@pytest.mark.parametrize('region',list(REGIONS))
def test_regional_fixture_native_h3(region,tmp_path,snapshot_fixture):
    initialize_workspace(tmp_path);cfg=load_governance_config(workspace=tmp_path)
    west,south,east,north=REGIONS[region]
    polygon=Polygon([(west,south),(east,south),(east,north),(west,north)])
    source=cfg.sources['adfg_groundfish_statistical_areas']
    raw=gpd.GeoDataFrame({'OBJECTID':[1],'STAT_AREA':[745001],'GEOMETRY_START_DATE':['2001-01-01'],'GEOMETRY_END_DATE':[None]},geometry=[polygon],crs=4326)
    source.snapshot_path.parent.mkdir(parents=True)
    source.snapshot_path.write_text(json.dumps(snapshot_fixture(source,raw,bbox=(-180,-90,180,90))))
    from governance.fisheries_management.management_areas.alaska import normalize
    native=normalize(raw,source)
    assert not native.empty
    assert native.AREA_SYSTEM_ID.tolist()[0]=='adfg.groundfish.statistical'
    assert native.EFFECTIVE_START.isna().all()



def kml_archive(tmp_path):
    kml='''<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark id="ID_fixture"><name>Fixture Marine Reserve</name><MultiGeometry><Polygon><outerBoundaryIs><LinearRing><coordinates>-124,44 -123,44 -123,45 -124,45 -124,44</coordinates></LinearRing></outerBoundaryIs><innerBoundaryIs><LinearRing><coordinates>-123.8,44.2 -123.2,44.2 -123.2,44.8 -123.8,44.8 -123.8,44.2</coordinates></LinearRing></innerBoundaryIs></Polygon></MultiGeometry></Placemark></Document></kml>'''
    kmz=io.BytesIO()
    with zipfile.ZipFile(kmz,'w') as archive:archive.writestr('doc.kml',kml)
    path=tmp_path/'fixture.zip'
    with zipfile.ZipFile(path,'w') as archive:archive.writestr('OregonMarineReserves_KMZ_GoogleEarth.kmz',kmz.getvalue())
    return path


def test_oregon_parser_preserves_holes_source_identity_and_zero_history(tmp_path):
    from governance.protected_areas.marine_protected_areas.oregon import source_frame
    cfg=load_governance_config();source=cfg.sources['odfw_marine_reserves_2016']
    raw=source_frame(kml_archive(tmp_path));native=normalize_collection(raw,source,cfg.collections['marine_protected_areas'])
    assert len(native.geometry.iloc[0].interiors)==1
    assert native.SOURCE_RECORD_ID.tolist()==['ID_fixture']
    assert native.EFFECTIVE_START.isna().all()
    assert native.SOURCE_MARINE_AREA_KM2.isna().all()


def tc_fixture():
    def table(section,names):
        rows=[]
        for name,coast in names:
            rows.append(f'<tr><th>{name}</th></tr>')
            for index,(lat,lon) in enumerate([('48°34.000’N','125°06.000’W'),('48°32.000’N','125°06.000’W'),('48°32.000’N','125°01.000’W'),('48°34.000’N','125°06.000’W')]):
                instruction='beginning at' if index==0 else 'then along the coastline to' if coast and index==3 else 'then to'
                rows.append(f'<tr><td>{instruction}</td><td>{lat}</td><td>{lon}</td><td>Fixture</td></tr>')
        return f'<h2 id="{section}">{section}</h2><table>'+''.join(rows)+'</table>'
    return 'Version 2026 June 1, 2026 November 30, 2026'+table('schedule2',[('1. Saturna Island',False),('2. Pender Island',False)])+table('schedule3',[('1. Mouth of the Nitinat River',True),('2. Swiftsure Bank',False)])


def test_fixed_instrument_clauses_units_dates_and_unresolved_coastline(tmp_path):
    from governance.vessel_management.fixed_rules import source_frame, normalize
    path=tmp_path/'instrument.html';path.write_text(tc_fixture())
    raw=source_frame(path);assert raw.TC_ZONE_ID.tolist()==['saturna','pender','swiftsure']
    source=load_governance_config().sources['tc_srkw_interim_order_2026']
    speed=normalize(raw,source,collection='speed_restriction_zones')
    assert speed.ORIGINAL_QUANTITY.tolist()==[10.] and speed.ORIGINAL_UNIT.tolist()==['knots over ground']
    assert speed.EFFECTIVE_START.tolist()==['2026-06-01'] and speed.EFFECTIVE_END.tolist()==['2026-11-30']
    assert speed.INSTRUMENT_VERSION.tolist()==['2026-05-22']
    assert '7(2)' in speed.EXCEPTIONS.iloc[0]
    path.write_text(tc_fixture().replace('then along the coastline to','then to'))
    with pytest.raises(ValueError,match='support contract'):source_frame(path)






def test_pacific_subarea_hierarchy_native_identity_and_cross_system_codes(tmp_path,snapshot_fixture):
    from governance.fisheries_management.management_areas.pacific import normalize
    initialize_workspace(tmp_path);cfg=load_governance_config(workspace=tmp_path)
    source=cfg.sources['dfo_pacific_fishery_management_areas']
    raw=gpd.GeoDataFrame({'OBJECTID':[1],'MGNT_AREA':[19],'SUBAREA_':[1],'GLOBALID':['{01234567-89ab-cdef-0123-456789abcdef}'],'NAME':['19-1'],'SQ_KM':[1.]},geometry=[box(-123.5,48.4,-123.4,48.5)],crs=4326)
    native=normalize(raw,source)
    assert native.AREA_CODE.tolist()==['19-1'] and native.PARENT_AREA_CODE.tolist()==['19']
    assert native.AREA_HIERARCHY_LEVEL.tolist()==['subarea'] and native.EFFECTIVE_START.isna().all()
    assert native.DFO_PFMA_SQ_KM.tolist()==['1.0']
    source.snapshot_path.parent.mkdir(parents=True)
    source.snapshot_path.write_text(json.dumps(snapshot_fixture(source,raw)))
    assert len(native)==1 and native.AREA_SYSTEM_ID.tolist()==['dfo.pacific.pfma.subareas']
    for field,value in [('MGNT_AREA',None),('SUBAREA_',-1),('GLOBALID','bad')]:
        changed=raw.copy();changed[field]=value
        with pytest.raises(ValueError):normalize(changed,source)




def test_fixed_zone_native_build_handles_relational_coordinate_metadata(tmp_path,monkeypatch):
    import yaml
    from governance.shared.artifacts import sha256_file,load_manifest
    initialize_workspace(tmp_path);cfg=load_governance_config(workspace=tmp_path)
    source=cfg.sources['tc_srkw_interim_order_2026'];source.snapshot_path.parent.mkdir(parents=True)
    source.snapshot_path.write_text(tc_fixture())
    source.snapshot_path.with_suffix('.html.metadata.json').write_text(json.dumps(dict(source_id=source.source_id,source_url=source.url,sha256=sha256_file(source.snapshot_path),full_source_dataset=True,retrieved_at_utc='2026-10-01T00:00:00Z')))
    data=yaml.safe_load(cfg.path.read_text());data['sources'][source.source_id]['expected_sha256']=sha256_file(source.snapshot_path)
    cfg.path.write_text(yaml.safe_dump(data));monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(tmp_path))
    from governance.vessel_management.exclusion_zones.build import build
    path=build(allow_partial=True)
    native=gpd.read_parquet(path)
    assert len(native)==2 and 'TC_COORDINATE_ROWS' in native
    manifest=load_manifest(path.parent/'manifest.json')
    assert len(manifest['semantic_sha256'])==64
