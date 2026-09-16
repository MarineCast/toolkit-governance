from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon

from governance.fisheries_management.management_areas.normalize import (
    normalize as normalize_wdfw_recreational_marine_areas,
)
from governance.jurisdiction.federal_waters.normalize import (
    normalize as normalize_noaa_federal_maritime_limits,
)
from governance.jurisdiction.federal_waters.publish import (
    _zone_availability,
)
from governance.jurisdiction.international_boundaries.normalize import (
    normalize as normalize_noaa_international_boundaries,
)
from governance.jurisdiction.state_provincial_waters.normalize import (
    normalize as normalize_boem_submerged_lands_boundary,
)
from governance.protected_areas.marine_protected_areas.normalize import (
    normalize as normalize_marine_protected_areas,
)
from governance.protected_areas.national_marine_sanctuaries.normalize import (
    normalize as normalize_national_marine_sanctuaries,
)
from governance.protected_areas.national_marine_sanctuaries.publish import (
    authority_records as sanctuary_authority_records,
)
from governance.shared.config import load_governance_config


def test_phase1_normalizers_preserve_native_legal_semantics() -> None:
    config = load_governance_config()
    noaa = gpd.GeoDataFrame(
        {
            "OBJECTID": [1, 2],
            "BOUND_ID": ["B1", "B2"],
            "REGION": ["US-Canada", "Pacific Coast"],
            "FEAT_TYPE": ["Maritime Boundary", "Maritime Limit"],
            "LEGAL_AUTH": ["Treaty", "Proclamation"],
            "AOR": ["NOAA/OCS", "NOAA/OCS"],
            "SUPP_INFO": ["https://example.test/treaty", None],
            "PUB_DATE": [1577836800000, "2020-01-01"],
            "APPRV_DATE": [1546300800000, "2019-01-01"],
            "TS": [1, 0],
            "CZ": [0, 0],
            "EEZ": [0, 1],
            "F_EEZ": [0, 0],
        },
        geometry=[
            LineString([(-125.0, 48.0), (-124.0, 49.0)]),
            LineString([(-125.0, 40.0), (-124.0, 41.0)]),
        ],
        crs="EPSG:4326",
    )
    noaa_boundary_source = config.sources["noaa_us_maritime_limits"]
    boundaries = normalize_noaa_international_boundaries(noaa, noaa_boundary_source)
    territorial = normalize_noaa_federal_maritime_limits(
        noaa.iloc[[0]].copy(), config.sources["noaa_us_territorial_sea_dynamic"]
    )
    eez = normalize_noaa_federal_maritime_limits(
        noaa.iloc[[1]].copy(), config.sources["noaa_us_eez_dynamic"]
    )
    limits = gpd.GeoDataFrame(
        pd.concat([territorial, eez], ignore_index=True), geometry="geometry", crs=noaa.crs
    )
    assert boundaries["BOUNDARY_ID"].tolist() == ["B1"]
    assert set(limits["ZONE_TYPE"]) == {
        "territorial_sea",
        "exclusive_economic_zone",
    }
    assert set(limits["FEATURE_TYPE"]) == {
        "territorial_sea_limit",
        "exclusive_economic_zone_limit",
    }
    assert set(limits["COUNTRY_CODE"]) == {"USA"}
    assert set(limits["ZONE_LIMIT_NM"]) == {12, 200}
    assert set(limits["PUBLICATION_DATE"]) == {"2020-01-01"}
    assert set(limits["APPROVAL_DATE"]) == {"2019-01-01"}
    assert limits["SOURCE_FEATURE_ID"].is_unique
    assert not limits["MODEL_ELIGIBLE"].any()
    assert "IS_FEDERAL_WATER" not in limits.columns
    assert not any(column.startswith("H3_") for column in limits.columns)

    availability = _zone_availability()["countries"]
    assert availability["USA"]["zones"]["internal_waters"]["status"] == ("unavailable_geometry")
    assert availability["CAN"]["zones"]["territorial_sea"]["status"] == (
        "unavailable_machine_readable_authoritative_geometry"
    )

    boem = gpd.GeoDataFrame(
        {
            "OBJECTID": [10],
            "BDRY_NAME_TEXT": ["Submerged Lands Act Boundary"],
            "BDRY_APRV_DATE": ["2014-12-15"],
            "BLOCK_NUMBER": [None],
        },
        geometry=[LineString([(-125.0, 40.0), (-124.0, 41.0)])],
        crs="EPSG:4326",
    )
    state = normalize_boem_submerged_lands_boundary(
        boem, config.sources["boem_submerged_lands_boundary"]
    )
    assert state["FEATURE_TYPE"].tolist() == ["state_seaward_boundary_line"]
    assert state["PROVINCE_WATER_EQUIVALENT"].tolist() == ["unavailable"]

    wdfw = gpd.GeoDataFrame(
        {
            "OBJECTID": [20],
            "AreaName": ["7"],
            "AreaTitle": ["San Juan Islands"],
            "WAC": ["220-56-185"],
        },
        geometry=[Polygon([(-123.5, 48.2), (-122.5, 48.2), (-122.5, 49.0), (-123.5, 48.2)])],
        crs="EPSG:4326",
    )
    areas = normalize_wdfw_recreational_marine_areas(
        wdfw, config.sources["wdfw_recreational_marine_areas"]
    )
    assert areas["AREA_CODE"].tolist() == ["7"]
    assert areas["MANAGEMENT_SYSTEM"].tolist() == ["WDFW recreational marine area"]


