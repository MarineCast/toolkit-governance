"""Finite reviewed standing-source crosswalks, retaining native reference geometry."""
from importlib.resources import files
import hashlib,json

REVIEW=json.loads(files('governance.resources').joinpath('exclusion_completion_20261020.json').read_text())
MPA='noaa_mpa_inventory_2023'
ENC='noaa_enc_harbor_rule_references_20261019'
FWS='fws_national_wildlife_refuges'
TORPEDO='noaa_enc_torpedo_references_20261020'
SMITH='noaa_enc_smith_reference_20261020'
NEW_SOURCES={FWS,TORPEDO,SMITH}
WAC={
 'WA102':('303-010','Brackett’s Landing / Edmonds conservation area','conservation'),
 'WA606':('303-010','Brackett’s Landing / Edmonds conservation area','conservation'),
 'WA516':('302-010','Admiralty Head Marine Preserve','admiralty'),
 'WA600':('302-020','Carkeek Park Marine Preserve','seattle'),
 'WA518':('302-030','Colvos Passage Marine Preserve','colvos'),
 'WA601':('302-040','Discovery Park Marine Preserve','seattle'),
 'WA602':('302-050','Emma Schmitz Marine Preserve','seattle'),
 'WA604':('302-060','Golden Gardens Marine Preserve','seattle'),
 'WA603':('302-070','Lincoln Park Marine Preserve','seattle'),
 'WA605':('302-080','Richey Viewpoint Marine Preserve','seattle'),
 'WA529':('302-090','Saltwater State Park Marine Preserve','saltwater'),
 'WA44':('302-100:1','False Bay Marine Preserve','sanjuan'),
 'WA47':('302-100:2','Friday Harbor Marine Preserve','sanjuan'),
 'WA34':('302-100:3','Argyle Lagoon Marine Preserve','sanjuan'),
 'WA87':('302-100:4','Yellow and Low Islands Marine Preserve','yellowlow'),
 'WA72':('302-100:5','Shaw Island Marine Preserve','shaw'),
 'WA508':('302-110','Titlow Beach Marine Preserve','titlow'),
 'WA515':('302-120',"Z’s Reef Marine Preserve",'zsreef'),
}
ACTIVITIES={
 'conservation':('Fishing for or possessing fish, shellfish or wildlife taken from the conservation area','No ordinary vessel entry/transit prohibition is asserted'),
 'admiralty':('Taking fish and wildlife; taking shellfish except sea cucumbers and sea urchins','Sea cucumber/urchin exception; other applicable rules still control'),
 'colvos':('Taking shellfish/wildlife; all commercial fish harvest; recreational fish harvest except personal-use salmon trolling','Salmon trolling from a vessel under power, in gear, making forward progress may be lawful'),
 'sanjuan':('Taking shellfish; taking food fish other than salmon, subject to stated herring exception','Salmon and herring exceptions as stated; other fishing rules still apply'),
 'yellowlow':('Taking shellfish and food fish in Yellow and Low Islands Preserve','Do not apply the other San Juan subareas’ food-fish exceptions here'),
 'shaw':('Taking shellfish except crab from Parks Bay; taking food fish other than salmon, subject to herring exception','Parks Bay crab, salmon and herring exceptions as stated; other rules still apply'),
 'titlow':('Taking shellfish/wildlife; commercial harvest of all fish; recreational harvest except the stated salmon exception','Salmon with artificial lures from shore or a nonmotorized vessel may be lawful'),
 'zsreef':('Taking shellfish/wildlife; commercial harvest of all fish; recreational harvest except salmon fly-fishing exception','Salmon with fly fishing gear defined in WAC 220-310-150 may be lawful'),
 'seattle':('Removing intertidal organisms except lawful finfish hook-and-line harvest','Finfish hook-and-line exception; other organisms must be returned unharmed where found. Preserve only to 4.5 feet below MLLW as defined'),
 'saltwater':('All recreational harvest','No commercial-harvest or vessel-entry prohibition inferred from this recreational rule'),
}
def _check(row,key):
 expected=REVIEW['native_records'][key]
 lookup={str(field).casefold():field for field in row.index}
 for field,value in expected['identity'].items():
  if field.casefold() not in lookup or str(row[lookup[field.casefold()]]).strip()!=str(value).strip():raise ValueError('Standing-source identity drift: '+key)
 if row.get('geometry') is not None and hashlib.sha256(row.geometry.wkb).hexdigest()!=expected['geometry_sha256']:
  raise ValueError('Standing-source geometry drift: '+key)

