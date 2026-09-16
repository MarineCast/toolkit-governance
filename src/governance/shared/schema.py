"""Canonical native-geometry schema for governance collections."""

from __future__ import annotations

from collections.abc import Sequence

import geopandas as gpd

CANONICAL_FIELDS: tuple[str, ...] = (
    "GOVERNANCE_FEATURE_ID",
    "SOURCE_DATASET_ID",
    "SOURCE_FEATURE_ID",
    "GEOMETRY_PART_ID",
    "FEATURE_NAME",
    "FEATURE_TYPE",
    "AUTHORITY",
    "JURISDICTION",
    "LEGAL_BINDING_STATUS",
    "LEGAL_AUTHORITY",
    "LEGAL_SOURCE_URL",
    "EFFECTIVE_START",
    "EFFECTIVE_END",
    "SYSTEM_LEARNED_AT",
    "SOURCE_VINTAGE",
    "SOURCE_COVERAGE_STATUS",
    "MEASUREMENT_STATUS",
    "MODEL_ELIGIBLE",
    "QC_STATUS",
    "QC_REASON",
    "CLIPPED_TO_FULL_AREA",
    "SOURCE_MIN_LON",
    "SOURCE_MIN_LAT",
    "SOURCE_MAX_LON",
    "SOURCE_MAX_LAT",
    "RETAINED_GEOMETRY_TYPE",
    "RETAINED_MEASURE_FRACTION",
    "geometry",
)

VALID_MEASUREMENT_STATUSES = {
    "observed",
    "derived",
    "estimated",
    "fallback",
    "unavailable",
}


def validate_governance_geometry(
    frame: gpd.GeoDataFrame,
    *,
    required_extra_fields: Sequence[str] = (),
) -> None:
    """Fail closed on schema, identity, CRS, geometry, or model-policy drift."""

    if not isinstance(frame, gpd.GeoDataFrame):
        raise TypeError("Governance geometry must be a GeoDataFrame.")
    required = set(CANONICAL_FIELDS).union(required_extra_fields)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Governance geometry is missing canonical fields: {missing}")
    if frame.crs is None or frame.crs.to_epsg() != 4326:
        raise ValueError("Governance geometry must use EPSG:4326.")
    if frame.empty:
        raise ValueError("Governance geometry collection cannot be empty.")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Governance geometry contains null or empty shapes.")
    if (~frame.geometry.is_valid).any():
        raise ValueError("Governance geometry contains invalid shapes.")
    if frame["GOVERNANCE_FEATURE_ID"].isna().any():
        raise ValueError("GOVERNANCE_FEATURE_ID cannot be null.")
    if frame["GEOMETRY_PART_ID"].duplicated().any():
        raise ValueError("GEOMETRY_PART_ID must be unique within an artifact.")
    statuses = set(frame["MEASUREMENT_STATUS"].dropna().astype(str))
    invalid_statuses = sorted(statuses.difference(VALID_MEASUREMENT_STATUSES))
    if invalid_statuses:
        raise ValueError(f"Invalid governance measurement statuses: {invalid_statuses}")
    if frame["MODEL_ELIGIBLE"].fillna(False).astype(bool).any():
        raise ValueError("Governance fields are model-ineligible by default.")
    if any(str(column).upper().startswith("H3_") for column in frame.columns):
        raise ValueError("Canonical governance artifacts cannot contain H3 fields.")
