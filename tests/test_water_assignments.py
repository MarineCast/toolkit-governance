import copy
import pyarrow as pa
import pytest
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition
from governance.jurisdiction.water_assignments import FAMILIES, add_features, assignment_group, category, normalize_country, scientific_features


def member(code, country, kind='state_water_polygon', feature='id', source='qualified_source'):
    r = dict.fromkeys(RECORD_FIELDS)
    r.update(source_dataset_id=source, source_feature_id=source+':001', jurisdiction=country, region=code,
             feature_type=kind, feature_name='Original source label', geometry_part_ids=['part-a', 'part-b'])
    return {'feature_id': feature, 'records': [r]}


def fixture(family, rows):
    name=family+'__feature_memberships_v1'; count=family+'__recorded_feature_count'
    states=['partial' if row else 'observed' if row == [] else 'unknown' for row in rows]
    columns={name:pa.array(rows,MEMBERSHIP_TYPE),name+'_status':pa.array(states),
             count:pa.array([None if r is None else len(r) for r in rows],pa.int64()),count+'_status':pa.array(states)}
    fields={n:{} for n in columns};fields[name]=definition(family)
    return pa.table(columns),fields,{family:{}}


def qualify(family, fields):
    q={'geometry_support':'positive_area_water_polygons','source_dataset_ids':['qualified_source'],
       'jurisdiction_definition':'state_province_water_jurisdiction' if family=='state_provincial_waters' else 'federal_administrative_waters_and_high_seas_beyond_national_jurisdiction',
       'evidence':'Synthetic qualification; test fixture only'}
    fields[family+'__feature_memberships_v1']['water_assignment_qualification']=q


@pytest.mark.parametrize('raw,expected',[('US','USA'),('usa','USA'),('United_States','USA'),('United States of America','USA'),('Canada','CAN'),('ca','CAN'),('CAN','CAN'),('International',None),(None,None)])
def test_country_normalization(raw,expected):
    assert normalize_country(raw)==expected


def test_qualified_state_membership_retains_all_crossings_and_provenance():
    family='state_provincial_waters'
    rows=[[member('Washington','United States',feature='id:1'),member('BRITISH_COLUMBIA','Canada','provincial_water_polygon',feature='id:2'),member('OR','USA',feature='id:3')],None,[]]
    table,fields,coverage=fixture(family,rows);original=table
    qualify(family,fields)
    result=add_features(table,fields,coverage);name=assignment_group(family)+'__feature_memberships_v1'
    assert result[name][0].as_py()==rows[0]
    assert [category(family,r['records'][0]) for r in rows[0]]==['WA','BC','OR']
    assert result[name].to_pylist()[1:]==[None,None]
    assert all(result[n].equals(original[n]) for n in original.column_names)
    assert {n for n,f in fields.items() if f.get('map_feature')}==set(scientific_features(family))
    assert result.equals(add_features(result,fields,coverage))
    coverage[family]={'geographic_inventory_coverage':{'status':'complete','scope':'full_supplied_cells','evidence':'Synthetic full-cell polygon inventory'}}
    complete=add_features(result,fields,coverage)
    assert complete[name][2].as_py()==[]
    assert complete[name+'_status'][2].as_py()=='observed'


@pytest.mark.parametrize('family',FAMILIES)
def test_lines_country_support_and_unqualified_polygons_never_become_water_assignments(family):
    entries=[member('WA','USA','state_seaward_boundary_line','a'),member('BC','Canada','country_water_reference_polygon','b'),member('OR','USA','exclusive_economic_zone_limit','c'),member('WA','USA',feature='d')]
    table,fields,coverage=fixture(family,[entries,None,[]]);result=add_features(table,fields,coverage)
    name=assignment_group(family)+'__feature_memberships_v1'
    assert result[name].to_pylist()==[None]*3
    assert result[name+'_status'].to_pylist()==['unavailable']*3
    qualify(family,fields)
    result=add_features(result,fields,coverage)
    assert result[name][1].as_py() is None # never International or empty by fallback
    assert result[name][2].as_py() is None
    assert category('state_provincial_waters', member('BC','USA')['records'][0]) is None


def test_federal_administration_eez_territorial_and_high_seas_are_distinct():
    family='federal_waters'
    kinds=['federal_administrative_water_polygon','federal_administrative_water_polygon','high_seas_polygon','territorial_sea_limit','exclusive_economic_zone_limit','country_water_reference_polygon']
    countries=['US','Canada','International','USA','CAN','CAN']
    entries=[member(None,c,k,str(i)) for i,(c,k) in enumerate(zip(countries,kinds))]
    table,fields,coverage=fixture(family,[entries]);qualify(family,fields)
    result=add_features(table,fields,coverage);name=assignment_group(family)+'__feature_memberships_v1'
    assert result[name][0].as_py()==entries[:3]
    assert [category(family,r['records'][0]) for r in entries]==['USA','CAN','INT',None,None,None]


def test_catalog_and_delivery_declare_one_choice_per_family():
    from governance.maintenance.catalog import build_catalog
    from governance.delivery import project_delivery
    catalog=build_catalog()
    columns={'H3_INDEX':['fixture']}
    for family in FAMILIES:
        assert catalog['collections'][family]['scientific_features']==scientific_features(family)
        for suffix,dtype in [('FEATURE_COUNT',pa.int64()),('POLYGON_COVERAGE_FRAC',pa.float64()),('LINE_LENGTH_M',pa.float64()),('POINT_COUNT',pa.int64())]:
            columns[family+'__'+suffix]=pa.array([None],dtype)
    metadata={'native_manifests':{family:{'manifest':{'source_completeness':'partial','sources':[{'source_id':family,'runtime_status':'available'}]}} for family in FAMILIES},'grid':{},'area_crs':'EPSG:6933','length_crs':'EPSG:32610','temporal_support':'static','config_hash':'fixture'}
    table,envelope=project_delivery(pa.table(columns),metadata,6)
    for family in FAMILIES:
        assert {n for n,f in envelope['fields'].items() if n.startswith(family+'__') and f.get('map_feature')}==set(scientific_features(family))
        assert table[assignment_group(family)+'__feature_memberships_v1'][0].as_py() is None
