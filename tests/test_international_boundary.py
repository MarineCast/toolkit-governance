import copy
import hashlib
import json
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import LineString, Polygon
from governance.jurisdiction.international_boundary import populate_features, select_lines, SOURCES, COLUMN, MEMBERS, COUNT, GROUP


def fixture(tmp_path):
    cell=h3.latlng_to_cell(48.5,-123.5,6)
    poly=Polygon([(lon,lat) for lat,lon in h3.cell_to_boundary(cell)])
    edge=LineString(list(poly.exterior.coords)[:2])
    frames=[gpd.GeoDataFrame({'SectionNum':[27],'SectionEng':['Straits of Georgia and Juan de Fuca'],'MaxScale':['1:200,000']},geometry=[edge],crs=4326),
        gpd.GeoDataFrame({'BOUND_ID':['border','eez','territorial'],'REGION':['Pacific']*3,'FEAT_TYPE':['Maritime Boundary']*3,'RULEID':[5,2,3]},geometry=[edge]*3,crs=4326),
        gpd.GeoDataFrame({'UUID':['international','province','eez'],'TYPE_E':['INTERN','PROV','EEZ_200'],'SRC_AGENCY':['IBC']*3},geometry=[edge]*3,crs=4326)]
    bindings={}
    for source,frame in zip(SOURCES,frames):
        path=tmp_path/f'OriginalData/{source}/geometry.parquet';path.parent.mkdir(parents=True);frame.to_parquet(path,index=False)
        t=pq.read_table(path);s={'source_id':source,'provider':source,'legal_citation':'mapping reference','url':'https://example.test','retrieved_at_utc':None,'source_as_of':'2018-04-19','limitation':'partial mapping reference','geometry_roster_complete':True}
        pq.write_table(t.replace_schema_metadata({**t.schema.metadata,b'governance_original':json.dumps({'source':s}).encode()}),path)
        bindings[source]={'path':str(path.relative_to(tmp_path)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    cells=[cell,h3.latlng_to_cell(47,-123.5,6)]
    table=pa.table({'h3_index':cells,'federal_waters__old_support':[12,34]})
    return table,{'fields':{n:{} for n in table.column_names},'coverage':{},'original_data':bindings},edge


def test_filters_exclude_limits_and_preserve_boundary_names_ids_and_inputs(tmp_path):
    table,meta,edge=fixture(tmp_path);result=populate_features(table,meta,tmp_path)
    assert result[COLUMN].type==pa.bool_()
    assert result[COLUMN].to_pylist()==[True,None]
    assert result[COLUMN+'_status'].to_pylist()==['partial','unknown']
    assert result[COUNT].to_pylist()==[3,None]
    records=[r for e in result[MEMBERS][0].as_py() for r in e['records']]
    assert {r['source_feature_id'] for r in records}=={SOURCES[0]+':section-27',SOURCES[1]+':border',SOURCES[2]+':international'}
    assert {r['feature_name'] for r in records}=={'Straits of Georgia and Juan de Fuca','Pacific','CGB international boundary international'}
    assert all(':original-line:' in r['geometry_part_ids'][0] for r in records)
    for name in table.column_names:assert result[name].equals(table[name])
    assert result.equals(populate_features(result,meta,tmp_path))
    assert meta['coverage'][GROUP]['source_selection_audit'][SOURCES[1]]['selected_rows']==1
    for source,extra in [(SOURCES[1],{'RULEID':[1,4,5,2,3,7,8],'BOUND_ID':[str(i) for i in range(7)]}),(SOURCES[2],{'TYPE_E':['INTERN','PROV','EEZ_200','EEZ_BB'],'UUID':[str(i) for i in range(4)]})]:
        frame=gpd.GeoDataFrame(extra,geometry=[edge]*len(next(iter(extra.values()))),crs=4326)
        assert len(select_lines(frame,source))==(3 if source==SOURCES[1] else 1)
    with pytest.raises(ValueError,match='lines'):
        select_lines(gpd.GeoDataFrame({'SectionNum':[1]},geometry=[Polygon([(0,0),(1,0),(1,1),(0,0)])],crs=4326),SOURCES[0])
    with pytest.raises(ValueError,match='identifiers'):
        select_lines(gpd.GeoDataFrame(geometry=[edge],crs=4326),SOURCES[0])


def test_closed_cells_include_shared_edges_and_vertex_only_contacts(tmp_path):
    table,meta,edge=fixture(tmp_path);vertex=edge.coords[0]
    neighbors=sorted(h3.grid_disk(table['h3_index'][0].as_py(),1))
    polygons=[Polygon([(lon,lat) for lat,lon in h3.cell_to_boundary(c)]) for c in neighbors]
    poly=polygons[neighbors.index(table['h3_index'][0].as_py())];center=poly.centroid
    contact=LineString([vertex,(vertex[0]+(vertex[0]-center.x)*.1,vertex[1]+(vertex[1]-center.y)*.1)])
    assert poly.intersection(contact).geom_type=='Point'
    path=tmp_path/meta['original_data'][SOURCES[0]]['path'];original=pq.read_schema(path).metadata[b'governance_original']
    frame=gpd.read_parquet(path);frame.geometry=[contact];frame.to_parquet(path,index=False);t=pq.read_table(path)
    pq.write_table(t.replace_schema_metadata({**t.schema.metadata,b'governance_original':original}),path)
    meta['original_data']={SOURCES[0]:{**meta['original_data'][SOURCES[0]],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
    result=populate_features(pa.table({'h3_index':neighbors,'federal_waters__old_support':[1]*len(neighbors)}),meta,tmp_path)
    assert result[COLUMN].to_pylist()==[True if p.intersects(contact) else None for p in polygons]
    assert result[COLUMN][neighbors.index(table['h3_index'][0].as_py())].as_py() is True


def test_false_requires_explicit_source_and_grid_bound_geographic_acceptance(tmp_path):
    table,meta,_=fixture(tmp_path)
    assert populate_features(table,copy.deepcopy(meta),tmp_path)[COLUMN].to_pylist()==[True,None]
    q={'status':'complete','scope':'full_supplied_cells','inventory':'actual_international_boundary_lines','evidence':'fixture accepted footprint',
       'original_source_bindings':copy.deepcopy(meta['original_data']),
       'h3_indexes_sha256':hashlib.sha256(json.dumps(sorted(table['h3_index'].to_pylist()),separators=(',',':')).encode()).hexdigest()}
    meta['coverage'][GROUP]={'geographic_inventory_coverage':q}
    complete=populate_features(table,copy.deepcopy(meta),tmp_path)
    assert complete[COLUMN].to_pylist()==[True,False]
    assert complete[MEMBERS][1].as_py()==[] and complete[COUNT][1].as_py()==0
    for key in ['evidence','h3_indexes_sha256','original_source_bindings']:
        changed=copy.deepcopy(meta);changed['coverage'][GROUP]['geographic_inventory_coverage'].pop(key)
        assert populate_features(table,changed,tmp_path)[COLUMN].to_pylist()==[True,None]
    meta['original_data'][SOURCES[0]]['sha256']='corrupt'
    with pytest.raises(ValueError,match='binding mismatch'):populate_features(table,meta,tmp_path)


def test_unavailable_sources_do_not_mean_false(tmp_path):
    table,meta,_=fixture(tmp_path);meta['original_data']={};result=populate_features(table,meta,tmp_path)
    assert result[COLUMN].to_pylist()==[None,None]
    assert result[COLUMN+'_status'].to_pylist()==['unavailable','unavailable']
