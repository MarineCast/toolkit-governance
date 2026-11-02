import copy
from governance.jurisdiction.presentation import annotate_fields,annotate_catalog,COLLECTIONS,FAMILY_NAME,FAMILY_KEY


def test_administrative_grouping_preserves_bia_nrcan_types_and_existing_features():
    fields={name+'__feature':{'definition':'source/legal type unchanged','source_context':{'BIA':'land area reference','NRCan':'reserve administrative geometry'},'units':'1','count_field':'original','missing_reason_field':'original_status'} for name in COLLECTIONS}
    before=copy.deepcopy(fields);annotate_fields(fields)
    assert fields=={name:{**field,'display_family':FAMILY_NAME} for name,field in before.items()}
    catalog={'areas':{name:{'source_ids':[name]} for name in COLLECTIONS},'feature_families':{'marine_conservation_areas':{'display_name':'Marine Conservation Areas'}}}
    annotate_catalog(catalog)
    assert catalog['feature_families'][FAMILY_KEY]['source_collections']==list(COLLECTIONS)
    assert 'marine_conservation_areas' in catalog['feature_families']
    assert all(record['source_ids']==[name] for name,record in catalog['areas'].items())
