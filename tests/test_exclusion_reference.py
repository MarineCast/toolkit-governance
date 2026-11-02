from dataclasses import replace
import copy
import hashlib
import json

import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from governance.shared.config import load_governance_config
from governance.vessel_management.exclusion_zones.washington import source_frame, normalize, SOURCE_ID, FEATURE_ID
from governance.vessel_management.exclusion_zones.interface import annotate_fields, annotate_product, COUNT, ASSIGNMENT, SCIENTIFIC_FEATURES


def xml_fixture():
    return '''<DIV8 N="165.1336"><P>(2) All waters inside an area beginning at 47°34′ 52.16″ N 122°21′27.11″ W; thence to 47°34′ 53.46″ N 122°21′30.42″ W; thence to 47°34′ 37.92″ N 122°21′30.51″ W; thence to 47°34′ 37.92″ N 122°21′27.65″ W. [Datum: NAD 1983].</P><P>Vessels may otherwise transit or navigate within this area without reservation.</P></DIV8>'''


def test_coordinate_reference_keeps_literal_boundary_datum_and_unknown_effective_dates(tmp_path):
    path=tmp_path/'rule.xml';path.write_text(xml_fixture())
    raw=source_frame(path)
    assert len(raw)==1 and raw.crs.to_epsg()==4326
    assert raw.SOURCE_DATUM.iloc[0]=='NAD83 (EPSG:4269)'
    assert len(raw.SOURCE_COORDINATES.iloc[0])==4
    assert 'shoreline' in raw.attrs['excluded_scope']
    source=load_governance_config().sources[SOURCE_ID]
    native=normalize(raw,source)
    assert native.GOVERNANCE_FEATURE_ID.tolist()==[FEATURE_ID]
    assert native.EFFECTIVE_START.isna().all() and native.EFFECTIVE_END.isna().all()
    assert native.EXCLUSION_CATEGORY.tolist()==['seabed_disturbance_restriction']
    assert 'Transit' in native.PERMITTED_ACTIVITY.iloc[0]
    assert not native.MODEL_ELIGIBLE.any()


@pytest.mark.parametrize('old,new', [('N="165.1336"','N="165.1327"'), ('NAD 1983','unknown'), ('thence to','along the shoreline to'), ('47°34′ 37.92″ N 122°21′27.65″ W','omitted point')])
def test_parser_rejects_unsupported_identity_datum_coast_or_corner(tmp_path,old,new):
    path=tmp_path/'rule.xml';path.write_text(xml_fixture().replace(old,new))
    with pytest.raises(ValueError):source_frame(path)


def test_only_count_assignment_are_picker_features_and_annotation_is_idempotent():
    fields={name:{'definition':'old','units':'count'} for name in [COUNT,ASSIGNMENT,COUNT+'_status','exclusion_zones__recorded_polygon_union_area_fraction']}
    fields['other__value']={'definition':'exact'};original=copy.deepcopy(fields)
    annotate_fields(fields);assert {n for n,f in fields.items() if f.get('map_feature')}==set(SCIENTIFIC_FEATURES)
    assert fields['other__value']==original['other__value']
    replay=copy.deepcopy(fields);annotate_fields(fields);assert fields==replay
    assert 'never zero' in fields[COUNT]['support_limitation']


def test_paired_rule_context_has_activity_exceptions_and_dates_without_changing_values(tmp_path):
    from governance.memberships import RECORD_FIELDS,MEMBERSHIP_TYPE
    source='tc_srkw_interim_order_2026';identity='tc.2026:pender'
    record=dict.fromkeys(RECORD_FIELDS);record.update(source_dataset_id=source,source_feature_id=identity,feature_name='Pender',geometry_part_ids=['part-a','part-b'])
    table=pa.table({COUNT:pa.array([1,None],pa.int64()),ASSIGNMENT:pa.array([[{'feature_id':identity,'records':[record]}],None],MEMBERSHIP_TYPE)})
    path=tmp_path/'OriginalData'/source/'geometry.parquet';path.parent.mkdir(parents=True)
    pq.write_table(pa.table({'TC_ZONE_ID':['pender'],'TC_SCHEDULE':['schedule2']}),path)
    metadata={'fields':{n:{'definition':'old'} for n in table.column_names},'original_data':{source:{'path':str(path.relative_to(tmp_path)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'retrieved_at_utc':'2026-10-14T02:08:37Z'}}}
    result=annotate_product(table,metadata,tmp_path);assert result.equals(table)
    ctx=metadata['fields'][ASSIGNMENT]['source_record_context'][identity]
    assert ctx['restriction_category']=='vessel_entry_restriction' and ctx['effective_end']=='2026-11-30'
    assert '20 m' in ctx['exceptions'] and ctx['knowledge_at_utc']=='2026-10-14T02:08:37Z'
    assert metadata['exclusion_zone_interface']['history_reconstructed'] is False
    metadata['original_data'][source]['sha256']='bad'
    with pytest.raises(ValueError,match='checksum'):annotate_product(table,metadata,tmp_path)


def test_multipart_overlaps_count_actual_zones_and_leave_no_hit_unknown():
    from shapely.geometry import box,MultiPolygon
    from governance.shared.registry import normalize_collection
    from governance.shared.spatial import clip_to_full_area
    from governance.h3_matrix import overlay_collection
    config=load_governance_config();source=config.sources[SOURCE_ID]
    frame=gpd.GeoDataFrame({'ZONE_ID':[FEATURE_ID],'BOUNDARY_TEXT':['fixture'],'RULE_TEXT':['fixture'],'SOURCE_DATUM':['NAD83'],
        'geometry':[MultiPolygon([box(-123,48,-122.95,48.05),box(-122.9,48,-122.85,48.05)])]},crs=4326)
    native=normalize_collection(frame,source,config.collections['exclusion_zones'])
    native,_=clip_to_full_area(native,config)
    grid=gpd.GeoDataFrame(geometry=[box(-123.1,47.9,-122.8,48.1),box(-125,49,-124.9,49.1)],crs=4326)
    overlay=overlay_collection(grid,native,completeness='partial',length_crs='EPSG:32610',include_attributes=False)
    assert overlay['FEATURE_COUNT'].to_pylist()==[1,None]
    member=overlay['FEATURE_MEMBERSHIPS_V1'].to_pylist()[0]
    assert len(member)==1 and len(member[0]['records'][0]['geometry_part_ids'])==2


def test_direct_source_pin_is_enforced_before_parsing(tmp_path):
    from governance.shared.acquisition import read_source_frame
    source=load_governance_config().sources[SOURCE_ID]
    path=tmp_path/'rule.xml';path.write_text(xml_fixture())
    source=replace(source,local_path=path,snapshot_path=None)
    with pytest.raises(ValueError,match='checksum'):read_source_frame(source)