def assignments(row,source,common,rules):
 """None delegates to prior crosswalk; [] is reviewed but intentionally unselected."""
 if source==MPA:
  site=str(row.get('Site_ID',row.get('site_id',''))).strip()
  if site not in WAC:return None
  _check(row,'mpa:'+site);clause,name,kind=WAC[site];prohibited,permitted=ACTIVITIES[kind]
  c=common('United States','Washington Department of Fish and Wildlife','fishing_harvest_restriction',prohibited,permitted,
   'WAC 220-'+clause+'; WAC 220-305-080(1)' if kind=='conservation' else 'WAC 220-'+clause+'; WAC 220-305-080(2)',
   'https://app.leg.wa.gov/WAC/default.aspx?cite=220-305-080')
  c.update(exceptions=permitted,activation_condition='Standing source harvest/activity reference; no complete amendment history',
   rule_boundary_url='https://app.leg.wa.gov/WAC/default.aspx?cite=220-'+clause.split(':')[0],
   full_rule_text=REVIEW['wac_harvest_text'],source_version='NOAA MPA inventory 2023; WAC and WDFW checked 2026-10-20',
   source_feature_id=site,native_site_name=str(row.Site_Name),native_designation=str(row.Design),
   geometry_qualification='Named NOAA inventory depiction linked to explicit WAC boundary/activity clauses. Provider reference only: surveyed ownership, tidal elevation, depth contours and marker positions not independently re-established.',
   effective_start='2017-03-18',effective_date_precision='Rule recodification date; not first establishment or reconstructed boundary history',
   vessel_gear_species_applicability=prohibited+'; '+permitted)
  if site=='WA529':c['boundary_crosscheck']='All four explicit WAC water corners lie within 0.18 m of the native inventory boundary in EPSG:32610. Native Underwater Park name/designation retained; DNR high-tide markers/shoreline remain unqualified.'
  if site in {'WA102','WA606'}:c['source_relationship']='WAC explicitly includes Edmonds Underwater Park within Brackett’s Landing; both native records form one counted regulatory area, with all overlapping source parts retained.'
  return [('wa.wac220'+clause.replace('-',':',1),'noaa.mpa:'+site,name,c)]
 if source==FWS:
  code=int(row.ORGCODE)
  if code not in {13532,13533}:return []
  _check(row,'fws:'+str(code));sanjuan=code==13532
  c=common('United States','U.S. Fish and Wildlife Service','habitat_landing_access_restriction',
   'Public access/landing on refuge lands, except specifically authorized access and designated public-use areas',
   'San Juan public-use areas on Matia and Turn Islands are excepted; separately authorized uses may apply' if sanjuan else 'Only specifically authorized access; no general public access',
   '50 CFR 26.21; current FWS refuge public-access notice',
   'https://www.fws.gov/refuge/san-juan-islands/visit-us' if sanjuan else 'https://www.fws.gov/refuge/protection-island/visit-us')
  c.update(exceptions=c['permitted_activity'],activation_condition='Standing public-access reference; no permit or visit-specific determination',
   source_version='Native FWS refuge boundary binding; agency access pages checked 2026-10-20',
   full_rule_text=REVIEW['fws_26_21_text'],source_feature_id=str(int(row.OBJECTID)),native_orgcode=str(code),native_globalid=str(row.GlobalID),
   geometry_qualification='Original named FWS refuge boundary, retained as an administrative reference extent tied to an explicit access rule; not inferred from refuge designation. Public-use subareas are not separately delineated; geometry is not wholly closed to every person.',
   unmapped_restriction='FWS also states a 200-yard watercraft closure. This product does not invent its shoreline buffer or assert that the administrative refuge boundary supplies the buffer baseline.',
   public_use_geometry='Matia and Turn public-use areas remain exceptions with unqualified subarea geometry' if sanjuan else 'No general public-use area reported by the agency notice')
  return [('us.fws.access:'+str(code),'fws.refuge:'+str(code),'San Juan Islands refuge access reference' if sanjuan else 'Protection Island refuge access reference',c)]
 if source==ENC:
  oid=int(row.OBJECTID)
  if oid in {77962,77963,77964,77965}:pairs=[('334.1250','a','Carr Inlet operations-area reference')]
  elif oid in {78962,78965,78990}:pairs=[('334.1220','a1','Bangor naval restricted area 1')]
  elif oid in {78963,78988}:pairs=[('334.1220','a2','Bangor magnetic-silencing area 2'),('165.1302','b','Bangor security-zone anchorage')]
  elif oid in {78961,78964,78967,78969}:pairs=[('165.1302','a','Bangor main security zone')]
  else:return None
 elif source==TORPEDO:
  oid=int(row.OBJECTID)
  if oid in {3731,3736,3737}:pairs=[('334.1190','a','Hood Canal torpedo ranging area')]
  elif oid in {3729,3730,3733,3734,3735,3741,3742}:pairs=[('334.1190','b','Dabob Bay testing area')]
  else:raise ValueError('Unreviewed torpedo source part')
 elif source==SMITH:pairs=[('334.1180','a','Smith Island scheduled restricted area')];oid=int(row.OBJECTID)
 else:return None
 _check(row,source+':'+str(oid));out=[]
 for rule,subarea,name in pairs:
  category='military_entry_permission';authority='U.S. Army Corps of Engineers; U.S. Navy enforcing authority'
  if rule=='334.1180':
   prohibited='Entry/remain between 0700 and 1200 local daily, except enforcing-agency authorization and stated fishing exception'
   permitted='Commercial gillnet fishing during scheduled fishing periods June 15–October 15; enforcing agency may extend closure date as stated in rule'
   activation='Recurring local-time 0700–1200 source condition; no daily history or vessel applicability synthesized'
  elif rule=='334.1190' and subarea=='a':
   category='conditional_military_entry';prohibited='Entry/remain during naval exercises in the source ranging area'
   permitted='Navigation permitted otherwise; one-quarter-NM shore navigation lanes are not closed; vessels already underway shall not delay progress'
   activation='Only while naval exercises in progress; red flag and notices. Typical operating schedule is not an activation feed'
  elif rule=='334.1190':
   category='military_activity_restriction';prohibited='Trawling/dragging; anchoring except between shore and 10-fathom line; non-incidental propeller/noise during actual testing'
   permitted='Anchoring exception shoreward of 10-fathom line; incidental noise and passage between tests; log-tow/slow traffic arrangements as stated'
   activation='Trawl/drag and anchoring rules standing; noise/testing conditions only during actual testing, indicated by flashing red beacons'
  elif rule=='334.1220' and subarea=='a1':
   prohibited='Entry without Commander Naval Submarine Base Bangor permission';permitted='Commander or authorized-representative permission';activation='Standing permission reference'
  elif rule=='334.1220':
   category='military_activity_restriction';prohibited='Equipment that may foul underwater installations, including anchors/grapnels; non-buoyant dumping; navigation during magnetic-silencing operations outside Area 1'
   permitted='Outside Area 1, navigation permitted except while magnetic-silencing operations are in progress';activation='Equipment/dumping rules at all times; transit condition indicated by quick-flashing red pier beacons'
  elif rule=='334.1250':
   category='conditional_military_activity';prohibited='Red-beacon range use: power/non-power vessel restrictions with source corridors and commercial/tow exceptions; local hydrophone and buoy-testing proximity rules remain rule-only'
   permitted='Non-active navigation; low-water shore corridors, through commercial traffic/tows, tow havens, range-control clearance and Warden patrol exceptions in full rule'
   activation='Red/green beacons or substitute flags; no actual operation calendar. Source typical days/hours never used as activity history'
  else:
   authority='United States Coast Guard';prohibited='Entry/remain without required authorization under the security rule'
   permitted='Qualifying U.S. public vessels other than U.S. Naval vessels; Navy-contract, exemption-certificate and COTP permission provisions as stated; authorized vessels may anchor in security-zone anchorage'
   activation='Standing security/authorization reference; no present enforcement classification'
  c=common('United States',authority,category,prohibited,permitted,'33 CFR '+rule+' '+subarea,
   'https://www.ecfr.gov/on/2026-10-15/title-33/section-'+rule)
  c.update(exceptions=permitted,activation_condition=activation,rule_clause=subarea,
   full_rule_text=REVIEW['cfr'][rule]['text']+(('\n'+REVIEW['cfr']['165.33']['text']) if rule=='165.1302' else ''),
   source_version='eCFR 2026-10-15; pinned NOAA chart source and receipt',source_feature_id=str(oid),
   source_datum='NOAA chart-derived EPSG:4326; unlabeled regulatory coordinates not silently interpreted as NAD83',
   geometry_qualification='Explicit CFR-cited official chart depiction and reviewed named subarea crosswalk; original chart pieces retained. Partial cartographic reference, not surveyed legal boundary or uniform activity prohibition.',
   chart_name=row.DSNM,chart_source_date=row.SORDAT,chart_source_reference=row.SORIND,
   temporal_kind='fixed_reference_with_activity_specific_conditions')
  if rule=='334.1250':c['unmapped_local_conditions']='100-yard hydrophone, 1000-yard buoy-testing and non-power course-line distances are rule-only; no speculative buoy coordinates or distance polygons were created.'
  if rule=='334.1190' and subarea=='b':c['unmapped_local_conditions']='10-fathom anchoring exception is retained in text; no bathymetric exception polygon invented.'
  if rule=='165.1302' and oid==78967:c['native_citation_qualification']='Native chart also prints 34.1220; that typo is preserved and is not treated as a valid USACE citation.'
  native=f'noaa.enc:{source}:{oid}:{rule}:{subarea}'
  out.append(('us.cfr33.'+rule+':'+subarea,native,name,c))
 return out
