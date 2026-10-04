from dataclasses import replace

import geopandas as gpd
import pytest
from shapely.geometry import box

from governance.jurisdiction.county_regional_boundaries.normalize import normalize as counties
from governance.protected_areas.wildlife_refuges.normalize import normalize as refuges
from governance.shared.config import load_governance_config


def frame(rows):
    return gpd.GeoDataFrame(rows, geometry=[box(-124, 48, -123, 49)] * len(rows), crs=4326)


def test_county_keeps_leading_zero_ids_and_vintage_not_legal_date():
    source = load_governance_config().sources['census_counties_2025']
    raw = frame([{'GEOID': '02013', 'NAME': 'Aleutians East', 'FUNCSTAT': 'A', 'ALAND': 42}])
    result = counties(raw, source)
    assert result.CENSUS_GEOID.tolist() == ['02013']
    assert result.SOURCE_FEATURE_ID.tolist() == ['census_counties_2025:02013']
    assert result.CENSUS_ALAND.tolist() == ['42']
    assert result.SOURCE_VINTAGE.tolist() == ['2025-01-01']
    assert result.EFFECTIVE_START.isna().all()
    assert result.LEGAL_AUTHORITY.isna().all()
    assert not result.MODEL_ELIGIBLE.any()
    for ids in ([2013], ['02013', '02013'], [None]):
        with pytest.raises(ValueError, match='GEOID'):
            counties(frame([{'GEOID': value} for value in ids]), source)


def test_refuge_filters_preserve_system_status_and_year_without_inference():
    sources = load_governance_config().sources
    us = refuges(frame([
        {'OBJECTID': 1, 'ORGNAME': 'Refuge', 'RSL_TYPE': 'NWR', 'GlobalID': 'source-uuid'},
        {'OBJECTID': 2, 'ORGNAME': 'Hatchery', 'RSL_TYPE': 'NFH'},
    ]), sources['fws_national_wildlife_refuges'])
    ca = refuges(frame([
        {'OBJECTID': 1, 'TYPE_E': 'National Wildlife Area', 'STATUS': 3, 'ESTYEAR': 1980},
        {'OBJECTID': 2, 'TYPE_E': 'Migratory Bird Sanctuary', 'STATUS': 2, 'ESTYEAR': 1960},
        {'OBJECTID': 3, 'TYPE_E': 'Marine National Wildlife Area', 'STATUS': 2, 'ESTYEAR': 2020},
        {'OBJECTID': 4, 'TYPE_E': 'Provincial Park', 'STATUS': 2, 'ESTYEAR': 1950},
    ]), sources['eccc_wildlife_areas_sanctuaries'])
    assert len(us) == 1 and len(ca) == 3
    assert us.FWS_GlobalID.iloc[0] == 'source-uuid'
    assert ca.ECCC_STATUS.tolist() == ['3', '2', '2']
    assert ca.ECCC_ESTYEAR.tolist() == ['1980', '1960', '2020']
    assert ca.EFFECTIVE_START.isna().all() and ca.EFFECTIVE_END.isna().all()
    assert ca.LEGAL_AUTHORITY.isna().all() and us.LEGAL_AUTHORITY.isna().all()
    assert not set(us.SOURCE_FEATURE_ID) & set(ca.SOURCE_FEATURE_ID)
    assert not ca.MODEL_ELIGIBLE.any()
    with pytest.raises(ValueError, match='Unsupported refuge source'):
        refuges(frame([{'OBJECTID': 1}]), replace(sources['fws_national_wildlife_refuges'], source_id='unknown'))


def test_refuge_duplicate_ids_fail_and_unselected_source_is_empty():
    source = load_governance_config().sources['fws_national_wildlife_refuges']
    with pytest.raises(ValueError, match='OBJECTID'):
        refuges(frame([{'OBJECTID': 1, 'RSL_TYPE': 'NWR'}] * 2), source)
    assert refuges(frame([{'OBJECTID': 1, 'RSL_TYPE': 'NFH'}]), source).empty


def test_refuge_download_requires_explicit_provisioning(tmp_path, monkeypatch):
    from governance.workspace import initialize_workspace
    from governance.protected_areas.wildlife_refuges.download import download
    from governance.shared.acquisition import SourceUnavailableError
    initialize_workspace(tmp_path)
    monkeypatch.setenv('GOVERNANCE_WORKSPACE', str(tmp_path))
    with pytest.raises(SourceUnavailableError, match='budgeted'):
        download()
