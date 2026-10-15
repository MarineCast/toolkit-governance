"""Canonical native-geometry schema for governance collections."""

from __future__ import annotations

from collections.abc import Sequence

import geopandas as gpd
import numpy as np
import pandas as pd

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
    if any(str(column).upper().startswith("H3_") for column in frame.columns):
        raise ValueError("Canonical governance artifacts cannot contain H3 fields.")
    if frame.empty:
        return
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Governance geometry contains null or empty shapes.")
    if (~frame.geometry.is_valid).any():
        raise ValueError("Governance geometry contains invalid shapes.")
    for field in ("GOVERNANCE_FEATURE_ID", "SOURCE_DATASET_ID", "SOURCE_FEATURE_ID", "GEOMETRY_PART_ID", "FEATURE_TYPE", "MEASUREMENT_STATUS", "SOURCE_COVERAGE_STATUS", "LEGAL_BINDING_STATUS"):
        if frame[field].isna().any() or frame[field].map(lambda value: not isinstance(value, str) or not value.strip()).any():
            raise ValueError(f"{field} must contain non-null nonempty strings")
    for field in ("MODEL_ELIGIBLE", "CLIPPED_TO_FULL_AREA"):
        if frame[field].isna().any() or frame[field].map(lambda value: not isinstance(value, (bool, np.bool_))).any():
            raise ValueError(f"{field} must contain non-null boolean values")
    if not frame.geometry.geom_type.isin(["Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"]).all():
        raise ValueError("Unsupported canonical geometry family")
    if not frame.RETAINED_GEOMETRY_TYPE.eq(frame.geometry.geom_type).all():
        raise ValueError("RETAINED_GEOMETRY_TYPE disagrees with geometry")
    for field in ("SOURCE_MIN_LON", "SOURCE_MIN_LAT", "SOURCE_MAX_LON", "SOURCE_MAX_LAT", "RETAINED_MEASURE_FRACTION", "SOURCE_AREA_KM2", "SOURCE_MARINE_AREA_KM2", "SOURCE_TOTAL_SITE_AREA_KM2"):
        if field in frame:
            values = frame[field].dropna()
            if values.map(lambda value: isinstance(value, (str, bool))).any() or not np.isfinite(pd.to_numeric(values, errors="coerce")).all():
                raise ValueError(f"{field} must contain finite numeric measurements or nulls")
            if ("AREA_KM2" in field or field == "RETAINED_MEASURE_FRACTION") and (values < 0).any():
                raise ValueError(f"{field} cannot be negative")
    fractions = frame.RETAINED_MEASURE_FRACTION.dropna()
    if (fractions > 1).any():
        raise ValueError("RETAINED_MEASURE_FRACTION must lie in [0, 1]")
    from .normalization import date_value
    for field in ("EFFECTIVE_START", "EFFECTIVE_END"):
        validated = set()
        for value in frame[field].dropna():
            if not isinstance(value, str):
                raise ValueError(f"{field} must be exact ISO dates or null")
            if value not in validated:
                if date_value(value) != value:
                    raise ValueError(f"{field} must be exact ISO dates or null")
                validated.add(value)
    intervals = frame.loc[frame.EFFECTIVE_START.notna() & frame.EFFECTIVE_END.notna()]
    if (intervals.EFFECTIVE_START > intervals.EFFECTIVE_END).any():
        raise ValueError("Effective interval start exceeds end")
    if not np.isfinite(frame.total_bounds).all() or frame.total_bounds[0] < -180 or frame.total_bounds[2] > 180 or frame.total_bounds[1] < -90 or frame.total_bounds[3] > 90:
        raise ValueError("Geometry bounds must be finite and within WGS84 support")
    validated = set()
    for value in frame.SYSTEM_LEARNED_AT.dropna():
        if not isinstance(value, str):
            raise ValueError('SYSTEM_LEARNED_AT must be an ISO UTC timestamp or null')
        if value in validated:
            continue
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed) or not (value.endswith('Z') or value.endswith('+00:00')):
            raise ValueError('SYSTEM_LEARNED_AT must be an ISO UTC timestamp or null')
        validated.add(value)
    if 'ESTABLISHMENT_DATE_PRECISION' in frame and not set(frame.ESTABLISHMENT_DATE_PRECISION.dropna()).issubset({'year', 'day', 'unknown'}):
        raise ValueError('Invalid establishment date precision')
    if 'SOURCE_ROLE' in frame:
        support = frame.SOURCE_ROLE.eq('spatial_support_only')
        if not frame.loc[support, 'LEGAL_BINDING_STATUS'].eq('derived_reference_geometry').all():
            raise ValueError('Spatial support cannot be relabeled as controlling legal authority')
    legal = {"reference_geometry", "derived_reference_geometry", "proposal_reference_geometry", "non_binding_physical_reference", "non_binding_cartographic_reference", "binding_designation_reference_geometry"}
    if not set(frame.LEGAL_BINDING_STATUS).issubset(legal):
        raise ValueError("Invalid LEGAL_BINDING_STATUS vocabulary")
    qc_values = set(frame.QC_STATUS.dropna())
    if not qc_values.issubset({'review_required', 'support_only', 'pass_with_limitations', 'passed_with_legal_source_caveat', 'passed'}):
        raise ValueError('Invalid QC_STATUS vocabulary')
    statuses = frame.SOURCE_COVERAGE_STATUS.astype(str)
    if not statuses.map(lambda s: any(s == state or s.startswith(state + "_") for state in ("complete", "partial", "unknown", "unavailable", "not_applicable"))).all():
        raise ValueError("Invalid SOURCE_COVERAGE_STATUS vocabulary")
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


def empty_governance_frame(*, extra_fields=(), crs=4326) -> gpd.GeoDataFrame:
    """Schema-preserving valid zero rows, with nullable canonical scalar dtypes."""
    import pandas as pd
    float_fields = {'SOURCE_MIN_LON', 'SOURCE_MIN_LAT', 'SOURCE_MAX_LON', 'SOURCE_MAX_LAT', 'RETAINED_MEASURE_FRACTION'}
    bool_fields = {'MODEL_ELIGIBLE', 'CLIPPED_TO_FULL_AREA'}
    data = {name: pd.Series(dtype='Float64' if name in float_fields else 'boolean' if name in bool_fields else 'object') for name in dict.fromkeys((*CANONICAL_FIELDS, *extra_fields)) if name != 'geometry'}
    return gpd.GeoDataFrame(data, geometry=gpd.GeoSeries([], crs=crs), crs=crs)