def test_international_sources_keep_scale_accuracy_and_support_non_authority() -> None:
    config = load_governance_config()
    ibc = gpd.GeoDataFrame(
        {
            "SectionNum": [26],
            "SectionEng": ["Straits of Georgia and Juan De Fuca"],
            "MaxScale": ["1:200,000"],
        },
        geometry=[LineString([(-123.5, 48.2), (-123.0, 48.8)])],
        crs="EPSG:4269",
    )
    ibc_records = normalize_noaa_international_boundaries(
        ibc,
        config.sources["international_boundary_commission_v1_3"],
    )
    assert ibc_records["SOURCE_SCALE_DENOMINATOR"].tolist() == [200_000]
    assert ibc_records["SOURCE_LEGAL_STATUS"].tolist() == ["mapping_only_not_boundary_definition"]
    assert "no coordinate snapping" in ibc_records["BOUNDARY_QC_REASON"].iloc[0]

    cgb = gpd.GeoDataFrame(
        {
            "UUID": [1125],
            "TYPE_E": ["INTERN"],
            "STATUS": ["LEGIS_SUR"],
            "SRC_AGENCY": ["IBC"],
            "SRC_DESC": ["International boundary surveyed by IBC"],
            "ACCUR": [10],
            "P_UPD_DATE": ["2007-05-17"],
        },
        geometry=[LineString([(-123.5, 48.2), (-123.0, 48.8)])],
        crs="EPSG:4269",
    )
    cgb_records = normalize_noaa_international_boundaries(
        cgb,
        config.sources["nrcan_canadian_geopolitical_boundaries_lines"],
    )
    assert cgb_records["SOURCE_POSITIONAL_ACCURACY_M"].tolist() == [10.0]
    assert cgb_records["CANADIAN_SOURCE_AGENCY"].tolist() == ["IBC"]
    assert cgb_records["SOURCE_LEGAL_STATUS"].tolist() == ["archived_cartographic_reference"]

    cgb_eez = gpd.GeoDataFrame(
        {
            "UUID": [855],
            "TYPE_E": ["EEZ_200"],
            "STATUS": ["LEGIS_DESC"],
            "SRC_AGENCY": ["DFO"],
            "SRC_DESC": ["200 nautical mile EEZ limit"],
            "ACCUR": [100],
            "P_UPD_DATE": ["2007-05-17"],
        },
        geometry=[LineString([(-134.0, 52.0), (-133.0, 53.0)])],
        crs="EPSG:4269",
    )
    canadian_zone = normalize_noaa_federal_maritime_limits(
        cgb_eez,
        config.sources["nrcan_canadian_geopolitical_boundaries_lines"],
    )
    assert canadian_zone["COUNTRY_CODE"].tolist() == ["CAN"]
    assert canadian_zone["ZONE_TYPE"].tolist() == ["exclusive_economic_zone"]
    assert canadian_zone["GEOMETRY_ROLE"].tolist() == ["eez_200nm_outer_limit"]
    assert canadian_zone["SOURCE_POSITIONAL_ACCURACY_M"].tolist() == [100.0]

    support = gpd.GeoDataFrame(
        {"NAME": ["CANADA"], "TYPE": ["TERRITORIAL"]},
        geometry=[
            Polygon(
                [
                    (-124.0, 48.0),
                    (-123.0, 48.0),
                    (-123.0, 49.0),
                    (-124.0, 48.0),
                ]
            )
        ],
        crs="EPSG:4326",
    )
    support_records = normalize_noaa_international_boundaries(
        support,
        config.sources["seascape_territorial_water_support"],
    )
    assert support_records["COUNTRY_CODE"].tolist() == ["CAN"]
    assert support_records["LEGAL_BINDING_STATUS"].tolist() == ["derived_reference_geometry"]
    assert support_records["SOURCE_ROLE"].tolist() == ["spatial_support_only"]
    assert support_records["MODEL_ELIGIBLE"].tolist() == [False]


