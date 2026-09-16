"""Normalize source-native U.S. and Canadian maritime-zone limit geometry."""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from governance.shared.config import GovernanceSource
from governance.shared.normalization import (
    base_record,
    clean,
    column,
    date_value,
    records_frame,
)

NORMALIZATION_PROFILE = "reconciled_us_canada_federal_maritime_zone_limits"


@dataclass(frozen=True)
class NoaaZone:
    zone_type: str
    feature_type: str
    limit_nm: int
    label: str


NOAA_ZONES = {
    "noaa_us_territorial_sea_dynamic": NoaaZone(
        "territorial_sea", "territorial_sea_limit", 12, "U.S. territorial sea"
    ),
    "noaa_us_contiguous_zone_dynamic": NoaaZone(
        "contiguous_zone", "contiguous_zone_limit", 24, "U.S. contiguous zone"
    ),
    "noaa_us_eez_dynamic": NoaaZone(
        "exclusive_economic_zone", "exclusive_economic_zone_limit", 200, "U.S. EEZ"
    ),
}

NOAA_RULE_ROLES = {
    1: "international_land_boundary",
    2: "eez_outer_limit",
    3: "territorial_sea_outer_limit",
    4: "international_maritime_boundary_and_eez",
    5: "international_maritime_boundary",
    6: "unused_or_unclassified",
    7: "contiguous_zone_outer_limit",
    8: "eastern_special_area",
}

CANADA_OCEANS_ACT_URL = "https://laws-lois.justice.gc.ca/eng/acts/O-2.4/"


def _number(value: object) -> float | None:
    parsed = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(parsed) else float(parsed)


def _integer(value: object) -> int | None:
    parsed = _number(value)
    return None if parsed is None else int(parsed)


def _source_date(value: object) -> str | None:
    """Handle ArcGIS epoch-millisecond dates and ordinary source dates."""

    numeric = _number(value)
    if numeric is not None and abs(numeric) >= 10_000_000_000:
        parsed = pd.to_datetime(numeric, unit="ms", utc=True, errors="coerce")
        return None if pd.isna(parsed) else parsed.date().isoformat()
    return date_value(value)


def _noaa(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    zone = NOAA_ZONES[source.source_id]
    records = []
    for index, row in frame.iterrows():
        boundary_id = clean(row.get("BOUND_ID")) or str(clean(row.get("OBJECTID")) or index)
        rule_id = _integer(row.get("RULEID"))
        rule_label = clean(row.get("RULE")) or clean(row.get("RULE_DESC"))
        region = clean(row.get("REGION"))
        publication_date = _source_date(row.get("PUB_DATE"))
        source_feature_id = f"{source.source_id}:{boundary_id}"
        geometry_role = NOAA_RULE_ROLES.get(rule_id, "source_value_unknown")
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"us_maritime_zone:{zone.zone_type}:{boundary_id}",
            feature_name=f"{region or boundary_id} — {zone.label} limit",
            feature_type=zone.feature_type,
            authority=clean(row.get("AOR")) or source.provider,
            jurisdiction="United States",
            legal_authority=clean(row.get("LEGAL_AUTH")) or source.legal_citation,
            legal_source_url=clean(row.get("SUPP_INFO")) or source.url,
            source_coverage_status="partial_current_dynamic_reference",
        )
        record.update(
            SOURCE_VINTAGE=publication_date or source.source_as_of,
            COUNTRY_CODE="USA",
            ZONE_TYPE=zone.zone_type,
            ZONE_LIMIT_NM=zone.limit_nm,
            GEOMETRY_ROLE=geometry_role,
            SOURCE_LAYER_NAME=zone.label,
            SOURCE_RULE_ID=rule_id,
            SOURCE_RULE_LABEL=rule_label,
            SOURCE_RECORD_ID=boundary_id,
            REGION=region,
            PUBLICATION_DATE=publication_date,
            APPROVAL_DATE=_source_date(row.get("APPRV_DATE")),
            SOURCE_POSITIONAL_ACCURACY_M=_number(row.get("POS_ACC")),
            SOURCE_AGENCY=clean(row.get("AOR")) or source.provider,
            SOURCE_STATUS=clean(row.get("STATUS")),
            ZONE_QC_REASON=(
                "Source-native NOAA line from the separately published dynamic zone layer; "
                "it is not a polygon and was not buffered, nested, dissolved, or converted "
                "to IS_FEDERAL_WATER. Controlling charts and legal instruments prevail."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)


def _cgb_eez(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    type_values = column(frame, "TYPE_E").fillna("").astype(str).str.upper()
    selected = frame.loc[type_values.str.startswith("EEZ")].copy()
    records = []
    for index, row in selected.iterrows():
        boundary_id = clean(row.get("UUID")) or str(index)
        source_type = (clean(row.get("TYPE_E")) or "EEZ").upper()
        source_agency = clean(row.get("SRC_AGENCY"))
        source_status = clean(row.get("STATUS"))
        source_description = clean(row.get("SRC_DESC"))
        publication_date = date_value(row.get("P_UPD_DATE"))
        geometry_role = (
            "eez_200nm_outer_limit"
            if source_type == "EEZ_200"
            else "eez_bilateral_or_shared_boundary"
        )
        source_feature_id = f"{source.source_id}:{boundary_id}:eez"
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"can_maritime_zone:exclusive_economic_zone:{boundary_id}",
            feature_name=f"Canadian EEZ reference limit {boundary_id}",
            feature_type="exclusive_economic_zone_limit",
            authority=source_agency or source.provider,
            jurisdiction="Canada",
            legal_authority=(
                f"Canada Oceans Act; {source_description}"
                if source_description
                else "Canada Oceans Act"
            ),
            legal_source_url=CANADA_OCEANS_ACT_URL,
            source_coverage_status="partial_archived_government_reference",
        )
        record.update(
            SOURCE_VINTAGE=publication_date or source.source_as_of,
            COUNTRY_CODE="CAN",
            ZONE_TYPE="exclusive_economic_zone",
            ZONE_LIMIT_NM=200,
            GEOMETRY_ROLE=geometry_role,
            SOURCE_LAYER_NAME="GeoBase Canadian Geopolitical Boundaries Level 1",
            SOURCE_RULE_ID=None,
            SOURCE_RULE_LABEL=source_type,
            SOURCE_RECORD_ID=boundary_id,
            REGION="Canada",
            PUBLICATION_DATE=publication_date,
            APPROVAL_DATE=None,
            SOURCE_POSITIONAL_ACCURACY_M=_number(row.get("ACCUR")),
            SOURCE_AGENCY=source_agency or source.provider,
            SOURCE_STATUS=source_status,
            ZONE_QC_REASON=(
                "Archived Canadian government cartographic EEZ reference with DFO source "
                "lineage where present; not a controlling legal boundary. Internal waters, "
                "territorial-sea, and contiguous-zone geometry are unavailable and were not "
                "inferred from this line."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)


def normalize(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    """Dispatch zone-layer semantics without manufacturing jurisdiction polygons."""

    if source.source_id in NOAA_ZONES:
        return _noaa(frame, source)
    if source.source_id == "nrcan_canadian_geopolitical_boundaries_lines":
        return _cgb_eez(frame, source)
    raise ValueError(f"Unsupported federal-waters source: {source.source_id}")
