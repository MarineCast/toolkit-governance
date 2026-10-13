"""Collection dispatch and provider schema contracts; no acquisition side effects."""
from importlib import import_module
from .schema import empty_governance_frame

# Required fields are checked case-insensitively before normalizers can invent fallbacks.
PROVIDER_FIELDS = {
    'odfw_marine_reserves_2016': ('ODFW_RECORD_ID', 'ODFW_NAME'),
    'tc_srkw_interim_order_2026': ('TC_ZONE_ID', 'TC_SCHEDULE'),
    'dfo_pacific_fishery_management_areas': ('OBJECTID', 'MGNT_AREA', 'SUBAREA_', 'GLOBALID'),
    'wdfw_recreational_marine_areas': ('OBJECTID', 'AreaName'),
    'dfo_oceans_act_marine_protected_areas': ('OBJECTID', 'NAME_E', 'ZONE_E'),
    'dfo_oceans_act_areas_of_interest': ('OBJECTID', 'NAME_E'),
    'noaa_mpa_inventory_2023': ('site_id',),
    'bia_administrative_lar': ('OBJECTID', 'LARID', 'CLASSIFICATION'),
    'nrcan_indian_reserves': ('OBJECTID', 'adminAreaId', 'distributionTypeEng', 'jurisdictionEng'),
    'eccc_marine_classification': ('OBJECTID', 'BIOME', 'PA_OECM_DF', 'STATUS', 'PARENT_ID', 'ZONE_ID'),
    'noaa_critical_habitat_polygon': ('OBJECTID', 'EFFECTDATE'),
    'noaa_critical_habitat_line': ('OBJECTID', 'EFFECTDATE'),
    'fws_national_wildlife_refuges': ('OBJECTID', 'RSL_TYPE'),
    'eccc_wildlife_areas_sanctuaries': ('OBJECTID', 'TYPE_E'),
    'adfg_groundfish_statistical_areas': ('OBJECTID', 'STAT_AREA', 'GEOMETRY_START_DATE', 'GEOMETRY_END_DATE'),
}


def normalize_collection(frame, source, collection, *, normalizer=None):
    from dataclasses import replace
    from governance.maintenance.catalog import EXTRA_FEATURES
    module = import_module(f'governance.{collection.category}.{collection.collection_id}.normalize')
    fields = PROVIDER_FIELDS.get(source.source_id, ())
    if source.source_id.startswith('noaa_mpa_inventory'):
        fields = ('site_id',)
    if source.source_id.startswith('chs_routing'):
        fields = ('OBJECTID', 'MERGE_SRC')
    if source.source_id == 'noaa_routing_2026':
        fields = ('SOURCE_FID', 'routeType')
    lookup = {str(name).casefold() for name in frame.columns}
    missing = [name for name in fields if name.casefold() not in lookup]
    # Even an empty service response must carry field metadata to establish its schema.
    if missing:
        raise ValueError(f'Upstream schema drift for {source.source_id}: missing required fields {missing}; inspect archived layer metadata')
    source = replace(source, retrieved_at_utc=frame.attrs.get('retrieved_at_utc', source.retrieved_at_utc))
    if fields:
        lookup = {str(name).casefold(): name for name in frame.columns}
        frame = frame.rename(columns={lookup[name.casefold()]: name for name in fields})
        declared = {item['name'].casefold(): item.get('type') for item in frame.attrs.get('layer_metadata', {}).get('fields', [])}
        for field in fields:
            if field in {'OBJECTID', 'STAT_AREA'}:
                kind = declared.get(field.casefold())
                if kind is not None and kind not in {'esriFieldTypeOID', 'esriFieldTypeInteger', 'esriFieldTypeSmallInteger', 'esriFieldTypeBigInteger'}:
                    raise ValueError(f'Upstream schema drift for {source.source_id}.{field}: expected integer identity, received {kind}')
                if frame[field].isna().any():
                    raise ValueError(f'{source.source_id}.{field}: required non-null identities')
    output = (normalizer or module.normalize)(frame, source)
    if output.empty:
        output = empty_governance_frame(extra_fields=[field[0] for field in EXTRA_FEATURES.get(collection.collection_id, ())])
    elif frame.attrs.get('receipts_by_id'):
        receipts = frame.attrs['receipts_by_id']
        # SOURCE_RECORD_ID retains exact provider OID in MPA records; other adapters namespace it.
        output['SYSTEM_LEARNED_AT'] = [receipts.get(str(row.get('SOURCE_RECORD_ID', str(row.SOURCE_FEATURE_ID).split(':')[-1])), source.retrieved_at_utc) for _, row in output.iterrows()]
    return output


CATEGORY_COLLECTIONS = {
    "protected_areas": (
        "marine_protected_areas",
        "critical_habitat",
        "national_marine_sanctuaries",
        "wildlife_refuges",
        "conservation_designations",
    ),
    "jurisdiction": (
        "international_boundaries",
        "federal_waters",
        "state_provincial_waters",
        "county_regional_boundaries",
        "tribal_first_nations_areas",
    ),
    "fisheries_management": (
        "management_areas",
        "seasonal_closures",
        "gear_restrictions",
        "harvest_regulations",
        "salmon_management_zones",
    ),
    "vessel_management": (
        "shipping_lanes",
        "traffic_separation_schemes",
        "exclusion_zones",
        "speed_restriction_zones",
        "whale_approach_regulation_zones",
    ),
    "administrative_context": (
        "ports",
        "coast_guard_sectors",
        "management_regions",
        "reporting_areas",
    ),
}
