"""Normalize NOAA sanctuary polygons without promoting GIS files to legal authority."""

from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
import pandas as pd

from governance.shared.config import GovernanceSource
from governance.shared.normalization import base_record, clean, records_frame

NORMALIZATION_PROFILE = "noaa_onms_west_coast_sanctuaries"
SQUARE_METERS_PER_SQUARE_MILE = 2_589_988.110336

SANCTUARY_METADATA: dict[str, dict[str, Any]] = {
    "noaa_onms_channel_islands_boundary": {
        "sanctuary_id": "CINMS",
        "name": "Channel Islands National Marine Sanctuary",
        "subdivision": "US-CA",
        "effective_start": "1980-09-22",
        "cfr_subpart": "G",
        "boundary_section": "15 CFR 922.70 and appendix A to subpart G",
        "legal_url": "https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-G",
        "designation_federal_register": "45 FR 65198",
        "boundary_amendment_summary": "Designated in 1980; current boundary description and coordinates are codified in 15 CFR part 922 subpart G.",
        "cfr_approx_area_sqmi": 1470.0,
    },
    "noaa_onms_chumash_heritage_boundary": {
        "sanctuary_id": "CHNMS",
        "name": "Chumash Heritage National Marine Sanctuary",
        "subdivision": "US-CA",
        "effective_start": "2024-11-30",
        "cfr_subpart": "V",
        "boundary_section": "15 CFR 922.230 and appendix A to subpart V",
        "legal_url": "https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-V",
        "designation_federal_register": "89 FR 83554",
        "boundary_amendment_summary": "Designated in 2024; this is the first effective sanctuary boundary edition.",
        "cfr_approx_area_sqmi": 4543.0,
    },
    "noaa_onms_cordell_bank_boundary": {
        "sanctuary_id": "CBNMS",
        "name": "Cordell Bank National Marine Sanctuary",
        "subdivision": "US-CA",
        "effective_start": "1989-05-24",
        "cfr_subpart": "K",
        "boundary_section": "15 CFR 922.110 and appendix A to subpart K",
        "legal_url": "https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-K",
        "designation_federal_register": "54 FR 22417",
        "boundary_amendment_summary": "Designated in 1989 and expanded north and west effective June 9, 2015; the archive represents the expanded boundary.",
        "cfr_approx_area_sqmi": 1286.0,
    },
    "noaa_onms_greater_farallones_boundary": {
        "sanctuary_id": "GFNMS",
        "name": "Greater Farallones National Marine Sanctuary",
        "subdivision": "US-CA",
        "effective_start": "1981-01-16",
        "cfr_subpart": "H",
        "boundary_section": "15 CFR 922.80 and appendix A to subpart H",
        "legal_url": "https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-H",
        "designation_federal_register": "46 FR 7936",
        "boundary_amendment_summary": "Designated in 1981 as Point Reyes-Farallon Islands, expanded north and west in 2015, and renamed Greater Farallones; the archive represents the expanded boundary.",
        "cfr_approx_area_sqmi": 3295.0,
    },
    "noaa_onms_monterey_bay_boundary": {
        "sanctuary_id": "MBNMS",
        "name": "Monterey Bay National Marine Sanctuary",
        "subdivision": "US-CA",
        "effective_start": "1992-09-18",
        "cfr_subpart": "M",
        "boundary_section": "15 CFR 922.130 and appendix A to subpart M",
        "legal_url": "https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-M",
        "designation_federal_register": "57 FR 43310",
        "boundary_amendment_summary": "Designated in 1992; Davidson Seamount was added in 2008 and the archive represents the two-area sanctuary boundary.",
        "cfr_approx_area_sqmi": 6093.0,
    },
    "noaa_onms_olympic_coast_boundary": {
        "sanctuary_id": "OCNMS",
        "name": "Olympic Coast National Marine Sanctuary",
        "subdivision": "US-WA",
        "effective_start": "1994-07-22",
        "cfr_subpart": "O",
        "boundary_section": "15 CFR 922.150 and appendix A to subpart O",
        "legal_url": "https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-O",
        "designation_federal_register": "59 FR 24586",
        "boundary_amendment_summary": "Designated in 1994; boundary-coordinate corrections were published in 1995 and current coordinates are codified in subpart O.",
        "cfr_approx_area_sqmi": 3188.0,
    },
}


def _value(row: pd.Series, *names: str) -> Any:
    lookup = {str(column).casefold(): column for column in row.index}
    for name in names:
        column = lookup.get(name.casefold())
        if column is not None:
            return row.get(column)
    return None


