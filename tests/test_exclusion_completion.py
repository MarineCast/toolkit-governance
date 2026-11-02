import pandas as pd
import pytest
from shapely.geometry import box
from governance.vessel_management.exclusion_zones.qualified import qualifications
from governance.vessel_management.exclusion_zones.standing import REVIEW,WAC,MPA,ENC,FWS,TORPEDO,SMITH

def native(key):return pd.Series(REVIEW['native_records'][key]['identity'])

def test_named_wac_roster_preserves_native_designations_and_counts_bracketts_once():
 results=[qualifications(native('mpa:'+site),MPA)[0] for site in WAC]
 assert len(results)==18 and len({r[0] for r in results})==17
 a,b=[r for r in results if r[0]=='wa.wac220303:010'];assert a[1]!=b[1]
 c=qualifications(native('mpa:WA529'),MPA)[0][3]
 assert qualifications(native('mpa:WA529').rename({'Site_ID':'site_id'}),MPA)[0][0]=='wa.wac220302:090'
 assert c['native_designation']=='Underwater Park' and '0.18 m' in c['boundary_crosscheck']
 assert c['prohibited_activity']=='All recreational harvest' and 'commercial-harvest' in c['permitted_activity']

def test_wac_species_gear_exceptions_do_not_become_blanket_entry_bans():
 def c(site):return qualifications(native('mpa:'+site),MPA)[0][3]
 assert 'sea cucumbers and sea urchins' in c('WA516')['prohibited_activity']
 assert 'under power' in c('WA518')['permitted_activity']
 assert 'nonmotorized' in c('WA508')['permitted_activity']
 assert 'fly fishing' in c('WA515')['permitted_activity']
 assert 'hook-and-line' in c('WA600')['permitted_activity']
 assert 'Parks Bay crab' in c('WA72')['permitted_activity']
 assert 'food fish' in c('WA87')['prohibited_activity'] and 'Do not apply' in c('WA87')['permitted_activity']

def test_shared_chart_circle_retains_two_distinct_rule_assignments_and_typo_is_not_authority():
 r=qualifications(native(ENC+':78963'),ENC)
 assert {x[0] for x in r}=={'us.cfr33.334.1220:a2','us.cfr33.165.1302:b'}
 assert len({x[1] for x in r})==2
 c=next(x[3] for x in r if '334.1220' in x[0]);assert 'Outside Area 1' in c['permitted_activity']
 r=qualifications(native(ENC+':78967'),ENC);assert len(r)==1 and r[0][0]=='us.cfr33.165.1302:a'
 assert 'typo is preserved' in r[0][3]['native_citation_qualification']

def test_torpedo_subareas_keep_testing_navigation_and_depth_conditions_separate():
 r=[x for key in REVIEW['native_records'] if key.startswith(TORPEDO+':') for x in qualifications(native(key),TORPEDO)]
 assert len(r)==10 and len({x[0] for x in r})==2
 a=next(x[3] for x in r if x[0].endswith(':a'));b=next(x[3] for x in r if x[0].endswith(':b'))
 assert 'one-quarter-NM' in a['permitted_activity'] and '10-fathom' in b['permitted_activity']
 assert 'incidental noise' in b['permitted_activity'] and 'no bathymetric' in b['unmapped_local_conditions']

def test_smith_daily_local_condition_is_not_a_dated_activation_series():
 c=qualifications(native(SMITH+':120420'),SMITH)[0][3]
 assert '0700 and 1200 local' in c['prohibited_activity']
 assert 'June 15–October 15' in c['permitted_activity'] and c['effective_start'] is None
 assert c['active_applicability_status'].startswith('Unknown')

def test_fws_access_uses_explicit_rule_with_public_use_exceptions_and_no_invented_buffer():
 a=qualifications(native('fws:13532'),FWS)[0][3];b=qualifications(native('fws:13533'),FWS)[0][3]
 assert 'Matia and Turn' in a['exceptions'] and 'No general public-use' in b['public_use_geometry']
 assert 'does not invent' in a['unmapped_restriction'] and '200-yard' in a['unmapped_restriction']
 assert '50 CFR 26.21' in a['rule_id'] and 'authorized' in b['exceptions']

def test_geometry_drift_fails_closed_and_tc_pin_review_does_not_invent_equivalence():
 r=native('mpa:WA529');r['geometry']=box(0,0,1,1)
 with pytest.raises(ValueError,match='geometry drift'):qualifications(r,MPA)
 tc=REVIEW['tc'];assert not tc['legacy_payload_available'] and 'Not provable' in tc['full_page_byte_equivalence']
 assert 'exactly' in tc['new_pin_disposition'] and tc['current_html_sha256']!=tc['legacy_html_sha256']
 assert '20 m or less' in tc['selected_instrument_text'] and 'existing right, other than for fishing' in tc['selected_instrument_text']
