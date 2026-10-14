import json
from importlib.resources import files
from governance.shared.availability import availability_matrix
from governance.shared.config import load_governance_config

def test_matrix_is_packaged_current_and_separates_acceptance_dimensions():
    matrix=availability_matrix(load_governance_config())
    assert matrix==json.loads(files('governance').joinpath('resources/availability.json').read_text())
    rows=matrix['rows']
    assert {row['layer'] for row in rows} >= {'marine_protected_areas','management_areas','speed_restriction_zones','gear_restrictions'}
    assert len({row['region'] for row in rows})==8
    assert all(row['legal_currentness']=='not_verified' and row['acquisition_completeness']=='not_evaluated' for row in rows)
    arctic=[row for row in rows if row['region']=='arctic_alaska' and row['system']=='adfg_groundfish_statistical_areas']
    assert arctic[0]['geographic_completeness']=='unavailable'
    assert all(row['implementation']=='not_implemented' for row in rows if row['layer']=='gear_restrictions')
