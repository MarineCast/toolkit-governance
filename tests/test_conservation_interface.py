"""Unique site identity, marine scope and full-cell union semantics."""
import json
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely
from shapely.geometry import Point, Polygon, box
from governance.protected_areas.marine_conservation_areas.interface import (
    prepare_sources, overlay, populate_features, GROUP, REFERENCE, COUNT, ASSIGNMENT, COVERAGE, ECCC, AOI, NOAA,
)
from governance.products import validate_metric_table


def frame(rows, geometries):
    return gpd.GeoDataFrame(rows, geometry=geometries, crs=4326)


def cpcad(oid, parent=10, zone=11, biome='M', classification=1, status=1, name='Same name'):
    return dict(OBJECTID=oid, PARENT_ID=parent, ZONE_ID=zone, BIOME=biome,
                PA_OECM_DF=classification, STATUS=status, NAME_E=name, TYPE_E='Marine park',
                MGMT_E='Provider', MECH_E='Source legal mechanism')


def test_deduplicates_parent_sites_and_keeps_all_source_records_and_zone_classifications():
    shape = box(-124,48,-123,49)
    sources = {ECCC[0]:frame([cpcad(1),cpcad(2,zone=12),cpcad(3,parent=20,zone=21,classification=2)], [shape]*3),
               ECCC[1]:frame([cpcad(1)],[shape])}
    geoms, descriptors, refs, audit, context = prepare_sources(sources)
    cell = h3.latlng_to_cell(48.5,-123.5,6)
    rows,fractions=overlay([cell],geoms,descriptors)
    assert len(rows[0]) == 2  # Parent sites, not zones, parts, inventories, or equal names.
    assert {r['source_feature_id'] for r in rows[0][0]['records']} == {ECCC[0]+':1',ECCC[0]+':2',ECCC[1]+':1'}
    assert {r['area_system_id'] for e in rows[0] for r in e['records']} == {'PA','OECM'}
    assert fractions == [pytest.approx(1.)]
    assert context[ECCC[0]+':1']['legal_mechanism']=='Source legal mechanism'
    assert not refs and not audit


def test_proposed_points_interim_and_terrestrial_stay_outside_core_totals():
    shape=box(-124,48,-123,49)
    sources={ECCC[0]:frame([cpcad(1,classification=3,status=3), cpcad(2,biome='T')],[shape]*2),
             AOI:frame([dict(OBJECTID=3,NAME_E='Race Rocks Area of Interest')],[Point(-123.5,48.5)])}
    geoms,descriptors,refs,audit,context=prepare_sources(sources)
    assert not geoms and not descriptors
    assert len(refs)==2
    assert [v['kind'] for v in audit]==['excluded_terrestrial_zone']
    assert context[AOI+':3']['designation_status'].startswith('Proposed')
    cells=[h3.latlng_to_cell(48.5,-123.5,6)]
    rows,fractions=overlay(cells,[v[0] for v in refs],[(v[1],v[2]) for v in refs],area=False)
    assert len(rows[0])==2 and fractions==[None]


def test_union_uses_full_cell_denominator_and_never_sums_overlaps():
    cell=h3.latlng_to_cell(48.5,-123.5,6)
    polygon=Polygon([(lon,lat) for lat,lon in h3.cell_to_boundary(cell)])
    west,south,east,north=polygon.bounds
    left=polygon.intersection(box(west,south,(west+east)/2,north))
    frame1=frame([cpcad(1),cpcad(2,parent=20)], [left,left])
    geoms,descriptors,*_=prepare_sources({ECCC[0]:frame1})
    rows,frac=overlay([cell],geoms,descriptors)
    projected=gpd.GeoSeries([left,polygon],crs=4326).to_crs(6933)
    expected=projected.iloc[0].intersection(projected.iloc[1]).area/projected.iloc[1].area
    assert len(rows[0])==2 and frac[0]==pytest.approx(expected,rel=1e-12)
    assert 0 < frac[0] < 1


def test_no_hit_remains_null_and_names_never_merge_sites():
    shape=box(-124,48,-123,49)
    geoms,descriptors,*_=prepare_sources({ECCC[0]:frame([cpcad(1),cpcad(2,parent=20)], [shape]*2)})
    rows,frac=overlay([h3.latlng_to_cell(20,20,6)],geoms,descriptors)
    assert rows==[None] and frac==[None]
    assert len({v[0] for v in descriptors})==2


def test_unsupported_provider_class_fails_closed():
    with pytest.raises(ValueError,match='Unqualified'):
        prepare_sources({ECCC[0]:frame([cpcad(1,classification=9)],[box(-124,48,-123,49)])})


