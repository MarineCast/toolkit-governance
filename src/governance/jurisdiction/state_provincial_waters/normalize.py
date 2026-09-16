"""Normalize BOEM state seaward boundary records for this feature layer."""

from __future__ import annotations

import geopandas as gpd

from governance.shared.config import GovernanceSource
from governance.shared.normalization import base_record, clean, records_frame

NORMALIZATION_PROFILE = "boem_submerged_lands_boundary"


def normalize(
    frame: gpd.GeoDataFrame,
    source: GovernanceSource,
) -> gpd.GeoDataFrame:
    """Preserve BOEM source lines without inferring enclosing water polygons."""

    records = []
    for index, row in frame.iterrows():
        object_id = clean(row.get("OBJECTID")) or str(index)
        source_feature_id = f"{source.source_id}:{object_id}"
        boundary_name = clean(row.get("BDRY_NAME_TEXT")) or "Submerged Lands Act boundary"
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"state_seaward_boundary:{object_id}",
            feature_name=boundary_name,
            feature_type="state_seaward_boundary_line",
            authority="Bureau of Ocean Energy Management",
            jurisdiction="United States coastal states",
            legal_authority=source.legal_citation,
            legal_source_url=source.url,
            source_coverage_status="partial_boundary_line_only",
        )
        record.update(
            BOUNDARY_APPROVAL_DATE=clean(row.get("BDRY_APRV_DATE")),
            BLOCK_NUMBER=clean(row.get("BLOCK_NUMBER")),
            PROVINCE_WATER_EQUIVALENT="unavailable",
            geometry=row.geometry,
        )
        records.append(record)
    return records_frame(records, frame.crs)
