"""Publish federal-waters country slices and explicit zone availability."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd

from governance.shared.artifacts import (
    atomic_write_geoparquet,
    atomic_write_json,
    sha256_file,
)
from governance.shared.config import load_governance_config
from governance.shared.schema import validate_governance_geometry

CANADA_OCEANS_ACT_URL = "https://laws-lois.justice.gc.ca/eng/acts/O-2.4/"
NOAA_SOURCE_URL = "https://nauticalcharts.noaa.gov/data/us-maritime-limits-and-boundaries.html"
CHS_SOURCE_URL = (
    "https://www.dfo-mpo.gc.ca/science/hydrography-hydrographie/" "advise-expertise-eng.html"
)


def _related_artifact(path: Path, frame: gpd.GeoDataFrame) -> dict[str, Any]:
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "geometry_types": sorted(set(frame.geometry.geom_type.astype(str))),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _zone_availability() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "geometry_contract": "source_native_limit_lines",
        "inferred_or_buffered_zone_polygons": False,
        "boolean_federal_water_field": False,
        "zone_definitions_are_not_interchangeable": True,
        "countries": {
            "USA": {
                "authority": "NOAA/NOS Office of Coast Survey",
                "authority_url": NOAA_SOURCE_URL,
                "zones": {
                    "internal_waters": {
                        "status": "unavailable_geometry",
                        "reason": (
                            "The selected NOAA dynamic maritime-limit layers do not publish "
                            "an internal-waters polygon; none was inferred shoreward of a baseline."
                        ),
                        "source_ids": [],
                    },
                    "territorial_sea": {
                        "status": "available_current_dynamic_reference",
                        "geometry_type": "source_native_limit_line",
                        "source_ids": ["noaa_us_territorial_sea_dynamic"],
                    },
                    "contiguous_zone": {
                        "status": "available_current_dynamic_reference",
                        "geometry_type": "source_native_limit_line",
                        "source_ids": ["noaa_us_contiguous_zone_dynamic"],
                    },
                    "exclusive_economic_zone": {
                        "status": "available_current_dynamic_reference",
                        "geometry_type": "source_native_limit_line",
                        "source_ids": ["noaa_us_eez_dynamic"],
                    },
                },
            },
            "CAN": {
                "authority": "Government of Canada",
                "legal_authority_url": CANADA_OCEANS_ACT_URL,
                "hydrographic_authority_url": CHS_SOURCE_URL,
                "zones": {
                    "internal_waters": {
                        "status": "unavailable_machine_readable_authoritative_geometry",
                        "reason": (
                            "No approved public machine-readable authoritative geometry was "
                            "identified; the zone was not inferred from shoreline or baseline data."
                        ),
                        "source_ids": [],
                    },
                    "territorial_sea": {
                        "status": "unavailable_machine_readable_authoritative_geometry",
                        "reason": (
                            "The legal zone is defined by Canada, but no approved public "
                            "machine-readable authoritative geometry was identified."
                        ),
                        "source_ids": [],
                    },
                    "contiguous_zone": {
                        "status": "unavailable_machine_readable_authoritative_geometry",
                        "reason": (
                            "The legal zone is defined by Canada, but no approved public "
                            "machine-readable authoritative geometry was identified."
                        ),
                        "source_ids": [],
                    },
                    "exclusive_economic_zone": {
                        "status": "available_archived_government_reference",
                        "geometry_type": "source_native_limit_line",
                        "source_ids": ["nrcan_canadian_geopolitical_boundaries_lines"],
                        "reason": (
                            "GeoBase CGB is an archived government cartographic reference with "
                            "DFO source lineage where present, not the controlling legal boundary."
                        ),
                    },
                },
            },
        },
    }


def publish_zone_products(
    artifact_path: str | Path,
    config_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Publish country-native line subsets and attach their contract to the manifest."""

    artifact_path = Path(artifact_path)
    frame = gpd.read_parquet(artifact_path)
    required = (
        "COUNTRY_CODE",
        "ZONE_TYPE",
        "ZONE_LIMIT_NM",
        "GEOMETRY_ROLE",
        "SOURCE_POSITIONAL_ACCURACY_M",
        "ZONE_QC_REASON",
    )
    validate_governance_geometry(frame, required_extra_fields=required)
    if "IS_FEDERAL_WATER" in frame.columns:
        raise ValueError("Federal-waters artifacts must not flatten zones to IS_FEDERAL_WATER.")

    us_frame = frame.loc[frame["COUNTRY_CODE"].eq("USA")].copy()
    canada_frame = frame.loc[frame["COUNTRY_CODE"].eq("CAN")].copy()
    validate_governance_geometry(us_frame, required_extra_fields=required)
    validate_governance_geometry(canada_frame, required_extra_fields=required)

    output_dir = artifact_path.parent
    us_path = output_dir / "us_maritime_zone_limits.parquet"
    canada_path = output_dir / "canadian_maritime_zone_limits.parquet"
    availability_path = output_dir / "zone_availability.json"
    atomic_write_geoparquet(us_frame, us_path, overwrite=overwrite)
    atomic_write_geoparquet(canada_frame, canada_path, overwrite=overwrite)
    atomic_write_json(availability_path, _zone_availability(), overwrite=overwrite)

    config = load_governance_config(config_path)
    manifest_path = config.collections["federal_waters"].manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["zone_geometry_policy"] = {
        "source_native_geometry": True,
        "published_geometry": "limit_lines",
        "inferred_or_buffered_zone_polygons": False,
        "boolean_federal_water_field": False,
        "distinct_zone_types": sorted(frame["ZONE_TYPE"].dropna().unique()),
        "internal_waters_status": "explicitly_unavailable_geometry",
    }
    manifest["zone_counts"] = {
        country: {
            zone: int(count)
            for zone, count in country_frame["ZONE_TYPE"].value_counts().sort_index().items()
        }
        for country, country_frame in frame.groupby("COUNTRY_CODE", dropna=False)
    }
    manifest["source_vintages"] = {
        source_id: sorted(
            value for value in source_frame["SOURCE_VINTAGE"].dropna().astype(str).unique()
        )
        for source_id, source_frame in frame.groupby("SOURCE_DATASET_ID")
    }
    manifest["zone_availability"] = _zone_availability()
    manifest["related_artifacts"] = {
        "us_maritime_zone_limits": _related_artifact(us_path, us_frame),
        "canadian_maritime_zone_limits": _related_artifact(canada_path, canada_frame),
        "zone_availability": {
            "path": str(availability_path),
            "sha256": sha256_file(availability_path),
            "bytes": availability_path.stat().st_size,
        },
    }
    atomic_write_json(manifest_path, manifest, overwrite=True)
    return artifact_path