def test_unqualified_fws_and_odfw_remain_explicit_unresolved_evidence():
    shape=box(-124,48,-123,49)
    from governance.protected_areas.marine_conservation_areas.interface import FWS,ODFW
    geoms,_,_,audit,_=prepare_sources({FWS:frame([dict(OBJECTID=1,ORGCODE=99,ORGNAME='Unknown refuge')],[shape]),
                                    ODFW:frame([dict(ODFW_RECORD_ID='ID_1',ODFW_NAME='Zone')],[shape])})
    assert not geoms
    assert {v['kind'] for v in audit}=={'excluded_unqualified_fws_marine_scope','unresolved_odfw_site_identity'}


def test_populate_checks_original_hash_and_preserves_unrelated_column(tmp_path):
    from governance.shared.artifacts import sha256_file
    source=ECCC[0];original=tmp_path/f'OriginalData/{source}/geometry.parquet';original.parent.mkdir(parents=True)
    frame([cpcad(1)],[box(-124,48,-123,49)]).to_parquet(original,index=False)
    raw=pq.read_table(original);pq.write_table(raw.replace_schema_metadata({**raw.schema.metadata,b'governance_original':json.dumps({'source':{'source_id':source}}).encode()}),original)
    cell=h3.latlng_to_cell(48.5,-123.5,6); table=pa.table({'h3_index':[cell], 'unrelated':[19.]})
    metadata={'schema_version':1,'model_eligible':False,'spatial':{'h3_resolution':6},'temporal':{'type':'static'},
              'collections':{'conservation_designations':{}}, 'fields':{'h3_index':{},'unrelated':{}},'coverage':{},
              'original_data':{source:{'path':str(original.relative_to(tmp_path)),'sha256':sha256_file(original)}}}
    result=populate_features(table,metadata,tmp_path)
    assert result['unrelated'].equals(table['unrelated'])
    assert result[COUNT].to_pylist()==[1]
    assert result[COVERAGE].to_pylist()==[pytest.approx(1.)]
    validate_metric_table(result,metadata)
    original.write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):
        populate_features(table,metadata,tmp_path)


def test_normal_build_and_export_populate_the_same_family_offline(tmp_path,monkeypatch,snapshot_fixture):
    import yaml
    from governance.workspace import initialize_workspace
    from governance.shared.config import load_governance_config
    from governance.products import build_products, validate_products
    work=tmp_path/'workspace';initialize_workspace(work);monkeypatch.setenv('GOVERNANCE_WORKSPACE',str(work))
    path=work/'config/data/governance/governance.yaml';values=yaml.safe_load(path.read_text())
    values['collections']={'marine_protected_areas':values['collections']['marine_protected_areas']}
    values['collections']['marine_protected_areas']['source_ids']=[NOAA]
    values['sources']={NOAA:values['sources'][NOAA]}
    values['sources'][NOAA].update(snapshot_path='data/raw/governance/noaa_mpa_inventory_2023/snapshot.json', expected_sha256=None, immutable_full_source_archive=False)
    path.write_text(yaml.safe_dump(values))
    source=load_governance_config(path).sources[NOAA]
    raw=frame([dict(OBJECTID=1,Site_ID='TEST',Site_Name='Test marine site',Marine='Marine',Design='Marine reserve',Mgmt_Agen='Agency')],[box(-124,48,-123,49)])
    source.snapshot_path.parent.mkdir(parents=True);source.snapshot_path.write_text(json.dumps(snapshot_fixture(source,raw)))
    grid=tmp_path/'grid.parquet';pq.write_table(pa.table({'H3_INDEX':[h3.latlng_to_cell(48.5,-123.5,6)],'H3_RESOLUTION':[6]}),grid)
    out=build_products([grid],tmp_path/'result',config_path=path,allow_partial=True,keep_workspace_data=True)
    table=pq.read_table(out/'governance-r6-static.parquet');assert table[COUNT].to_pylist()==[1]
    metadata=json.loads(table.schema.metadata[b'governance'])
    assert 'marine_protected_areas__recorded_feature_count' not in metadata['fields']
    assert metadata['fields'][COUNT]['units'] == 'count'
    assert validate_products(out)['status']=='passed'
    rebuild=build_products([grid],tmp_path/'rebuild',config_path=path,original_data=out,allow_partial=True,keep_workspace_data=True)
    assert table.equals(pq.read_table(rebuild/'governance-r6-static.parquet'),check_metadata=False)


def test_retired_ports_remove_only_physical_derivatives_and_keep_source_lineage():
    from governance.administrative_context.ports.retired import retire_delivery
    table=pa.table({'h3_index':['cell'],'ports__recorded_feature_count':[1], 'other':[7]})
    metadata={'fields':{c:{} for c in table.column_names},'coverage':{'ports':{},'other':{}},'collections':{'ports':{},'other':{}},'original_data':{'nga_world_port_index':{'sha256':'source'}}}
    result=retire_delivery(table,metadata)
    assert result.column_names==['h3_index','other'] and result['other'].equals(table['other'])
    assert 'ports' not in metadata['coverage'] and 'ports' not in metadata['collections']
    assert metadata['original_data']['nga_world_port_index']['sha256']=='source'
