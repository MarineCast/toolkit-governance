"""Validate MPA status groups and retain authority/rule evaluation metadata."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

from governance.shared.artifacts import (
    atomic_write_json,
)
from governance.shared.config import load_governance_config
from governance.shared.schema import validate_governance_geometry




def publish_mpa_products(
    artifact_path: str | Path,
    config_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Separate designation polygons from AOIs and document legal-source gaps."""

    artifact_path = Path(artifact_path)
    frame = gpd.read_parquet(artifact_path)
    required = (
        "DESIGNATION_ID",
        "AUTHORITY_ID",
        "COUNTRY_CODE",
        "DESIGNATION_STATUS",
        "EFFECTIVE_STATUS",
        "MANAGEMENT_AUTHORITY",
        "GOVERNING_RULE_STATUS",
        "MPA_QC_REASON",
    )
    validate_governance_geometry(frame, required_extra_fields=required)
    if any("SCORE" in str(column).upper() for column in frame.columns):
        raise ValueError("Marine protected-area products cannot synthesize a protection score.")

    polygons = frame.loc[
        frame.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        & ~frame["DESIGNATION_STATUS"].eq("area_of_interest")
    ].copy()
    areas_of_interest = frame.loc[frame["DESIGNATION_STATUS"].eq("area_of_interest")].copy()
    validate_governance_geometry(polygons, required_extra_fields=required)
    validate_governance_geometry(areas_of_interest, required_extra_fields=required)

    us = frame.loc[frame["COUNTRY_CODE"].eq("USA")]
    us_designations = us.drop_duplicates("DESIGNATION_ID")
    evaluation = {
        "schema_version": 1,
        "noaa_inventory_role": "discovery_and_reference_metadata",
        "noaa_inventory_is_governing_authority": False,
        "retained_us_designations": int(len(us_designations)),
        "retained_us_geometry_parts": int(len(us)),
        "us_features_with_management_authority": int(
            us_designations["MANAGEMENT_AUTHORITY"].notna().sum()
        ),
        "us_gov_rule_status_counts": {
            str(status): int(count)
            for status, count in us_designations["GOVERNING_RULE_STATUS"]
            .value_counts(dropna=False)
            .items()
        },
        "site_rule_gap_policy": (
            "Retain the management agency, authority URL, and program legal framework; "
            "flag every site whose governing instrument is not supplied by the inventory."
        ),
        "dfo_geometry_role": "visual_reference_regulation_coordinates_control",
        "area_of_interest_policy": "native_points_separate_from_designated_mpa_polygons",
        "protection_score": None,
    }

    config = load_governance_config(config_path)
    manifest_path = config.collections["marine_protected_areas"].manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["designation_policy"] = {
        "active_and_inventory_polygons_separate_from_areas_of_interest": True,
        "noaa_inventory_is_discovery_metadata": True,
        "dfo_regulation_coordinates_control": True,
        "source_native_area_of_interest_points": True,
        "area_of_interest_points_are_not_boundaries": True,
        "protection_strength_score": None,
        "model_eligible": False,
    }
    designations = frame.drop_duplicates("DESIGNATION_ID")
    manifest["designation_counts"] = {
        str(status): int(count)
        for status, count in designations["DESIGNATION_STATUS"].value_counts().items()
    }
    manifest["geometry_part_counts"] = {
        str(status): int(count)
        for status, count in frame["DESIGNATION_STATUS"].value_counts().items()
    }
    manifest["country_counts"] = {
        str(country): int(count)
        for country, count in designations["COUNTRY_CODE"].value_counts().items()
    }
    manifest["source_authority_evaluation"] = evaluation
    atomic_write_json(manifest_path, manifest, overwrite=True)
    return artifact_path
