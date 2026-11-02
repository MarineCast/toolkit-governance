from pathlib import Path
import copy
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from governance.vessel_management.exclusion_zones.qualified import qualify,DFO,ENC,MPA,WAC
from governance.vessel_management.exclusion_zones.theafoss import source_frame

def dfo(kind,name='Example',oid=164):
 return pd.Series(dict(TypeEN=kind,NameEN=name,OBJECTID=oid,UrlEN='https://www.pac.dfo-mpo.gc.ca/fm-gp/sustain-soutien/maps-cartes/example.html'))

def test_rca_specific_gear_is_not_blanket_entry_or_indigenous_closure():
 _,_,_,c=qualify(dfo('Rockfish Conservation Area'),DFO)
 assert c['effective_start'] is None and c['effective_end'] is None
 assert 'salmon trolling' in c['prohibited_activity'] and 'spearfishing' in c['prohibited_activity']
 assert 'no vessel-entry' in c['permitted_activity'] and 'Indigenous' in c['vessel_gear_species_applicability']
 assert 'variation-order IDs not qualified' in c['rule_id']

def test_proposed_refuge_is_an_existing_fishing_closure_with_narrower_applicability():
 c=qualify(dfo('Glass Sponge Reef Fishery Closure','Alberta Bay',163),DFO)[3]
 assert c['designation_status']=='Fishing closure in place; marine refuge designation proposed'
 assert c['recreational_salmon_downrigger'].startswith('Prohibited')
 assert 'do not extend closure to Indigenous FSC' in c['vessel_gear_species_applicability']

def test_defence_islands_exception_is_not_applied_to_east_defence():
 a=qualify(dfo('Glass Sponge Reef Marine Refuge','Howe Sound - Defence Islands',183),DFO)[3]
 b=qualify(dfo('Glass Sponge Reef Marine Refuge','East Defence Islands',170),DFO)[3]
 assert a['recreational_salmon_downrigger'].startswith('No additional')
 assert b['recreational_salmon_downrigger'].startswith('Prohibited')
 assert 'Indigenous Food, Social and Ceremonial' in a['vessel_gear_species_applicability']

def test_dfo_designation_and_nonofficial_link_fail_closed():
 with pytest.raises(ValueError):qualify(dfo('Marine Protected Area'),DFO)
 row=dfo('Rockfish Conservation Area');row.UrlEN='https://example.org/map'
 with pytest.raises(ValueError):qualify(row,DFO)

def enc(rule,name=None,oid=1):
 return pd.Series(dict(INFORM='33 CFR '+rule,OBJNAM=name,OBJECTID=oid,DSNM='chart',SORDAT='200302',SORIND='NOAA'))

def test_military_activity_not_vessel_ban_and_multipart_identity_dedup():
 a=qualify(enc('334.1210',oid=1),ENC);b=qualify(enc('334.1210',oid=2),ENC)
 assert a[0]==b[0] and a[1]!=b[1]
 assert 'Navigation is not prohibited' in a[3]['permitted_activity']
 assert a[3]['effective_start'] is None
 assert qualify(enc('334.1200'),ENC) is None # Entry-at-own-risk rule not a prohibition.
 assert qualify(enc('334.1220'),ENC) is None # Ambiguous subarea assignment withheld.

def test_vessel_size_exception_security_notice_and_drydock_are_distinct():
 c=qualify(enc('334.1240','Sinclair Inlet naval restriction area 1'),ENC)[3]
 assert '100 gross tons' in c['prohibited_activity'] and 'Ferries' in c['permitted_activity']
 c=qualify(enc('165.1321',oid=78923),ENC)[3]
 assert 'COTP notice required' in c['activation_condition'] and 'Public vessels exempt' in c['permitted_activity']
 c=qualify(enc('165.1340'),ENC)[3]
 assert c['temporal_kind']=='fixed_geofence_conditionally_activated'
 with pytest.raises(ValueError):qualify(enc('165.1321',oid=99),ENC)

def test_wac_explicit_crosswalk_not_no_take_inventory_inference():
 for site,(clause,name) in WAC.items():
  row=pd.Series(dict(Site_ID=site,Site_Name=name,State='WA',Design='Conservation Area'))
  _,_,_,c=qualify(row,MPA)
  assert '220-303-'+clause in c['rule_id'] and 'vessel entry or transit' in c['permitted_activity']
  assert 'not a surveyed legal boundary' in c['geometry_qualification']
 row=pd.Series(dict(Site_ID='other',Site_Name='Any MPA',State='WA',Design='Conservation Area'))
 assert qualify(row,MPA) is None
 row.Site_ID='WA507'
 with pytest.raises(ValueError):qualify(row,MPA)

def test_theafoss_requires_two_named_four_corner_nad83_areas(tmp_path):
 pairs='Point 1: 47°15′43.49″ N, 122°26′23.29″ W; Point 2: 47°15′44.59″ N, 122°26′19.89″ W; Point 3: 47°15′39.01″ N, 122°26′15.99″ W; Point 4: 47°15′37.91″ N, 122°26′19.39″ W.'
 text='<DIV8 N="165.1329">'+''.join(f'<P>({i}) All waters of the Thea Foss Waterway bounded by a line connecting the following points: {pairs} [Datum: NAD 1983].</P>' for i in (1,2))+'</DIV8>'
 p=tmp_path/'rule.xml';p.write_text(text);f=source_frame(p)
 assert f.ZONE_ID.tolist()==['us.cfr33.165.1329:a1','us.cfr33.165.1329:a2'] and f.crs.to_epsg()==4326
 p.write_text(text.replace('NAD 1983','unknown'))
 with pytest.raises(ValueError):source_frame(p)
