"""Reviewed source/rule crosswalks; inventories alone never establish a prohibition."""
from importlib.resources import files
import json
import re

from governance.shared.normalization import base_record, records_frame

DFO = 'dfo_pacific_closure_references_20261019'
ENC = 'noaa_enc_harbor_rule_references_20261019'
THEA = 'uscg_theafoss_rna_20261015'
MPA = 'noaa_mpa_inventory_2023'
NAVY='dnd_wg_active_reference_20261020'
from .standing import NEW_SOURCES
SOURCES = {DFO, ENC, THEA, MPA, NAVY} | NEW_SOURCES
RULES = json.loads(files('governance.resources').joinpath('exclusion_rules_20261015.json').read_text())
WAC = {
 'WA507': ('080', 'Sund Rock Conservation Area'),
 'WA509': ('040', 'Octopus Hole Conservation Area'),
 'WA510': ('050', 'Orchard Rocks Conservation Area'),
 'WA511': ('070', 'South 239th Street Park Conservation Area'),
 'WA512': ('020', 'City of Des Moines Park Conservation Area'),
 'WA513': ('090', 'Waketickeh Creek Conservation Area'),
 'WA514': ('060', "Saltar's Point Beach Conservation Area"),
 'WA517': ('030', 'Keystone Conservation Area'),
}
# One regulatory area may have many chart-cell features. Source OIDs survive as
# records; the rule/subarea ID, never its chart part, determines zone counts.
ENC_RULES = {
 '334.1210': ('Admiralty Inlet naval restricted area', 'seabed_equipment_restriction', 'Equipment that may foul underwater installations (anchors, fishing gear, grapnels); dumping non-buoyant objects', 'Navigation is not prohibited by this rule', 'Standing activity rule; no enforcement history'),
 '334.1215': ('Naval Station Everett restricted area', 'military_entry_permission', 'Entry, mooring, anchoring, fishing and recreational boating without prior written permission', 'Written permission of Commanding Officer, Naval Station Everett', 'Standing permission requirement'),
 '334.1230': ('Port Orchard naval restricted area', 'seabed_disturbance_restriction', 'Anchoring or towing a drag of any kind', 'Transit is not prohibited by this rule', 'At any time; no effective interval reconstructed'),
 '334.1244': ('Manchester Fuel Depot restricted area', 'conditional_military_entry', 'Entry without enforcing-agency permission during restricted pier/ship operations', 'Military/naval supervision or enforcing-agency permission', 'Only during ship loading or pier operations precluding safe entry; quick-flashing beacons'),
 '334.1260': ('Dabob Bay Whitney Point restricted area', 'seabed_disturbance_restriction', 'Anchoring or towing a drag of any kind', 'Transit is not prohibited by this rule', 'At any time; no effective interval reconstructed'),
 '334.1270': ('Indian Island Walan Point restricted area', 'conditional_military_entry', 'Entry without enforcing-agency permission during restricted operations', 'Enforcing-agency permission', 'Only when ship loading or pier operations preclude safe entry; red ship/pier flag'),
 '165.1309': ('Eagle Harbor sediment-cap RNA', 'seabed_disturbance_restriction', 'Anchoring, dredging, cable laying, dragging, seining, bottom fishing, salvage and other seabed disturbance', 'Ordinary transit/navigation permitted', 'Standing rule reference'),
 '165.1311': ('Olympic View Resource Area RNA', 'seabed_disturbance_restriction', 'Anchoring, dredging, cable laying, dragging, seining, bottom fishing, salvage and other seabed disturbance', 'Ordinary transit/navigation permitted', 'Standing rule reference'),
 '165.1340': ('West Duwamish drydock movement safety zone', 'event_activated_safety_zone', 'Entry or remaining without COTP authorization during noticed drydock movement enforcement', 'COTP/designated-representative authorization', 'Only upon enforcement notice; treaty-fishing coordination in full rule; current activation unknown'),
}
def _common(country, authority, category, prohibited, permitted, rule, url):
 return dict(country=country, authority=authority, restriction_category=category,
  prohibited_activity=prohibited, permitted_activity=permitted, rule_id=rule,
  source_url=url, binding_status='Qualified restriction reference; inspect geometry/instrument evidence; no current legal applicability certification',
  effective_start=None, effective_end=None, seasonal_dates=None,
  current_activity='Unknown; static geometry never establishes current activation or applicability to every vessel/person/date')