def _float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _system_learned_at(source: GovernanceSource) -> str | None:
    """Use the archived acquisition time so cached rebuilds remain deterministic."""

    if source.snapshot_path is None:
        return None
    metadata_path = source.snapshot_path.with_suffix(f"{source.snapshot_path.suffix}.metadata.json")
    if not metadata_path.is_file():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return clean(metadata.get("retrieved_at_utc"))


def normalize(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    """Retain source polygon parts while attaching current controlling CFR references."""

    metadata = SANCTUARY_METADATA.get(source.source_id)
    if metadata is None:
        raise ValueError(f"Unsupported NOAA sanctuary source: {source.source_id}")
    if frame.empty:
        return records_frame([], frame.crs)

    geometry_area_sqmi = float(
        frame.to_crs("EPSG:6933").geometry.area.sum() / SQUARE_METERS_PER_SQUARE_MILE
    )
    cfr_area_sqmi = float(metadata["cfr_approx_area_sqmi"])
    area_difference_pct = 100.0 * (geometry_area_sqmi - cfr_area_sqmi) / cfr_area_sqmi
    area_qc_status = (
        "within_0_5_percent_of_current_cfr_approx_area"
        if abs(area_difference_pct) <= 0.5
        else "outside_0_5_percent_of_current_cfr_approx_area"
    )
    system_learned_at = _system_learned_at(source)

    records = []
    for index, row in frame.iterrows():
        source_record_id = clean(_value(row, "POLY_ID")) or str(index + 1)
        source_feature_id = f"{source.source_id}:{source_record_id}"
        source_polygon_name = clean(_value(row, "AREA_NAME", "Name"))
        source_area_sqmi = _float(_value(row, "AREA_SQMI", "AREA_SM"))
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=(
                f"national_marine_sanctuary:{metadata['sanctuary_id'].casefold()}"
            ),
            feature_name=str(metadata["name"]),
            feature_type="national_marine_sanctuary_boundary_polygon",
            authority="NOAA Office of National Marine Sanctuaries",
            jurisdiction="United States",
            legal_authority=source.legal_citation,
            legal_source_url=str(metadata["legal_url"]),
            source_coverage_status="complete_current_noaa_west_coast_sanctuary_roster",
        )
        record.update(
            LEGAL_BINDING_STATUS="binding_designation_reference_geometry",
            EFFECTIVE_START=str(metadata["effective_start"]),
            SYSTEM_LEARNED_AT=system_learned_at,
            SOURCE_VINTAGE=source.source_as_of,
            QC_STATUS=(
                "passed_with_legal_source_caveat"
                if area_qc_status.startswith("within")
                else "review_required"
            ),
            QC_REASON=(
                "NOAA GIS polygon agrees with the approximate current CFR area within "
                "0.5%; current CFR boundary text and coordinates remain controlling."
                if area_qc_status.startswith("within")
                else "NOAA GIS polygon differs from the approximate current CFR area by more "
                "than 0.5%; legal-boundary review is required."
            ),
            SANCTUARY_ID=str(metadata["sanctuary_id"]),
            AUTHORITY_ID="USA:NOAA:ONMS",
            COUNTRY_CODE="USA",
            SUBDIVISION_CODE=str(metadata["subdivision"]),
            DESIGNATION_TYPE="national_marine_sanctuary",
            DESIGNATION_STATUS="active_designated",
            EFFECTIVE_STATUS="active",
            CFR_PART="15 CFR part 922",
            CFR_SUBPART=str(metadata["cfr_subpart"]),
            CFR_BOUNDARY_SECTION=str(metadata["boundary_section"]),
            DESIGNATION_FEDERAL_REGISTER=str(metadata["designation_federal_register"]),
            BOUNDARY_AMENDMENT_SUMMARY=str(metadata["boundary_amendment_summary"]),
            AMENDMENT_HISTORY_STATUS="principal_designation_and_boundary_events_pinned",
            LEGAL_BOUNDARY_STATUS="current_cfr_text_and_coordinates_control",
            SOURCE_GEOMETRY_STATUS="onms_gis_boundary_representation_not_for_legal_use",
            SOURCE_POLYGON_NAME=source_polygon_name,
            SOURCE_DATUM=clean(_value(row, "DATUM")) or "NAD83 / EPSG:4269",
            SOURCE_AREA_SQMI=source_area_sqmi,
            SANCTUARY_GEOMETRY_AREA_SQMI=geometry_area_sqmi,
            CFR_APPROX_AREA_SQMI=cfr_area_sqmi,
            CFR_AREA_DIFFERENCE_PCT=area_difference_pct,
            AREA_QC_STATUS=area_qc_status,
            SANCTUARY_QC_REASON=(
                "The GIS archive is retained as mapped evidence; it is neither a navigational "
                "product nor the controlling legal boundary."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)
