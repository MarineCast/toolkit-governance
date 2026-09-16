"""Normalize NOAA discovery-inventory and DFO Oceans Act MPA geometry."""

from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd

from governance.shared.config import GovernanceSource
from governance.shared.normalization import (
    base_record,
    clean,
    date_value,
    records_frame,
)

NORMALIZATION_PROFILE = "noaa_dfo_marine_protected_areas"

NOAA_PROGRAMS = {
    "noaa_mpa_inventory_2023": "NOAA Marine Protected Areas Inventory",
    "noaa_mpa_inventory_states": "State, Tribal, territorial, and local MPAs",
    "noaa_mpa_inventory_nerrs": "National Estuarine Research Reserve System",
    "noaa_mpa_inventory_boem": "Bureau of Ocean Energy Management MPAs",
    "noaa_mpa_inventory_marine_national_monuments": "Marine national monuments",
    "noaa_mpa_inventory_national_marine_sanctuaries": "National marine sanctuaries",
    "noaa_mpa_inventory_national_park_service": "National Park Service marine units",
    "noaa_mpa_inventory_national_wildlife_refuge_system": (
        "National Wildlife Refuge System marine units"
    ),
    "noaa_mpa_inventory_national_forest_service": "National Forest Service marine units",
}


def _slug(value: str | None, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or fallback).casefold()).strip("-")
    return normalized or fallback


def _number(value: object) -> float | None:
    parsed = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(parsed) else float(parsed)


def _value(row: pd.Series, *names: str) -> object:
    lookup = {str(column).casefold(): column for column in row.index}
    for name in names:
        resolved = lookup.get(name.casefold())
        if resolved is not None:
            return row.get(resolved)
    return None


def _source_date(value: object) -> str | None:
    numeric = _number(value)
    if numeric is not None and abs(numeric) >= 10_000_000_000:
        parsed = pd.to_datetime(numeric, unit="ms", utc=True, errors="coerce")
        return None if pd.isna(parsed) else parsed.date().isoformat()
    return date_value(value)


def _established_date(value: object) -> str | None:
    text = clean(value)
    if text is None:
        return None
    match = re.search(r"\b(18|19|20)\d{2}\b", text)
    return f"{match.group(0)}-01-01" if match else None


def _metadata_defaults() -> dict[str, object]:
    return {
        "SOURCE_RECORD_ID": None,
        "DESIGNATION_ID": None,
        "AUTHORITY_ID": None,
        "COUNTRY_CODE": None,
        "DESIGNATION_STATUS": None,
        "EFFECTIVE_STATUS": None,
        "MPA_PROGRAM": None,
        "MAP_GROUP": None,
        "MANAGEMENT_AUTHORITY": None,
        "AUTHORITY_SOURCE_URL": None,
        "GOVERNING_RULE_CITATION": None,
        "GOVERNING_RULE_STATUS": None,
        "INVENTORY_GOVERNMENT_LEVEL": None,
        "SOURCE_SUBDIVISION_CODE": None,
        "SOURCE_DESIGNATION_TYPE": None,
        "SOURCE_ZONE_NAME": None,
        "PROTECTION_PURPOSE": None,
        "PROTECTION_PURPOSE_STATUS": None,
        "PRIMARY_CONSERVATION_FOCUS": None,
        "CONSERVATION_FOCUS": None,
        "PROTECTION_FOCUS": None,
        "PROTECTION_LEVEL_REFERENCE": None,
        "NATIONAL_SYSTEM_STATUS": None,
        "MANAGEMENT_PLAN_STATUS": None,
        "PERMANENCE": None,
        "CONSTANCY": None,
        "FISHING_RESTRICTIONS_REFERENCE": None,
        "VESSEL_RESTRICTIONS_REFERENCE": None,
        "ANCHORING_RESTRICTIONS_REFERENCE": None,
        "ALLOWED_ACTIVITIES": None,
        "PROHIBITED_ACTIVITIES": None,
        "ACTIVITY_METADATA_STATUS": None,
        "IUCN_REPORTING_CLASS": None,
        "IUCN_CLASS_STATUS": "unavailable_not_sourced",
        "SOURCE_AREA_KM2": None,
        "SOURCE_GEOMETRY_STATUS": None,
        "MPA_QC_REASON": None,
    }