def _qualify(row, source_id):
 """Return (zone ID, source-feature ID, name, context), or an explicit unselected row."""
 if source_id==NAVY:
  if row.ZONE_ID!='ca.dnd.notmar35:wg_active' or 'NAD83' not in row.SOURCE_DATUM:raise ValueError('WG active-area identity/datum drift')
  c=_common('Canada','Department of National Defence','conditional_military_entry',
   'Entering or remaining within the WG active exercise area while active without specific authorization',
   'Winchelsea Control may specifically authorize entry; non-active transit is not asserted prohibited by this reference',
   'NOTMAR 35 explanatory notes 5(b), 7; WG hazardous-area notice','https://www.notmar.gc.ca/publications/annual/section-f/f35-en')
  c.update(exceptions='Specific Winchelsea Control authorization; obey range/control directions. No operational permission inferred.',
   activation_condition='Only while WG active. General operating schedule is not an activation interval; off-schedule operations possible.',
   temporal_kind='fixed_geofence_conditionally_activated',source_version='NOTMAR Annual Edition 2026 through monthly edition 09; source receipt 2026-10-20',
   source_datum=row.SOURCE_DATUM,boundary_text=row.BOUNDARY_TEXT,rule_summary=row.RULE_TEXT,
   source_document_sha256=row.SOURCE_DOCUMENT_SHA256,source_diagram_sha256=row.SOURCE_DIAGRAM_SHA256,
   geometry_qualification='Five diagram corners A–E visually checked against Navy published active-area coordinates. NOTMAR 35 explicitly supplies NAD83 default datum. Source precision 0.01 arc-minute. Larger four-point WG operations/airspace envelope is not substituted.',
   excluded_scope='Other Canadian military areas, permanent no-anchor/fishing zone, controlled-access harbour shorelines and vessel-relative buffers remain unqualified')
  return row.ZONE_ID,row.ZONE_ID,'WG active exercise area (conditional)',c
 if source_id == DFO:
  kind=str(row.TypeEN).strip();name=str(row.NameEN).strip();oid=int(row.OBJECTID)
  if kind not in {'Rockfish Conservation Area','Glass Sponge Reef Marine Refuge','Glass Sponge Reef Fishery Closure'}:
   raise ValueError('Unreviewed DFO closure type')
  if not str(row.UrlEN).startswith('https://www.pac.dfo-mpo.gc.ca/'):
   raise ValueError('DFO closure lacks official rule/coordinate link')
  if kind=='Rockfish Conservation Area':
   c=_common('Canada','Fisheries and Oceans Canada','species_gear_fishing_restriction',
    'Commercial: salmon trolling; groundfish bottom/midwater trawl, hook-and-line or trap; tuna hook-and-line; shrimp trawl. Recreational: spearfishing any species; groundfish angling; salmon trolling/jigging/mooching; octopus angling; squid jigging.',
    'Other fisheries may be permitted subject to current notices, sport guide and licence conditions; no vessel-entry prohibition is asserted',
    'DFO RCA activity restrictions; implementing variation-order IDs not qualified',str(row.UrlEN).strip())
   c.update(rule_summary_url='https://www.pac.dfo-mpo.gc.ca/fm-gp/sustain-soutien/rca-acs/rca-regs-acs-eng.html',source_version='Agency rule guide modified 2023-12-19; GIS receipt 2026-10-19/20',
    vessel_gear_species_applicability='Distinct commercial/recreational species and gear list; do not apply this list to Indigenous fisheries without separate source qualification',
    exceptions='Check current DFO fishery notices, sport guide and licence conditions; complete instrument exceptions/history not supplied',activation_condition='Long-term geographically defined RCA reference; legal effective dates and current notice variations unknown',designation_status='RCA as reported by DFO map')
  else:
   established=kind=='Glass Sponge Reef Marine Refuge'
   c=_common('Canada','Fisheries and Oceans Canada','bottom_contact_fishing_restriction',
    'Bottom-contact fishing: prawn traps, shrimp traps/trawls, crab traps, groundfish (including halibut) trawl and hook-and-line',
    'This source does not prohibit vessel transit; other fisheries require separate current-rule checks',
    'DFO Pacific glass sponge reef activity restrictions; implementing variation-order IDs not qualified',str(row.UrlEN).strip())
   howe=oid in {164,165,169,170,181,182,183,189,190,199} or not established
   downrigger=howe and oid!=183
   c.update(rule_summary_url='https://www.pac.dfo-mpo.gc.ca/fm-gp/sustain-soutien/gsr-res/gsr-regs-res-eng.html',source_version='Agency guide modified 2026-04-10; GIS receipt 2026-10-19/20',
    vessel_gear_species_applicability=('Commercial, recreational and Indigenous Food, Social and Ceremonial bottom-contact fishing' if established else 'Commercial and recreational bottom-contact fishing; do not extend closure to Indigenous FSC without a source'),
    exceptions='Downrigger ban does not apply to Defence Islands (OBJECTID 183); all current notices/licence conditions still require review',
    activation_condition='Standing fishing closure reference; no effective-date history supplied',
    designation_status='Established marine refuge' if established else 'Fishing closure in place; marine refuge designation proposed',
    recreational_salmon_downrigger='Prohibited in this Howe Sound closure' if downrigger else 'No additional downrigger ban asserted by this guide')
  c.update(source_feature_id=str(oid),source_type=kind,knowledge_limitation='Exact variation-order IDs, amendments and historical effectiveness remain unqualified; official agency-published reference only',
   geometry_qualification='DFO fishing-regulation GIS feature explicitly links this named closure to its official coordinates/rules page; native polygon retained, no MPA inference. Legal-coordinate cross-check of every coastal vertex remains pending.')
  return 'ca.dfo.closure:'+str(oid),'dfo.closure:'+str(oid),name,c
 if source_id==MPA:
  sid=str(row.get('Site_ID',row.get('site_id',''))).strip()
  if sid not in WAC:return None
  clause,name=WAC[sid]
  if row.Site_Name!=name or row.State!='WA' or row.Design!='Conservation Area':raise ValueError('WDFW/NOAA named-area crosswalk drift')
  c=_common('United States','Washington Department of Fish and Wildlife','fishing_harvest_restriction',
   'Fishing for, or possessing fish, shellfish or wildlife taken from this conservation area',
   'This rule does not prohibit ordinary vessel entry or transit','WAC 220-305-080(1); WAC 220-303-'+clause,
   'https://app.leg.wa.gov/WAC/default.aspx?cite=220-305-080')
  c.update(rule_boundary_url='https://app.leg.wa.gov/WAC/default.aspx?cite=220-303-'+clause,
   effective_start='2017-03-18',effective_date_precision='Rule recodification effective date; not inferred first closure date or boundary history',
   source_version='NOAA MPA inventory 2023 depiction; WAC text checked 2026-10-19/20',
   activation_condition='Standing conservation-area harvest rule reference',exceptions='No exception in WAC 220-305-080(1); other permits/rights not independently adjudicated',
   geometry_qualification='Retained NOAA inventory depiction crosswalked by exact WDFW conservation-area name to its explicit WAC boundary definition. Cartographic reference, not a surveyed legal boundary; ownership, tidal shoreline and landmark geometry not independently re-established.',
   source_feature_id=sid)
  return 'wa.wac220303:'+clause,'noaa.mpa:'+sid,name,c
 if source_id==THEA:
  sid=str(row.ZONE_ID);c=_common('United States','United States Coast Guard','seabed_disturbance_restriction',
   'Seabed disturbance including anchoring, dragging and spudding; sediment-cap integrity', 'Ordinary transit/navigation permitted',
   '33 CFR 165.1329','https://www.ecfr.gov/on/2026-10-15/title-33/section-165.1329')
  c.update(rule_clause=row.RULE_CLAUSE,source_datum=row.SOURCE_DATUM,boundary_text=row.BOUNDARY_TEXT,
   full_rule_text=RULES['165.1329']['text'],activation_condition='Standing activity rule reference',
   exceptions='EPA-associated remediation with advance COTP notice; written COTP waiver subject to full rule',source_version='eCFR 2026-10-15; effective dates unknown')
  return sid,sid,'Thea Foss sediment-cap RNA '+row.RULE_CLAUSE,c
 if source_id==ENC:
  refs=re.findall(r'(?<!\d)(?:334|165)\.\d+',str(row.INFORM))
  if len(set(refs))!=1:return None
  rule=refs[0];suffix='';authority='U.S. Army Corps of Engineers; U.S. Navy enforcing authority' if rule.startswith('334.') else 'United States Coast Guard'
  if rule=='334.1240':
   if row.OBJNAM not in {'Sinclair Inlet naval restriction area 1','Sinclair Inlet naval restriction area 2'}:raise ValueError('Sinclair subarea unqualified')
   suffix='a'+str(row.OBJNAM)[-1];name=str(row.OBJNAM)
   if suffix=='a1':category='vessel_class_entry_permission';prohibited='Vessels of 100 gross tons or greater entering/navigating without permission';permitted='Washington State Ferries on established routes; enforcing-agency permission'
   else:category='military_entry_permission';prohibited='Entry by persons/vessels/craft/articles/things without permission';permitted='Under military/naval supervision or enforcing-agency permission'
   activation='Standing source permission rule'
  elif rule=='165.1321':
   # Three disconnected source OIDs have distinct legal-area clauses. An OID is
   # accepted only from this pinned snapshot; coordinates are checked separately.
   if int(row.OBJECTID) not in {78923,78920,77961}:raise ValueError('Unreviewed military cargo security feature')
   suffix,name={78923:('c1','Blair Waterway military cargo security zone'),78920:('c2','Sitcum Waterway military cargo security zone'),77961:('c3','Budd Inlet military cargo security zone')}[int(row.OBJECTID)]
   category='notice_activated_security_zone';prohibited='Entry, movement within or exit without permission during noticed enforcement';permitted='Public vessels exempt; COTP/designated permission or waiver';activation='COTP notice required; suspension authorizes entry/transit/exit. Current activation unknown'
  elif rule in ENC_RULES:name,category,prohibited,permitted,activation=ENC_RULES[rule]
  else:return None
  c=_common('United States',authority,category,prohibited,permitted,'33 CFR '+rule,'https://www.ecfr.gov/on/2026-10-15/title-33/section-'+rule)
  c.update(rule_clause=suffix or 'See full rule',activation_condition=activation,exceptions='See full rule for all permissions, exemptions and waivers',
   full_rule_text=RULES[rule]['text'],source_version='eCFR 2026-10-15; NOAA ENC GIS snapshot 2026-10-19/20',
   source_datum='NOAA ENC Direct GIS EPSG:4326 (WGS84); regulatory text datum not reinterpreted',
   geometry_qualification='Official chart-derived polygon with explicit matching CFR citation; original chart-cell pieces retained. Source chart vintage/shoreline may differ from rule; this is a partial cartographic reference, not certified legal boundary.',
   chart_name=row.DSNM,chart_source_date=row.SORDAT,chart_source_reference=row.SORIND,
   temporal_kind='fixed_geofence_conditionally_activated' if 'conditional' in category or 'activated' in category else 'standing_activity_reference')
  return 'us.cfr33.'+rule+(':'+suffix if suffix else ''),'noaa.enc197:'+str(int(row.OBJECTID)),name,c
 raise ValueError('Unqualified restriction source '+source_id)

