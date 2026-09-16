"""Canonical record helpers shared by governance source normalizers."""

from __future__ import annotations

from datetime import UTC, datetime
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


def date_value(value: Any) -> str | None:
    """Normalize one source date to ISO calendar-date form."""

    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date().isoformat()


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
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs or "EPSG:4326")
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
        "SYSTEM_LEARNED_AT": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "SOURCE_VINTAGE": source.source_as_of,
        "SOURCE_COVERAGE_STATUS": source_coverage_status,
        "MEASUREMENT_STATUS": "observed",
        "MODEL_ELIGIBLE": False,
        "QC_STATUS": "review_required",
        "QC_REASON": source.source_limitation,
    }
