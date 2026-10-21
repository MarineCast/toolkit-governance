import copy
import pandas as pd
import pytest
from shapely.geometry import box
from governance.vessel_management.exclusion_zones.qualified import DFO,ENC,THEA,MPA,qualify
from governance.vessel_management.exclusion_zones.evidence import evidence_context,REVIEW

def dfo(oid,name):
 return pd.Series(dict(OBJECTID=oid,NameEN=name,TypeEN='Glass Sponge Reef Fishery Closure',UrlEN='https://www.pac.dfo-mpo.gc.ca/fm-gp/sustain-soutien/maps-cartes/example.html'))

def test_current_fsc_notice_updates_exactly_three_existing_fishing_closures():
 for oid,name in [(166,'Carmelo Point'),(167,'Collingwood Channel'),(188,'Langdale')]:
  c=qualify(dfo(oid,name),DFO)[3]
  assert 'Indigenous Food, Social and Ceremonial' in c['vessel_gear_species_applicability']
  assert '2026-217' in c['variation_order_references'] and '2026-05-29' in c['activity_effective_dates']
  assert '2022-01-17' in c['activity_effective_dates']
  assert c['effective_start'] is None # Earliest date is activity specific.
  assert c['designation_status'].endswith('designation proposed')
  assert 'NAD83' in c['published_coordinate_datum']
 for oid,name in [(163,'Alberta Bay'),(200,'Mariners Rest')]:
  c=qualify(dfo(oid,name),DFO)[3]
  assert 'do not extend closure to Indigenous FSC' in c['vessel_gear_species_applicability']
  assert '2026-217' not in c['variation_order_references']

def test_evidence_annotation_is_idempotent_and_separates_geometry_and_activation():
 c=qualify(dfo(166,'Carmelo Point'),DFO)[3];before=copy.deepcopy(c)
 assert evidence_context(DFO,'dfo.closure:166',c)==before==c
 assert c['geometry_evidence_status'].startswith('Provider reference')
 assert c['active_applicability_status'].startswith('Unknown')
 for source in ['tc_srkw_interim_order_2026','uscg_lockheed_rna_20261015',THEA]:
  c=evidence_context(source,'example',{})
  assert c['geometry_evidence_status'].startswith('Parsed closed legal-instrument')
  assert c['active_applicability_status'].startswith('Unknown')
 with pytest.raises(ValueError):evidence_context('invented','example',{})

def test_coordinate_disagreement_is_preserved_and_changed_geometry_fails_closed():
 assert len(REVIEW['dfo_reef_coordinate_audit'])==22
 for oid in (182,191):
  c=evidence_context(DFO,'dfo.closure:'+str(oid),{})
  assert 'Native provider geometry preserved' in c['coordinate_discrepancy'] if oid==182 else 'Conflicting provider depictions retained' in c['coordinate_discrepancy']
 row=dfo(166,'Carmelo Point');row['geometry']=box(-123.5,49.4,-123.4,49.5)
 with pytest.raises(ValueError,match='geometry differs'):qualify(row,DFO)

def test_wac_daymarker_check_is_approximate_and_uses_daybeacon_not_buoy():
 c=evidence_context(MPA,'noaa.mpa:WA510',{})
 assert 'not the nearby lighted buoy' in c['landmark_check']
 assert '365.76' in c['boundary_comparison'] and 'Approximate' in c['boundary_comparison']
 assert c['geometry_evidence_status'].startswith('Provider reference')

def test_wg_is_active_only_five_point_area_and_missing_companion_fails(tmp_path,monkeypatch):
 from governance.vessel_management.exclusion_zones import nanoose
 import hashlib
 text='North American Datum 1983; vessels are required to remain clear whenever WG is active; Area WG constitutes a defence establishment'
 p=tmp_path/'notmar-f35.html';p.write_text(text)
 monkeypatch.setattr(nanoose,'DOCUMENT_SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
 with pytest.raises(ValueError,match='companion'):nanoose.source_frame(p)
 image=p.with_name('notmar-wg-active.jpg');image.write_bytes(b'reviewed diagram fixture')
 monkeypatch.setattr(nanoose,'DIAGRAM_SHA256',hashlib.sha256(image.read_bytes()).hexdigest())
 f=nanoose.source_frame(p);assert len(f)==1 and f.crs.to_epsg()==4326
 assert len(f.iloc[0].SOURCE_COORDINATES)==5
 assert f.geometry.iloc[0].bounds[0]>-124.14 # Larger four-corner WG envelope reaches -124.1583.
 from governance.vessel_management.exclusion_zones.qualified import NAVY
 c=qualify(f.iloc[0],NAVY)[3]
 assert c['temporal_kind']=='fixed_geofence_conditionally_activated' and 'Only while WG active' in c['activation_condition']
 assert c['effective_start'] is None and c['active_applicability_status'].startswith('Unknown')
 assert 'rule_summary' in c and 'full_rule_text' not in c
 p.write_text(text+'changed')
 with pytest.raises(ValueError,match='source-version drift'):nanoose.source_frame(p)