def qualify(row, source_id):
 from .evidence import evidence_context
 if source_id==DFO and row.get('geometry') is not None:
  from .evidence import REVIEW
  import hashlib
  audit=REVIEW['dfo_reef_coordinate_audit'].get(str(int(row.OBJECTID)))
  if audit and hashlib.sha256(row.geometry.wkb).hexdigest()!=audit['provider_geometry_sha256']:
   raise ValueError('DFO provider geometry differs from reviewed coordinate comparison')
 result=_qualify(row,source_id)
 if result is None:return None
 zone,identity,name,context=result
 return zone,identity,name,evidence_context(source_id,identity,context)

def qualifications(row, source_id):
 from .standing import assignments
 from .evidence import evidence_context
 results=assignments(row,source_id,_common,RULES)
 if results is None:
  result=qualify(row,source_id)
  return [] if result is None else [result]
 return [(zone,identity,name,evidence_context(source_id,identity,context)) for zone,identity,name,context in results]

def normalize(frame, source):
 rows=[]
 for _,row in frame.iterrows():
  for identity,source_id,name,c in qualifications(row,source.source_id):
   record=base_record(source,source_feature_id=source_id,governance_feature_id=identity,
    feature_name=name,feature_type=c['restriction_category'],authority=c['authority'],
    jurisdiction=c['country'],legal_authority=c['rule_id'],legal_source_url=c['source_url'],
    source_coverage_status='partial_named_rule_references')
   record.update(EXCLUSION_CATEGORY=c['restriction_category'],PROHIBITED_ACTIVITY=c['prohibited_activity'],
    PERMITTED_ACTIVITY=c['permitted_activity'],EXCEPTIONS=c['exceptions'],RULE_CONTEXT_JSON=json.dumps(c,sort_keys=True),
    EFFECTIVE_START=c.get('effective_start'),EFFECTIVE_END=c.get('effective_end'),geometry=row.geometry)
   rows.append(record)
 return records_frame(rows,frame.crs)
