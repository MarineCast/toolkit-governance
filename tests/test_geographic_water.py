import copy
import hashlib
import json
from pathlib import Path
import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import box, Polygon
from governance.memberships import RECORD_FIELDS, MEMBERSHIP_TYPE, definition
from governance.jurisdiction.water_assignments import add_features, category
from governance.jurisdiction.geographic_water import populate_features, WATER, COUNTIES, COUNTRY_COLUMN


def fixture(tmp_path):
    water=gpd.GeoDataFrame({'NAME':['UNITED_STATES','CANADA'],'AREA':['CONTIGUOUS','BRITISH_COLUMBIA'],'TYPE':['TERRITORIAL','TERRITORIAL']},geometry=[box(-123,47,-122,48),box(-123,48,-122,49)],crs=4326)
    county=gpd.GeoDataFrame({'STATEFP':['53','41'],'GEOID':['53001','41001'],'NAME':['WA fixture','OR fixture'],'NAMELSAD':['WA fixture county','OR fixture county']},geometry=[box(-123,47,-122.4,48.1),box(-122.4,47,-122,48.1)],crs=4326)
    bindings={}
    for source,frame in [(WATER,water),(COUNTIES,county)]:
        path=tmp_path/f'OriginalData/{source}/geometry.parquet';path.parent.mkdir(parents=True);frame.to_parquet(path,index=False);t=pq.read_table(path);pq.write_table(t.replace_schema_metadata({**t.schema.metadata,b'governance_original':json.dumps({'source':{'source_id':source}}).encode()}),path)
        bindings[source]={'path':str(path.relative_to(tmp_path)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    cells=[h3.latlng_to_cell(48,-122.4,6),h3.latlng_to_cell(47.5,-122.8,6),h3.latlng_to_cell(50,-122.8,6)]
    country_rows=[]
    for cell in cells:
        poly=Polygon([(lon,lat) for lat,lon in h3.cell_to_boundary(cell)]);entries=[]
        for country,geom in zip(['USA','CAN'],water.geometry):
            if poly.intersection(geom).area<=0:continue
            record=dict.fromkeys(RECORD_FIELDS);record.update(source_dataset_id=WATER,source_feature_id=f'{WATER}:{country}:01',feature_name=country+' original water label',feature_type='country_water_reference_polygon',jurisdiction=country,region='UNITED_STATES' if country=='USA' else 'CANADA',geometry_part_ids=[country+':original-part'])
            entries.append({'feature_id':f'country_water_reference:{country}:01','records':[record]})
        country_rows.append(sorted(entries,key=lambda e:e['feature_id']) or None)
    count=COUNTRY_COLUMN.replace('feature_memberships_v1','recorded_feature_count');states=['partial' if row else 'unknown' for row in country_rows]
    columns={'h3_index':cells,COUNTRY_COLUMN:pa.array(country_rows,MEMBERSHIP_TYPE),COUNTRY_COLUMN+'_status':states,count:pa.array([len(r) if r else None for r in country_rows],pa.int64()),count+'_status':states}
    for family in ['state_provincial_waters','federal_waters']:
        columns[family+'__recorded_feature_count']=pa.array([None]*3,pa.int64());columns[family+'__recorded_feature_count_status']=['unknown']*3
    fields={n:{} for n in columns};fields[COUNTRY_COLUMN]=definition('international_boundaries');coverage={}
    table=add_features(pa.table(columns),fields,coverage)
    return table,{'fields':fields,'coverage':coverage,'original_data':bindings},cells


def codes(table,family,row):
    entries=table[family+'__assignment__feature_memberships_v1'][row].as_py()
    return {category(family,r) for e in entries or [] for r in e['records']}


def test_geographic_crossings_use_water_intersections_and_preserve_inputs(tmp_path):
    table,meta,cells=fixture(tmp_path);before=copy.deepcopy(meta);result=populate_features(table,meta,tmp_path)
    assert codes(result,'state_provincial_waters',0)=={'WA','BC','OR'}
    assert codes(result,'federal_waters',0)=={'USA','CAN'}
    assert codes(result,'state_provincial_waters',1)=={'WA'}
    for family in ['state_provincial_waters','federal_waters']:
        name=family+'__assignment__feature_memberships_v1'
        assert result[name][2].as_py() is None
        assert result[name+'_status'].to_pylist()==['partial','partial','unknown']
        assert result[name.replace('feature_memberships_v1','recorded_feature_count')][2].as_py() is None
        assert meta['fields'][name]['assignment_semantics']=='geographic'
        assert meta['fields'][name]['original_source_bindings']=={k:v for k,v in before['original_data'].items() if family=='state_provincial_waters' or k==WATER}
    for name in table.column_names:
        if '__assignment__' not in name:assert table[name].equals(result[name]),name
    original=table[COUNTRY_COLUMN][0].as_py()
    derived=result['federal_waters__assignment__feature_memberships_v1'][0].as_py()
    for source,target in zip(original,derived):
        assert source['feature_id']==target['feature_id']
        for a,b in zip(source['records'],target['records']):
            for field in ['source_dataset_id','source_feature_id','feature_name','geometry_part_ids']:
                assert a[field]==b[field]
    assert result.equals(populate_features(result,meta,tmp_path))


def test_country_only_and_missing_originals_remain_honest(tmp_path):
    table,meta,cells=fixture(tmp_path);meta['original_data'].pop(COUNTIES)
    result=populate_features(table,meta,tmp_path)
    assert codes(result,'state_provincial_waters',0)=={'BC'}
    assert result['state_provincial_waters__assignment__feature_memberships_v1'][1].as_py() is None
    assert codes(result,'federal_waters',0)=={'USA','CAN'}
    meta['original_data'].pop(WATER)
    assert populate_features(table,meta,tmp_path) is table


def test_original_checksum_and_country_mask_binding_are_verified(tmp_path):
    table,meta,_=fixture(tmp_path);meta['original_data'][WATER]['sha256']='changed'
    with pytest.raises(ValueError,match='binding mismatch'):populate_features(table,meta,tmp_path)