def test_mpa_sources_preserve_inventory_regulation_and_proposal_semantics() -> None:
    config = load_governance_config()
    noaa = gpd.GeoDataFrame(
        {
            "site_id": ["CA001"],
            "site_name": ["Fixture State Marine Reserve"],
            "date_gis_u": [1672531200000],
            "mgmt_agen": ["California Department of Fish and Wildlife"],
            "url": ["https://example.test/authority"],
            "gov_level": ["State"],
            "estab_yr": ["2012"],
            "pri_con_fo": ["Natural Heritage"],
            "cons_focus": ["Biodiversity"],
            "prot_focus": ["Ecosystem"],
            "prot_lvl": ["No Take"],
            "ns_full": ["Member"],
            "mgmt_plan": ["Yes"],
            "permanence": ["Permanent"],
            "constancy": ["Year-round"],
            "fish_rstr": ["Fishing restricted"],
            "vessel": ["Transit allowed"],
            "anchor": ["Anchoring restricted"],
            "area_km_ma": [12.5],
        },
        geometry=[Polygon([(-123.0, 37.0), (-122.5, 37.0), (-122.5, 37.5), (-123.0, 37.0)])],
        crs="EPSG:4326",
    )
    us = normalize_marine_protected_areas(noaa, config.sources["noaa_mpa_inventory_states"])
    assert us["DESIGNATION_ID"].tolist() == ["USA:NOAA_MPA:CA001"]
    assert us["EFFECTIVE_START"].tolist() == ["2012-01-01"]
    assert us["SOURCE_VINTAGE"].tolist() == ["2023-01-01"]
    assert us["MAP_GROUP"].tolist() == ["us_state_tribal_local_reference"]
    assert us["GOVERNING_RULE_STATUS"].tolist() == [
        "program_framework_only_site_rule_not_in_inventory"
    ]
    assert us["IUCN_REPORTING_CLASS"].isna().all()
    assert not any("SCORE" in column for column in us.columns)

    dfo = gpd.GeoDataFrame(
        {
            "OBJECTID": [10],
            "NAME_E": ["Fixture Oceans Act MPA"],
            "ZONE_E": ["Core Zone"],
            "URL_E": ["https://example.test/dfo-mpa"],
            "REGULATION": ["Fixture Marine Protected Area Regulations"],
            "KM2": [44.0],
        },
        geometry=[Polygon([(-128.0, 50.0), (-127.0, 50.0), (-127.0, 51.0), (-128.0, 50.0)])],
        crs="EPSG:4326",
    )
    active = normalize_marine_protected_areas(
        dfo, config.sources["dfo_oceans_act_marine_protected_areas"]
    )
    assert active["DESIGNATION_STATUS"].tolist() == ["active_designated"]
    assert active["GOVERNING_RULE_STATUS"].tolist() == ["source_regulation_citation_present"]
    assert active["SOURCE_ZONE_NAME"].tolist() == ["Core Zone"]

    aoi = gpd.GeoDataFrame(
        {
            "OBJECTID": [11],
            "NAME_E": ["Fixture Area of Interest"],
            "URL_E": ["https://example.test/dfo-aoi"],
        },
        geometry=[Point(-123.0, 48.0)],
        crs="EPSG:4326",
    )
    proposed = normalize_marine_protected_areas(
        aoi, config.sources["dfo_oceans_act_areas_of_interest"]
    )
    assert proposed["DESIGNATION_STATUS"].tolist() == ["area_of_interest"]
    assert proposed["LEGAL_BINDING_STATUS"].tolist() == ["proposal_reference_geometry"]
    assert proposed["SOURCE_GEOMETRY_STATUS"].tolist() == [
        "dfo_area_of_interest_point_not_proposed_boundary"
    ]


def test_sanctuary_normalizer_separates_gis_evidence_from_cfr_authority() -> None:
    config = load_governance_config()
    source = config.sources["noaa_onms_chumash_heritage_boundary"]
    source_frame = gpd.GeoDataFrame(
        {
            "Name": ["Chumash Heritage National Marine Sanctuary"],
            "Area_sqmi": [4543.14292],
        },
        geometry=[
            Polygon(
                [
                    (-121.70500178238098, 33.823772308673334),
                    (-119.93332992118029, 33.823772308673334),
                    (-119.93332992118029, 35.192789811301495),
                    (-121.70500178238098, 33.823772308673334),
                ]
            )
        ],
        crs="EPSG:4269",
    )
    sanctuaries = normalize_national_marine_sanctuaries(source_frame, source)

    assert sanctuaries["SANCTUARY_ID"].tolist() == ["CHNMS"]
    assert sanctuaries["EFFECTIVE_START"].tolist() == ["2024-11-30"]
    assert sanctuaries["CFR_SUBPART"].tolist() == ["V"]
    assert sanctuaries["DESIGNATION_FEDERAL_REGISTER"].tolist() == ["89 FR 83554"]
    assert sanctuaries["LEGAL_BOUNDARY_STATUS"].tolist() == [
        "current_cfr_text_and_coordinates_control"
    ]
    assert sanctuaries["SOURCE_GEOMETRY_STATUS"].tolist() == [
        "onms_gis_boundary_representation_not_for_legal_use"
    ]
    assert sanctuaries["MODEL_ELIGIBLE"].tolist() == [False]
    assert not any(column.startswith("H3_") for column in sanctuaries.columns)

    records = sanctuary_authority_records(sanctuaries)
    assert len(records) == 1
    assert records[0]["SANCTUARY_ID"] == "CHNMS"
    assert records[0]["LEGAL_SOURCE_URL"].endswith("/subpart-V")
