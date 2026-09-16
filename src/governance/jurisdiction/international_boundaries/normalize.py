"""Normalize reconciled Canada-United States boundary source geometry."""

from __future__ import annotations

import re

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

NORMALIZATION_PROFILE = "reconciled_us_canada_international_boundaries"


def _scale_denominator(value: object) -> int | None:
    text = clean(value)
    if text is None:
        return None
    denominator = text.rsplit(":", maxsplit=1)[-1]
    digits = re.sub(r"[^0-9]", "", denominator)
    return int(digits) if digits else None


def _noaa(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    feature_type = column(frame, "FEAT_TYPE").fillna("").astype(str)
    selected = frame.loc[feature_type.str.contains("boundary", case=False, regex=False)].copy()
    records = []
    for index, row in selected.iterrows():
        boundary_id = clean(row.get("BOUND_ID")) or str(clean(row.get("OBJECTID")) or index)
        source_feature_id = f"{source.source_id}:{boundary_id}"
        region = clean(row.get("REGION"))
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"international_boundary:noaa:{boundary_id}",
            feature_name=region or boundary_id,
            feature_type="international_boundary_reference_segment",
            authority=clean(row.get("AOR")),
            jurisdiction=region or "Canada-United States",
            legal_authority=clean(row.get("LEGAL_AUTH")),
            legal_source_url=clean(row.get("SUPP_INFO")),
            source_coverage_status="partial_authoritative_reference",
        )
        record.update(
            BOUNDARY_ID=boundary_id,
            REGION=region,
            COUNTRY_CODE=None,
            SECTION_NUMBER=None,
            SECTION_NAME=None,
            PUBLICATION_DATE=date_value(row.get("PUB_DATE")),
            APPROVAL_DATE=date_value(row.get("APPRV_DATE")),
            UNILATERAL_CLAIM=clean(row.get("UNILATERAL")),
            SOURCE_ROLE="agency_boundary_reference",
            SOURCE_SCALE=None,
            SOURCE_SCALE_DENOMINATOR=None,
            SOURCE_POSITIONAL_ACCURACY_M=None,
            SOURCE_PRECISION_BASIS="not_reported_in_noaa_feature",
            SOURCE_LEGAL_STATUS="reference_not_for_legal_use",
            CANADIAN_SOURCE_AGENCY=None,
            CANADIAN_SOURCE_STATUS=None,
            CANADIAN_SOURCE_DESCRIPTION=None,
            RECONCILIATION_STATUS="pending_source_comparison",
            BOUNDARY_QC_REASON=(
                "NOAA reference geometry is not for legal use; comparison is published "
                "without snapping and controlling legal instruments prevail."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)


def _ibc(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    records = []
    for index, row in frame.iterrows():
        section_number = clean(row.get("SectionNum")) or str(index)
        section_name = clean(row.get("SectionEng")) or f"IBC section {section_number}"
        scale = clean(row.get("MaxScale"))
        source_feature_id = f"{source.source_id}:section-{section_number}"
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"international_boundary:ibc:section-{section_number}",
            feature_name=section_name,
            feature_type="international_boundary_reference_segment",
            authority=source.provider,
            jurisdiction="Canada-United States",
            legal_authority=source.legal_citation,
            legal_source_url=source.url,
            source_coverage_status="partial_authoritative_reference",
        )
        record.update(
            BOUNDARY_ID=f"IBC-{section_number}",
            REGION="Canada-United States",
            COUNTRY_CODE=None,
            SECTION_NUMBER=section_number,
            SECTION_NAME=section_name,
            PUBLICATION_DATE=source.source_as_of,
            APPROVAL_DATE=None,
            UNILATERAL_CLAIM=None,
            SOURCE_ROLE="commission_boundary_reference",
            SOURCE_SCALE=scale,
            SOURCE_SCALE_DENOMINATOR=_scale_denominator(scale),
            SOURCE_POSITIONAL_ACCURACY_M=None,
            SOURCE_PRECISION_BASIS="section_mapping_scale",
            SOURCE_LEGAL_STATUS="mapping_only_not_boundary_definition",
            CANADIAN_SOURCE_AGENCY=None,
            CANADIAN_SOURCE_STATUS=None,
            CANADIAN_SOURCE_DESCRIPTION=None,
            RECONCILIATION_STATUS="pending_source_comparison",
            BOUNDARY_QC_REASON=(
                f"IBC mapping-only digital representation at {scale or 'unreported scale'}; "
                "no coordinate snapping or replacement was applied."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)


def _cgb_lines(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    selected = frame.loc[column(frame, "TYPE_E").fillna("").astype(str).eq("INTERN")].copy()
    records = []
    for index, row in selected.iterrows():
        boundary_id = clean(row.get("UUID")) or str(index)
        accuracy = pd.to_numeric(row.get("ACCUR"), errors="coerce")
        accuracy_m = None if pd.isna(accuracy) else float(accuracy)
        source_agency = clean(row.get("SRC_AGENCY"))
        source_status = clean(row.get("STATUS"))
        source_description = clean(row.get("SRC_DESC"))
        source_feature_id = f"{source.source_id}:{boundary_id}"
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"international_boundary:cgb:{boundary_id}",
            feature_name=f"CGB international boundary {boundary_id}",
            feature_type="international_boundary_reference_segment",
            authority=source_agency or source.provider,
            jurisdiction="Canada-United States",
            legal_authority=source_description or source.legal_citation,
            legal_source_url=source.url,
            source_coverage_status="partial_authoritative_reference",
        )
        record.update(
            BOUNDARY_ID=boundary_id,
            REGION="Canada-United States",
            COUNTRY_CODE=None,
            SECTION_NUMBER=None,
            SECTION_NAME=None,
            PUBLICATION_DATE=date_value(row.get("P_UPD_DATE")),
            APPROVAL_DATE=None,
            UNILATERAL_CLAIM=None,
            SOURCE_ROLE="canadian_government_boundary_reference",
            SOURCE_SCALE=None,
            SOURCE_SCALE_DENOMINATOR=None,
            SOURCE_POSITIONAL_ACCURACY_M=accuracy_m,
            SOURCE_PRECISION_BASIS="CGB_ACCUR_field" if accuracy_m is not None else "unknown",
            SOURCE_LEGAL_STATUS="archived_cartographic_reference",
            CANADIAN_SOURCE_AGENCY=source_agency,
            CANADIAN_SOURCE_STATUS=source_status,
            CANADIAN_SOURCE_DESCRIPTION=source_description,
            RECONCILIATION_STATUS="pending_source_comparison",
            BOUNDARY_QC_REASON=(
                "Archived Canadian cartographic reference; source agency, status, and "
                "positional accuracy are retained and no snapping was applied."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)


def _country_water_support(
    frame: gpd.GeoDataFrame,
    source: GovernanceSource,
) -> gpd.GeoDataFrame:
    records = []
    country_counts: dict[str, int] = {}
    for index, row in frame.iterrows():
        country_name = (clean(row.get("NAME")) or "UNKNOWN").upper()
        country_code = {"CANADA": "CAN", "UNITED_STATES": "USA"}.get(country_name)
        if country_code is None:
            continue
        country_counts[country_code] = country_counts.get(country_code, 0) + 1
        part = country_counts[country_code]
        source_feature_id = f"{source.source_id}:{country_code}:{part:02d}"
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"country_water_reference:{country_code}:{part:02d}",
            feature_name=f"{country_name.replace('_', ' ').title()} water support",
            feature_type="country_water_reference_polygon",
            authority="OrcaCast spatial-support pipeline",
            jurisdiction=country_code,
            legal_authority="None; derived spatial support only",
            legal_source_url=source.url,
            source_coverage_status="partial_derived_support",
        )
        record.update(
            LEGAL_BINDING_STATUS="derived_reference_geometry",
            MEASUREMENT_STATUS="derived",
            BOUNDARY_ID=None,
            REGION=country_name,
            COUNTRY_CODE=country_code,
            SECTION_NUMBER=None,
            SECTION_NAME=None,
            PUBLICATION_DATE=None,
            APPROVAL_DATE=None,
            UNILATERAL_CLAIM=None,
            SOURCE_ROLE="spatial_support_only",
            SOURCE_SCALE=None,
            SOURCE_SCALE_DENOMINATOR=None,
            SOURCE_POSITIONAL_ACCURACY_M=None,
            SOURCE_PRECISION_BASIS="mixed_upstream_sources_see_water_geometry_manifest",
            SOURCE_LEGAL_STATUS="not_legal_authority",
            CANADIAN_SOURCE_AGENCY=None,
            CANADIAN_SOURCE_STATUS=None,
            CANADIAN_SOURCE_DESCRIPTION=None,
            RECONCILIATION_STATUS="pending_country_allocation_check",
            QC_STATUS="support_only",
            BOUNDARY_QC_REASON=(
                "Derived from the canonical seascape territorial-water support solely for "
                "clipping and country-water reference; the assembled outline is not a legal "
                "jurisdiction authority and unresolved exterior segments remain unchanged."
            ),
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)


def normalize(frame: gpd.GeoDataFrame, source: GovernanceSource) -> gpd.GeoDataFrame:
    """Dispatch source-specific semantics without modifying source geometry."""

    if source.source_id == "international_boundary_commission_v1_3":
        return _ibc(frame, source)
    if source.source_id == "noaa_us_maritime_limits":
        return _noaa(frame, source)
    if source.source_id == "nrcan_canadian_geopolitical_boundaries_lines":
        return _cgb_lines(frame, source)
    if source.source_id == "seascape_territorial_water_support":
        return _country_water_support(frame, source)
    if source.source_id in {
        "nrcan_canadian_geopolitical_country_area",
        "dfo_federal_marine_bioregions_support",
    }:
        return records_frame([], frame.crs)
    raise ValueError(f"Unsupported international-boundary source: {source.source_id}")
