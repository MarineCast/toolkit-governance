"""Two inspection choices for a deliberately incomplete restriction reference."""
from pathlib import Path
import hashlib
import pyarrow.parquet as pq

from .washington import SOURCE_ID, FEATURE_ID
from .replay import MASK_LIMITATION, replay_qualifications
from .standing import FWS,TORPEDO,SMITH,NEW_SOURCES
from .qualified import SOURCES as QUALIFIED_SOURCES, DFO, ENC, THEA, MPA, NAVY, qualifications

GROUP = 'exclusion_zones'
COUNT = GROUP+'__recorded_feature_count'
ASSIGNMENT = GROUP+'__feature_memberships_v1'
SCIENTIFIC_FEATURES = {COUNT: {'display_name': 'Exclusion Zone Count', 'role': 'scientific_metric'},
    ASSIGNMENT: {'display_name': 'Exclusion Zone Assignment', 'role': 'recorded_feature_identity'}}
LIMITATION = ('Partial static reference to named restrictions, not currently active restrictions for every date or vessel. '
    'Vessel-entry, seabed/anchoring and fishing restrictions are different activities; transit may be permitted. '
    'All overlaps and source IDs are retained; geometry parts do not increase zone counts. '
    'No-hit cells are unknown, never zero. Fisheries, military/security, habitat access, temporary and moving zones remain incomplete. '
    'Source and effective dates, seasonal conditions, exceptions and knowledge times must be inspected; no 2009-present history is inferred. '
    + MASK_LIMITATION + ' '
    'Five areas use parsed legal-instrument coordinate rings, one uses a checked agency active-area diagram; other areas use provider reference geometry; inspect per-product evidence counts. No geometry certifies present prohibition. '
    'DFO notices identify reef orders and activity-specific dates; full orders, WAC surveyed boundaries and NOAA chart/rule vintage differences remain qualified gaps.')
SOURCE_CONTEXT = {
    'tc_srkw_interim_order_2026': {'country': 'Canada', 'agency': 'Transport Canada',
        'boundary_type': '2026 Schedule 2 coordinate-ring vessel restriction reference',
        'classification': 'Mandatory seasonal instrument with exceptions; source-version reference, no currentness certification',
        'scope': 'Saturna/Pender only; not all Canadian restrictions'},
    SOURCE_ID: {'country': 'United States', 'agency': 'United States Coast Guard',
        'boundary_type': '33 CFR 165.1336(a)(2) four-corner regulated navigation area',
        'classification': 'Seabed-disturbance restriction; ordinary transit/navigation permitted',
        'scope': 'Lockheed Shipyard only; neighboring shoreline-dependent area omitted'},
}
GAPS = ['BC fisheries outside selected RCA/reef roster; underlying signed variation orders/amendments/history and RCA coordinate audit remain unqualified; 22 reef notice-coordinate checks supplied',
    'WAC named conservation/preserve roster is integrated as provider reference geometry; surveyed tidal/property/marker boundaries, other seasonal salmon/shellfish closures remain unqualified',
    'Named USACE standing-source checklist integrated as chart references; local buoy/hydrophone/depth exceptions remain rule-only and actual activation unknown',
    'USCG zones beyond named chart/CFR references remain partial; moving-vessel/animal, event-only and notices history separate',
    'One WG active-area diagram qualified; other Canadian Navy/Esquimalt fixed shoreline zones, no-anchor/fishing area and vessel-relative permissions remain unqualified',
    'FWS Protection Island/San Juan landing-access reference includes explicit Matia/Turn public-use exceptions; 200-yard watercraft baselines and Scott Islands low-water zones remain unmapped',
    'Oregon portion of the study domain is outside this BC/WA restriction inventory; unknown coverage',
    'Historical versions and date/vessel-specific active applicability unavailable']

for _id, _country, _agency, _kind in [(DFO,'Canada','Fisheries and Oceans Canada','Rockfish and glass-sponge fishing restrictions'),(ENC,'United States','NOAA Office of Coast Survey; cited CFR authorities','Chart-derived named military/security/seabed rule references'),(THEA,'United States','United States Coast Guard','Thea Foss two coordinate-ring seabed areas'),(MPA,'United States','NOAA inventory; WDFW rule authority','Named WAC conservation-area and marine-preserve harvest restrictions'),(NAVY,'Canada','Department of National Defence; Canadian Coast Guard NOTMAR','One WG active-only military entry reference')]:
    SOURCE_CONTEXT[_id]={'country':_country,'agency':_agency,'boundary_type':_kind,'classification':'Partial official source/rule reference; inspect activation, source geometry qualification and unlinked legal-order gaps','scope':'Named sources only; no comprehensive restriction coverage'}

