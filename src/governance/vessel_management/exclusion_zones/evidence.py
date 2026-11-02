"""Explicit evidence classes; a restriction reference never certifies activation."""
from importlib.resources import files
import json

REVIEW=json.loads(files('governance.resources').joinpath('exclusion_qualification_20261020.json').read_text())
DFO='dfo_pacific_closure_references_20261019'
COORDINATE_SOURCES={'tc_srkw_interim_order_2026','uscg_lockheed_rna_20261015','uscg_theafoss_rna_20261015'}
from .standing import NEW_SOURCES, REVIEW as COMPLETION
PROVIDER_SOURCES={DFO,'noaa_enc_harbor_rule_references_20261019','noaa_mpa_inventory_2023'} | NEW_SOURCES
FSC_2026={166:'Carmelo Point',167:'Collingwood Channel',188:'Langdale'}
REEF_2019={164,165,169,170,181,189,190,199}
REEF_2022={163,166,167,188,200}

def evidence_context(source_id,identity,detail):
 c=dict(detail)
 if c.get("evidence_review_version")=="2026-10-20-2":return c
 if source_id in COORDINATE_SOURCES:
  c.update(geometry_evidence_status='Parsed closed legal-instrument coordinate ring; source-version geometry only',
   legal_instrument_evidence='Cited instrument coordinate clauses checked; amendments, current applicability and enforcement not certified')
  if source_id=='tc_srkw_interim_order_2026':
   c.update(source_version_qualification=COMPLETION['tc']['new_pin_disposition'],prior_pin_equivalence=COMPLETION['tc']['full_page_byte_equivalence'],source_document_sha256=COMPLETION['tc']['current_html_sha256'],instrument_source_knowledge_at_utc=COMPLETION['tc']['source_knowledge_at_utc'],selected_instrument_text=COMPLETION['tc']['selected_instrument_text'])
 elif source_id=='dnd_wg_active_reference_20261020':
  c.update(geometry_evidence_status='Agency-published active-area coordinate diagram; source-version reference',
   legal_instrument_evidence='NOTMAR datum, active-area boundary and active-only direction checked; underlying regulations, designation changes and operational activation not certified')
 elif source_id in PROVIDER_SOURCES:
  c.update(geometry_evidence_status='Provider reference geometry; not independently established legal boundary',
   legal_instrument_evidence='Published activity/rule crosswalk checked; complete instruments, boundary equivalence and amendments not certified')
 else:raise ValueError('Unclassified exclusion geometry evidence source: '+source_id)
 c.update(active_applicability_status='Unknown for any requested date, vessel, person or activity; no operational activation feed',
  mandatory_advisory_status='Mandatory as reported by cited instrument/agency; this record is a qualified reference',
  use_qualification='Static research/reference only; not navigation, legal compliance, present activation or model eligibility')
 if source_id==DFO:
  oid=int(identity.rsplit(':',1)[1]);audit=REVIEW['dfo_reef_coordinate_audit'].get(str(oid))
  if audit:
   c.update(geometry_evidence_status='Provider reference geometry compared with published agency coordinate rings; legal equivalence remains unqualified',
    coordinate_comparison=f"Numerical boundary Hausdorff distance {audit['numeric_coordinate_hausdorff_m']:.3f} m in EPSG:32610; no datum assumed where source omits it. Native provider geometry retained.",
    rule_review_date='2026-10-20',
    legal_instrument_evidence='Agency notices identify variation orders; underlying signed orders, amendments and current legal applicability not independently certified')
   if oid in REEF_2022:
    c.update(variation_order_references='2022-RCT-077 and 2022-078 as reported by FN0039 (2022)',
     rule_notice_url=REVIEW['documents']['dfo-FN0039-2022.html']['source_url'],
     rule_notice_sha256=REVIEW['documents']['dfo-FN0039-2022.html']['sha256'],
     activity_effective_dates='Commercial/recreational bottom-contact closure: 2022-01-17; recreational salmon downrigger condition announced for 2022-04-01. No continuous history reconstructed.')
   elif oid in REEF_2019:
    c.update(variation_order_references='2019-95, 2019-96 and 2019-97 as reported by FN0205 (2019)',
     rule_notice_url=REVIEW['documents']['dfo-FN0205-2019.html']['source_url'],
     rule_notice_sha256=REVIEW['documents']['dfo-FN0205-2019.html']['sha256'],
     activity_effective_dates='2019-04-01 as stated in notice; not a complete amendment or enforcement history')
   else:
    c.update(variation_order_references='2015-293 as reported by FN0571 (2015)',
     rule_notice_url=REVIEW['documents']['dfo-FN0571-2015.html']['source_url'],
     rule_notice_sha256=REVIEW['documents']['dfo-FN0571-2015.html']['sha256'])
   c['knowledge_limitation']='Underlying variation-order instruments and full amendments/history remain unqualified; agency notice identifiers and coordinate comparison are supplied separately from the provider GIS.'
   if oid in {182,191}:
    c['coordinate_discrepancy']=COMPLETION['DFO_reconciliation'][str(oid)]
   if oid in FSC_2026:
    if c.get('designation_status')!='Fishing closure in place; marine refuge designation proposed':raise ValueError('DFO 2026 closure designation drift')
    c.update(vessel_gear_species_applicability='Commercial, recreational and Indigenous Food, Social and Ceremonial bottom-contact fishing; activity-specific dates differ',
     variation_order_references=c['variation_order_references']+'; 2026-217 as reported by FN0521 (2026)',
     supplemental_rule_notice_url=REVIEW['documents']['dfo-FN0521-2026.html']['source_url'],
     supplemental_rule_notice_sha256=REVIEW['documents']['dfo-FN0521-2026.html']['sha256'],
     supplemental_notice_knowledge_at_utc=REVIEW['documents']['dfo-FN0521-2026.html']['retrieved_at_utc'],
     activity_effective_dates=c['activity_effective_dates']+' Indigenous FSC bottom-contact closure: 2026-05-29 indefinitely as reported by FN0521; not a claim that the same FSC restriction applied in 2022.',
     published_coordinate_datum='FN0521 specifies NAD83 and rhumb-line segments; provider GIS is retained with the measured boundary difference',
     rule_id='DFO glass-sponge closure notices FN0039 (2022) / FN0521 (2026); variation orders 2022-RCT-077, 2022-078 and 2026-217 reported; full orders unqualified')
 if source_id=='noaa_mpa_inventory_2023' and identity=='noaa.mpa:WA510':
  x=REVIEW['wac_landmark_check'];c.update(landmark_check='NOAA ENC Orchard Rocks Daybeacon OBJECTID 100742, chart source 1994-11-16; not the nearby lighted buoy',
   boundary_comparison=f"WAC radius {x['required_radius_m']} m; retained inventory vertices lie {x['inventory_vertex_radius_min_m']:.3f}–{x['inventory_vertex_radius_max_m']:.3f} m from NOAA beacon. Approximate cartographic agreement only.")
 c["evidence_review_version"]="2026-10-20-2"
 return c