def _noaa(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    program = NOAA_PROGRAMS[source.source_id]
    records = []
    for index, row in frame.iterrows():
        site_id = clean(_value(row, "site_id")) or str(clean(_value(row, "objectid")) or index)
        site_name = clean(_value(row, "site_name")) or clean(_value(row, "site_label")) or site_id
        management_authority = clean(_value(row, "mgmt_agen")) or source.provider
        authority_url = clean(_value(row, "url")) or source.url
        source_vintage = _source_date(_value(row, "date_gis_u")) or source.source_as_of
        government_level = clean(_value(row, "gov_level"))
        iucn_class = clean(_value(row, "IUCNcat"))
        map_group = (
            "us_federal_program_reference"
            if government_level and "federal" in government_level.casefold()
            else "us_state_tribal_local_reference"
        )
        record = base_record(
            source,
            source_feature_id=f"{source.source_id}:{site_id}",
            governance_feature_id=f"marine_protected_area:usa:{site_id}",
            feature_name=site_name,
            feature_type="marine_protected_area_inventory_polygon",
            authority=management_authority,
            jurisdiction="United States",
            legal_authority=source.legal_citation,
            legal_source_url=authority_url,
            source_coverage_status="partial_noaa_discovery_inventory",
        )
        record.update(_metadata_defaults())
        record.update(
            EFFECTIVE_START=_established_date(_value(row, "estab_yr")),
            SOURCE_VINTAGE=source_vintage,
            SOURCE_RECORD_ID=site_id,
            DESIGNATION_ID=f"USA:NOAA_MPA:{site_id}",
            AUTHORITY_ID=f"USA:AGENCY:{_slug(management_authority, 'unknown')}",
            COUNTRY_CODE="USA",
            DESIGNATION_STATUS="active_reference_inventory",
            EFFECTIVE_STATUS="inventory_lists_existing_mpa_not_legally_reverified",
            MPA_PROGRAM=program,
            MAP_GROUP=map_group,
            MANAGEMENT_AUTHORITY=management_authority,
            AUTHORITY_SOURCE_URL=authority_url,
            GOVERNING_RULE_CITATION=source.legal_citation,
            GOVERNING_RULE_STATUS="program_framework_only_site_rule_not_in_inventory",
            INVENTORY_GOVERNMENT_LEVEL=government_level,
            SOURCE_SUBDIVISION_CODE=clean(_value(row, "State")),
            SOURCE_DESIGNATION_TYPE=clean(_value(row, "Design")),
            PROTECTION_PURPOSE=clean(_value(row, "pri_con_fo")),
            PROTECTION_PURPOSE_STATUS="noaa_inventory_reference_classification",
            PRIMARY_CONSERVATION_FOCUS=clean(_value(row, "pri_con_fo")),
            CONSERVATION_FOCUS=clean(_value(row, "cons_focus")),
            PROTECTION_FOCUS=clean(_value(row, "prot_focus")),
            PROTECTION_LEVEL_REFERENCE=clean(_value(row, "prot_lvl")),
            NATIONAL_SYSTEM_STATUS=clean(_value(row, "ns_full")),
            MANAGEMENT_PLAN_STATUS=clean(_value(row, "mgmt_plan")),
            PERMANENCE=clean(_value(row, "permanence")),
            CONSTANCY=clean(_value(row, "constancy")),
            FISHING_RESTRICTIONS_REFERENCE=clean(_value(row, "fish_rstr")),
            VESSEL_RESTRICTIONS_REFERENCE=clean(_value(row, "vessel")),
            ANCHORING_RESTRICTIONS_REFERENCE=clean(_value(row, "anchor")),
            ACTIVITY_METADATA_STATUS=(
                "inventory_restriction_classes_retained_not_interpreted_as_legal_rules"
            ),
            IUCN_REPORTING_CLASS=iucn_class,
            IUCN_CLASS_STATUS=(
                "sourced_noaa_inventory_reference"
                if iucn_class
                else "inventory_scope_uses_iucn_definition_but_category_not_sourced"
            ),
            SOURCE_AREA_KM2=_number(_value(row, "AreaMar", "area_km_ma"))
            or _number(_value(row, "AreaKm", "area_km_to")),
            SOURCE_GEOMETRY_STATUS="inventory_reference_polygon_not_controlling_legal_source",
            MPA_QC_REASON=(
                "NOAA MPA Inventory is retained as discovery/reference geometry. The source "
                "management agency and program framework are retained, but the inventory "
                "does not provide a verified site-specific governing-rule citation."
            ),
            geometry=row.geometry,
        )
        record["QC_REASON"] = record["MPA_QC_REASON"]
        records.append(record)
    return records_frame(records, frame.crs)


def _dfo_active(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    records = []
    for index, row in frame.iterrows():
        object_id = str(clean(row.get("OBJECTID")) or index)
        name = clean(row.get("NAME_E")) or clean(row.get("NAME_F")) or object_id
        regulation = clean(row.get("REGULATION"))
        authority_url = clean(row.get("URL_E")) or source.url
        designation_slug = _slug(name, object_id)
        record = base_record(
            source,
            source_feature_id=f"{source.source_id}:{object_id}",
            governance_feature_id=f"marine_protected_area:can:{designation_slug}:{object_id}",
            feature_name=name,
            feature_type="oceans_act_marine_protected_area_zone_polygon",
            authority="Fisheries and Oceans Canada",
            jurisdiction="Canada",
            legal_authority=regulation or source.legal_citation,
            legal_source_url=regulation or authority_url,
            source_coverage_status="partial_dfo_oceans_act_reference",
        )
        record.update(_metadata_defaults())
        record.update(
            SOURCE_RECORD_ID=object_id,
            DESIGNATION_ID=f"CAN:DFO_OCEANS_ACT:{designation_slug}",
            AUTHORITY_ID="CAN:DFO",
            COUNTRY_CODE="CAN",
            DESIGNATION_STATUS="active_designated",
            EFFECTIVE_STATUS="designated_effective_date_not_in_spatial_source",
            MPA_PROGRAM="Oceans Act Marine Protected Area",
            MAP_GROUP="canada_active_oceans_act",
            MANAGEMENT_AUTHORITY="Fisheries and Oceans Canada",
            AUTHORITY_SOURCE_URL=authority_url,
            GOVERNING_RULE_CITATION=regulation,
            GOVERNING_RULE_STATUS=(
                "source_regulation_citation_present"
                if regulation
                else "regulation_citation_missing_from_source_feature"
            ),
            SOURCE_ZONE_NAME=clean(row.get("ZONE_E")),
            PROTECTION_PURPOSE_STATUS="not_feature_specific_in_spatial_source",
            ACTIVITY_METADATA_STATUS="consult_feature_regulation_not_encoded_in_spatial_source",
            IUCN_CLASS_STATUS="not_sourced_in_dfo_spatial_layer",
            SOURCE_AREA_KM2=_number(row.get("KM2")),
            SOURCE_GEOMETRY_STATUS="dfo_visual_reference_polygon_regulation_coordinates_control",
            MPA_QC_REASON=(
                "DFO states that the polygon is a visual reference and not legally "
                "authoritative; the retained regulation and its official coordinates control."
            ),
            geometry=row.geometry,
        )
        record["QC_REASON"] = record["MPA_QC_REASON"]
        records.append(record)
    return records_frame(records, frame.crs)


def _dfo_aoi(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    records = []
    for index, row in frame.iterrows():
        object_id = str(clean(row.get("OBJECTID")) or index)
        name = clean(row.get("NAME_E")) or clean(row.get("NAME_F")) or object_id
        authority_url = clean(row.get("URL_E")) or source.url
        designation_slug = _slug(name, object_id)
        record = base_record(
            source,
            source_feature_id=f"{source.source_id}:{object_id}",
            governance_feature_id=f"marine_protected_area_aoi:can:{designation_slug}",
            feature_name=name,
            feature_type="oceans_act_area_of_interest_point",
            authority="Fisheries and Oceans Canada",
            jurisdiction="Canada",
            legal_authority=source.legal_citation,
            legal_source_url=authority_url,
            source_coverage_status="partial_dfo_area_of_interest_points",
        )
        record.update(_metadata_defaults())
        record.update(
            LEGAL_BINDING_STATUS="proposal_reference_geometry",
            SOURCE_RECORD_ID=object_id,
            DESIGNATION_ID=f"CAN:DFO_AOI:{designation_slug}",
            AUTHORITY_ID="CAN:DFO",
            COUNTRY_CODE="CAN",
            DESIGNATION_STATUS="area_of_interest",
            EFFECTIVE_STATUS="proposed_or_under_assessment_not_designated",
            MPA_PROGRAM="Oceans Act Marine Protected Area establishment process",
            MAP_GROUP="canada_area_of_interest",
            MANAGEMENT_AUTHORITY="Fisheries and Oceans Canada",
            AUTHORITY_SOURCE_URL=authority_url,
            GOVERNING_RULE_STATUS="not_applicable_not_designated",
            PROTECTION_PURPOSE_STATUS="not_sourced_in_area_of_interest_point_layer",
            ACTIVITY_METADATA_STATUS="not_applicable_not_designated",
            IUCN_CLASS_STATUS="not_applicable_not_designated",
            SOURCE_GEOMETRY_STATUS="dfo_area_of_interest_point_not_proposed_boundary",
            MPA_QC_REASON=(
                "The source supplies an Area of Interest point, not a proposed or legal "
                "boundary. It is kept separate from active MPA polygons and has no implied area."
            ),
            geometry=row.geometry,
        )
        record["QC_REASON"] = record["MPA_QC_REASON"]
        records.append(record)
    return records_frame(records, frame.crs)


def normalize(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    """Dispatch source semantics without treating inventories as legal authority."""

    if source.source_id in NOAA_PROGRAMS:
        return _noaa(frame, source)
    if source.source_id == "dfo_oceans_act_marine_protected_areas":
        return _dfo_active(frame, source)
    if source.source_id == "dfo_oceans_act_areas_of_interest":
        return _dfo_aoi(frame, source)
    raise ValueError(f"Unsupported marine-protected-area source: {source.source_id}")
