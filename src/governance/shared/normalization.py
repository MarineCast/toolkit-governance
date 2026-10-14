"""Canonical record helpers shared by governance source normalizers."""

from __future__ import annotations

from datetime import date, datetime
from numbers import Real
import re
from typing import Any

import geopandas as gpd
import pandas as pd

from .config import GovernanceSource


def clean(value: Any) -> str | None:
    """Return a trimmed source value or ``None`` for missing/blank values."""

    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def date_value(value: Any, *, encoding: str | None = None) -> str | None:
    """Parse declared epoch-ms or unambiguous ISO dates; never guess numeric units."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Real) and not isinstance(value, bool):
        if encoding != "arcgis_epoch_ms":
            raise ValueError(f"Numeric source date requires declared arcgis_epoch_ms encoding: {value!r}")
        parsed = pd.to_datetime(value, unit="ms", utc=True, errors="coerce")
    elif isinstance(value, (date, datetime, pd.Timestamp)):
        parsed = pd.Timestamp(value)
    elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].*)?", value.strip()):
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
    else:
        raise ValueError(f"Malformed or ambiguous source date: {value!r}")
    if pd.isna(parsed):
        raise ValueError(f"Malformed source date: {value!r}")
    return parsed.date().isoformat()


def source_date(frame: gpd.GeoDataFrame, field: str, value: Any, *, arcgis_date: bool = False) -> str | None:
    """Use archived field declarations; explicit provider contract covers offline fixtures."""
    fields = {item["name"].casefold(): item.get("type") for item in frame.attrs.get("layer_metadata", {}).get("fields", [])}
    declared = fields.get(field.casefold())
    if declared is not None and declared != "esriFieldTypeDate":
        if isinstance(value, Real):
            raise ValueError(f"Upstream date schema drift for {field}: {declared}")
        arcgis_date = False
    return date_value(value, encoding="arcgis_epoch_ms" if declared == "esriFieldTypeDate" or arcgis_date else None)


def column(frame: pd.DataFrame, *names: str) -> pd.Series:
    """Resolve a source column case-insensitively, returning nulls if absent."""

    lookup = {str(value).casefold(): value for value in frame.columns}
    for name in names:
        resolved = lookup.get(name.casefold())
        if resolved is not None:
            return frame[resolved]
    return pd.Series([None] * len(frame), index=frame.index, dtype="object")


def records_frame(records: list[dict[str, Any]], crs: Any) -> gpd.GeoDataFrame:
    """Create a WGS84-capable geometry frame from normalized source records."""

    if not records:
        from .schema import empty_governance_frame
        return empty_governance_frame(crs=crs or "EPSG:4326")
    return gpd.GeoDataFrame(records, geometry="geometry", crs=crs or "EPSG:4326")


def base_record(
    source: GovernanceSource,
    *,
    source_feature_id: str,
    governance_feature_id: str,
    feature_name: str | None,
    feature_type: str,
    authority: str | None,
    jurisdiction: str | None,
    legal_authority: str | None,
    legal_source_url: str | None,
    source_coverage_status: str,
) -> dict[str, Any]:
    """Create the canonical fields common to every normalized governance record."""

    return {
        "GOVERNANCE_FEATURE_ID": governance_feature_id,
        "SOURCE_DATASET_ID": source.source_id,
        "SOURCE_FEATURE_ID": source_feature_id,
        "FEATURE_NAME": feature_name,
        "FEATURE_TYPE": feature_type,
        "AUTHORITY": authority or source.provider,
        "JURISDICTION": jurisdiction,
        "LEGAL_BINDING_STATUS": "reference_geometry",
        "LEGAL_AUTHORITY": legal_authority or source.legal_citation,
        "LEGAL_SOURCE_URL": legal_source_url or source.url,
        "EFFECTIVE_START": None,
        "EFFECTIVE_END": None,
        "SYSTEM_LEARNED_AT": source.retrieved_at_utc,
        "SOURCE_VINTAGE": source.source_as_of,
        "SOURCE_COVERAGE_STATUS": source_coverage_status,
        "MEASUREMENT_STATUS": "observed",
        "MODEL_ELIGIBLE": False,
        "QC_STATUS": "review_required",
        "QC_REASON": source.source_limitation,
    }
