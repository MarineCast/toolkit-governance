"""Normalize WDFW recreational marine management areas for this feature layer."""

from __future__ import annotations

import geopandas as gpd

from governance.shared.config import GovernanceSource
from governance.shared.normalization import base_record, clean, records_frame

NORMALIZATION_PROFILE = "wdfw_recreational_marine_areas"


def normalize(
    frame: gpd.GeoDataFrame,
    source: GovernanceSource,
) -> gpd.GeoDataFrame:
    """Preserve official WDFW management polygons and source semantics."""

    records = []
    for index, row in frame.iterrows():
        area_name = clean(row.get("AreaName"))
        object_id = clean(row.get("OBJECTID"))
        if area_name is None or object_id is None:
            raise ValueError("Original WDFW area and source record identifiers required")
        source_feature_id = f"{source.source_id}:{object_id}"
        title = clean(row.get("AreaTitle"))
        record = base_record(
            source,
            source_feature_id=source_feature_id,
            governance_feature_id=f"wdfw_marine_area:{area_name}",
            feature_name=f"WDFW Marine Area {area_name}" + (f" — {title}" if title else ""),
            feature_type="recreational_marine_catch_reporting_area",
            authority="Washington Department of Fish and Wildlife",
            jurisdiction="Washington",
            legal_authority=clean(row.get("WAC")) or source.legal_citation,
            legal_source_url="https://app.leg.wa.gov/WAC/default.aspx?cite=220-56-185",
            source_coverage_status="partial_washington_recreational_only",
        )
        record.update(
            MANAGEMENT_SYSTEM="WDFW recreational marine area",
            AREA_SYSTEM_ID="wdfw.recreational_marine_catch_reporting",
            AREA_HIERARCHY_LEVEL="marine_area",
            PARENT_AREA_CODE=None,
            FISHERY_SECTOR="recreational",
            AREA_CODE=area_name,
            AREA_TITLE=title,
            SECTOR_APPLICABILITY="recreational finfish and shellfish catch reporting",
            GEOMETRY_VERSION=source.source_as_of,
            geometry=row.geometry,
        )
        for name, value in row.items():
            if name != frame.geometry.name:
                record['WDFW_' + name] = clean(value)
        records.append(record)
    return records_frame(records, frame.crs)
