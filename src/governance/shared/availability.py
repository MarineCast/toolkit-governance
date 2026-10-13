"""Machine-readable implementation/region/source qualification, separate from runtime receipts."""
from .registry import CATEGORY_COLLECTIONS

REGIONS = {
    'central_oregon': ('USA', 'oregon'), 'washington': ('USA', 'washington'),
    'southern_bc': ('CAN', 'british_columbia_canada'), 'northern_bc': ('CAN', 'british_columbia_canada'),
    'southeast_alaska': ('USA', 'alaska'), 'gulf_alaska': ('USA', 'alaska'),
    'aleutians_dateline': ('USA', 'alaska'), 'arctic_alaska': ('USA', 'alaska'),
}
BLOCKERS = {
    'management_areas': 'DFO Pacific subarea geometry is implemented; whole-area/regulatory applicability and redistribution remain unqualified. Oregon commercial PDF/chart blocks lack qualified vector/identity; Alaska groundfish is one reporting system, not all fisheries.',
    'tribal_first_nations_areas': 'BIA land-area and NRCan BC Indian Reserves only; traditional territory, treaties, title and fishing rights need separate provider/interpretation contracts.',
    'marine_protected_areas': 'NOAA 2023 discovery and ODFW 2016 reference vintages; current site instruments and complete jurisdiction rosters remain unverified. DFO AOIs require opt-in and are not designation boundaries.',
    'exclusion_zones': 'Only TC 2026 Saturna/Pender closed rings; other issuers/zones unqualified. Shoreline exceptions require vessel/context interpretation.',
    'speed_restriction_zones': 'Only TC 2026 Swiftsure closed ring; Nitinat requires pinned authoritative coastline support. Other systems/unversioned law unavailable.',
    'state_provincial_waters': 'BOEM reference boundary line only; no complete provincial legal water geometry supplied.',
    'whale_approach_regulation_zones': 'Moving-animal applicability requires animal/vessel/species/activity context; permanent zone geometry is not applicable.',
}



def provider_region_states(source):
    states = {region: source.coverage.get(legacy_region, 'unknown') for region, (_, legacy_region) in REGIONS.items()}
    if source.source_id == 'adfg_groundfish_statistical_areas':
        states['arctic_alaska'] = 'unavailable'
    return states

def availability_matrix(config):
    rows=[]
    for category,names in CATEGORY_COLLECTIONS.items():
        for name in names:
            collection=config.collections.get(name)
            sources=[config.sources[sid] for sid in collection.source_ids] if collection else [None]
            for source in sources:
                for region,(jurisdiction,legacy_region) in REGIONS.items():
                    geographic=source.coverage.get(legacy_region,'unknown') if source else 'unavailable'
                    if source and source.source_id=='adfg_groundfish_statistical_areas' and region=='arctic_alaska':
                        geographic='unavailable' # Declared layer extent ends south of this regional fixture.
                    rows.append(dict(layer=name,category=category,jurisdiction=jurisdiction,region=region,
                        provider=source.provider if source else None,system=source.source_id if source else None,
                        implementation='implemented_reference' if collection else 'not_implemented',
                        acquisition_completeness='not_evaluated',geographic_completeness=geographic,
                        legal_currentness='not_verified',temporal_capability='instrument_version_snapshot' if source and source.source_id=='tc_srkw_interim_order_2026' else 'inventory_snapshot_only' if collection else 'unavailable',
                        geometry_type='polygon' if name in {'marine_protected_areas','management_areas','exclusion_zones','speed_restriction_zones','tribal_first_nations_areas'} and not (source and source.source_id=='dfo_oceans_act_areas_of_interest') else 'point' if name=='ports' or (source and source.source_id=='dfo_oceans_act_areas_of_interest') else 'provider_native_mixed_or_unqualified',
                        source_vintage=source.source_as_of if source else None,source_url=source.url if source else None,
                        limitation=BLOCKERS.get(name, 'Named provider reference scope only; exhaustive regional/legal qualification remains unverified.') + (' '+source.source_limitation if source else ' Required evidence: named issuer/system, authoritative geometry, stable identities, access/rights, applicable instrument versions and intervals.'),
                        rights=source.redistribution if source else 'unqualified',attribution=source.attribution if source else None))
    return {'availability_schema_version':1,'qualification_date':'2026-10-13','scope':'central Oregon, Washington, BC and separately qualified Alaska regions',
            'semantics':'Implementation, complete acquisition receipt, geographic completeness and legal currentness are separate. Runtime get_layer.coverage supplies actual receipt state; synthetic tests do not certify these regions.',
            'rows':rows,
            'additional_source_gaps':[
                {'layer':'marine_protected_areas','jurisdiction':'BC','provider':'BC Parks/Tantalis','status':'not_implemented','evidence_url':'https://catalogue.data.gov.bc.ca/dataset/bc-parks-ecological-reserves-and-protected-areas','blocker':'Provincial park/eco-reserve/protected-area polygons do not by themselves classify marine designations; marine inclusion taxonomy, stable zone identity and authoritative vector/terms need qualification. Existing ECCC marine classification remains separate.'},
                {'layer':'management_areas','jurisdiction':'BC','provider':'DFO Pacific','status':'implemented_subarea_reference_only','evidence_url':'https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/Pacific/DFO_BC_PFMA_SUBAREAS_50K_V3_1/MapServer/0','blocker':'Subarea hierarchy adapter and bounded receipts implemented; licence fields blank, redistribution unqualified; whole-area polygon authority, legal applicability and history remain separate gaps.'},
                {'layer':'management_areas','jurisdiction':'Oregon','provider':'ODFW','status':'not_implemented','evidence_url':'https://www.dfw.state.or.us/fish/commercial/docs/marine_reserves/logbook_grid_charts.asp','blocker':'Nearshore logbook charts are not an approved vector reporting/management system.'},
                {'layer':'safety_security_zones','jurisdiction':'USA/CAN','status':'not_implemented','blocker':'Named controlling instruments, fixed boundaries, applicability/exceptions, source access and versioned regional rosters are required. No universal safe-waters score.'}]}