for _sid in NEW_SOURCES:
    SOURCE_CONTEXT[_sid]={'country':'United States','agency':'U.S. Fish and Wildlife Service' if _sid==FWS else 'NOAA chart depiction; cited USACE/Navy rule authority','boundary_type':'Explicit named access/activity reference','classification':'Provider reference geometry; source-specific exceptions and current applicability unknown','scope':'Finite reviewed named sources only; no comprehensive closure inventory'}

def annotate_fields(fields):
    for name, field in fields.items():
        if name.startswith(GROUP+'__'):
            field.update(map_feature=name in SCIENTIFIC_FEATURES, display_family='Exclusion Zones')
            field.update(SCIENTIFIC_FEATURES.get(name, {}))
            if name in SCIENTIFIC_FEATURES:
                field.update(support_limitation=LIMITATION, source_context=SOURCE_CONTEXT)
                if LIMITATION not in field.get('interpretation', ''):
                    field['interpretation'] = (field.get('interpretation', '')+' '+LIMITATION).strip()


def annotate_catalog(catalog):
    if GROUP in catalog.get('areas', {}):
        catalog['areas'][GROUP]['scientific_features'] = SCIENTIFIC_FEATURES


def annotate_product(table, metadata, original_root):
    annotate_fields(metadata['fields'])
    if ASSIGNMENT not in table.column_names:
        return table
    from governance.memberships import qualify_unknown_no_hit
    table = qualify_unknown_no_hit(table, (COUNT, ASSIGNMENT))
    wanted = {}
    for row in table[ASSIGNMENT].to_pylist():
        for member in row or []:
            for record in member['records']:
                wanted.setdefault(record['source_dataset_id'], set()).add(record['source_feature_id'])
    context = {}
    for source, identities in wanted.items():
        if source not in SOURCE_CONTEXT:
            raise ValueError('Exclusion source needs explicit rule-context qualification: '+source)
        binding = metadata.get('original_data', {}).get(source)
        if binding is None:
            raise ValueError('Exclusion original source binding missing')
        path = (Path(original_root)/binding['path']).resolve()
        if not path.is_relative_to(Path(original_root).resolve()):
            raise ValueError('Exclusion original path escapes root')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != binding['sha256']:
                raise ValueError('Exclusion original checksum mismatch')
        learned = binding.get('retrieved_at_utc')
        if source == 'tc_srkw_interim_order_2026':
            for row in pq.read_table(path, columns=['TC_ZONE_ID','TC_SCHEDULE']).to_pylist():
                identity = 'tc.2026:'+row['TC_ZONE_ID']
                if identity not in identities: continue
                if row['TC_SCHEDULE'] != 'schedule2':
                    raise ValueError('Speed reference cannot become vessel exclusion')
                context[identity] = {'restriction_category':'vessel_entry_restriction',
                    'prohibited_activity':'Navigation and operation of vessels', 'permitted_activity':'Only applicable source exceptions',
                    'binding_status':'Mandatory instrument prohibition with exceptions; static reference',
                    'country':'Canada', 'authority':'Minister of Transport, Canada',
                    'rule_id':'tc.srkw.interim_order.2026', 'rule_clause':'Sections 2, 5, 6, 10; Schedule 2',
                    'source_version':'2026-05-22', 'effective_start':'2026-06-01', 'effective_end':'2026-11-30',
                    'end_precision':'Inclusive local calendar day in source instrument; no UTC daily series',
                    'activation_condition':'2026 fixed season only; applicability and exceptions depend on vessel/person/activity',
                    'seasonal_dates':'June 1 through November 30, 2026; no recurrence inferred for other years',
                    'exceptions':'Sections 2, 5(2), 6(2): emergency/public duty; qualifying direct access; human-powered vessels within 20 m of shoreline; specified Indigenous fishing/rights and authorized persons. Full instrument controls.',
                    'source_url':'https://tc.canada.ca/en/interim-order-protection-killer-whale-orcinus-orca-waters-southern-british-columbia',
                    'knowledge_at_utc':learned, 'current_activity':'Unknown; static geometry never means active for every date/vessel'}
        elif source in QUALIFIED_SOURCES:
            import geopandas as gpd
            for _, row in gpd.read_parquet(path).iterrows():
                for _, identity, _, detail in qualifications(row, source):
                    if identity not in identities: continue
                    context[identity] = {**detail, 'knowledge_at_utc': learned}
        else:
            rows = pq.read_table(path, columns=['ZONE_ID','RULE_TEXT','BOUNDARY_TEXT','SOURCE_DATUM']).to_pylist()
            for row in rows:
                identity = row['ZONE_ID']
                if identity not in identities: continue
                if identity != FEATURE_ID: raise ValueError('Unqualified USCG original identity')
                context[identity] = {'restriction_category':'seabed_disturbance_restriction',
                    'prohibited_activity':'Seabed disturbance, including anchoring, dragging, trawling and spudding',
                    'permitted_activity':'Ordinary transit and navigation permitted',
                    'binding_status':'Mandatory rule reference with exceptions; no currentness certification',
                    'country':'United States', 'authority':'United States Coast Guard',
                    'rule_id':'33 CFR 165.1336', 'rule_clause':'(a)(2), (b)(1)-(3), (c)',
                    'source_version':'eCFR point-in-time 2026-10-15', 'source_publication':'77 FR 21435, 2012-04-10; not asserted as effective date',
                    'effective_start':None, 'effective_end':None, 'seasonal_dates':None,
                    'activation_condition':'Standing rule reference; no activation/enforcement history supplied',
                    'exceptions':'Remediation with EPA advance notice to COTP; source preserves Muckleshoot/Suquamish treaty fishing provisions; COTP waiver may apply. See full rule.',
                    'source_url':'https://www.ecfr.gov/on/2026-10-15/title-33/section-165.1336',
                    'source_datum':row['SOURCE_DATUM'], 'boundary_text':row['BOUNDARY_TEXT'],
                    'knowledge_at_utc':learned, 'current_activity':'Unknown; no date/vessel compliance classification',
                    'full_rule_text':row['RULE_TEXT'], 'spatial_support':'Full supplied H3 cell intersections; consult product-specific reporting-mask qualification. No water-only overlap is implied.'}
        if identities.difference(context):
            raise ValueError('Exclusion membership lacks qualified rule context')
    from .evidence import evidence_context
    source_for_record = {r['source_feature_id']: r['source_dataset_id'] for row in table[ASSIGNMENT].to_pylist() for m in row or [] for r in m['records']}
    context = {identity:evidence_context(source_for_record[identity],identity,detail) for identity,detail in context.items()}
    prior_context = metadata['fields'][ASSIGNMENT].get('source_record_context', {})
    context = {identity: {**prior_context.get(identity, {}), **detail} for identity, detail in context.items()}
    for identity, detail in context.items():
        if source_for_record[identity]==NAVY:
            detail.pop('full_rule_text',None)
        if 'spatial_support' in prior_context.get(identity, {}):
            detail['spatial_support'] = prior_context[identity]['spatial_support']
    metadata['fields'][ASSIGNMENT]['source_record_context'] = context
    metadata.setdefault('coverage', {}).setdefault(GROUP, {})['scope_gaps'] = GAPS
    metadata['exclusion_zone_interface'] = {'method_version':'bounded-static-restriction-reference-4',
        'active_restriction_by_date_or_vessel':False, 'history_reconstructed':False,
        'count_semantics':'Distinct recorded zone IDs; source categories not legally equivalent',
        'missingness':'Unknown no-hit support; never absence', 'scope_gaps':GAPS,
        'geometry_evidence_counts':{'parsed_legal_instrument_coordinate_areas':len({m['feature_id'] for row in table[ASSIGNMENT].to_pylist() for m in row or [] if m['records'][0]['source_dataset_id'] in {'tc_srkw_interim_order_2026',SOURCE_ID,THEA}}),
         'agency_coordinate_reference_areas':len({m['feature_id'] for row in table[ASSIGNMENT].to_pylist() for m in row or [] if m['records'][0]['source_dataset_id']==NAVY}),
         'provider_reference_areas':len({m['feature_id'] for row in table[ASSIGNMENT].to_pylist() for m in row or [] if m['records'][0]['source_dataset_id'] in ({DFO,ENC,MPA} | NEW_SOURCES)})}}
    replay_qualifications(table, metadata, original_root, context)
    return table
