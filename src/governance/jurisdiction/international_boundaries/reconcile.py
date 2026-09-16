"""Publish source-preserving international-boundary reconciliation artifacts."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from governance.shared.acquisition import read_source_frame
from governance.shared.artifacts import (
    atomic_write_geoparquet,
    atomic_write_json,
    sha256_file,
)
from governance.shared.config import load_governance_config
from governance.shared.schema import validate_governance_geometry

METRIC_CRS = "EPSG:3347"
SAMPLE_SPACING_M = 5_000.0


def _line_parts(geometry: BaseGeometry) -> list[LineString]:
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return list(geometry.geoms)
    if hasattr(geometry, "geoms"):
        return [part for item in geometry.geoms for part in _line_parts(item)]
    return []


def _sample_line(geometry: BaseGeometry) -> list[BaseGeometry]:
    points: list[BaseGeometry] = []
    for line in _line_parts(geometry):
        count = max(2, int(math.ceil(line.length / SAMPLE_SPACING_M)) + 1)
        points.extend(
            line.interpolate(float(distance)) for distance in np.linspace(0, line.length, count)
        )
    return points


def _marine_class(section_name: str) -> str:
    text = section_name.casefold()
    if any(value in text for value in ("strait", "canal")):
        return "marine"
    if "southeast alaska" in text:
        return "mixed_land_marine"
    return "terrestrial"


def _status(distances: np.ndarray, precision_m: float) -> tuple[str, float]:
    tolerance = max(25.0, precision_m)
    if distances.size == 0 or not np.isfinite(distances).any():
        return "comparison_geometry_unavailable", tolerance
    finite = distances[np.isfinite(distances)]
    if float(np.min(finite)) > 50_000.0:
        return "no_comparable_geometry_near_section", tolerance
    within_precision = float(np.mean(finite <= tolerance))
    p95 = float(np.percentile(finite, 95))
    if within_precision >= 0.90:
        return "aligned_within_reported_precision", tolerance
    if p95 <= max(1_000.0, tolerance * 5.0):
        return "minor_divergence_within_1km", tolerance
    if float(np.mean(finite <= 5_000.0)) >= 0.90:
        return "divergence_within_5km_review_required", tolerance
    return "unresolved_divergence", tolerance


def _comparison_targets(
    artifact: gpd.GeoDataFrame,
    config_path: str | Path,
) -> dict[str, dict[str, Any]]:
    config = load_governance_config(config_path)
    metric = artifact.to_crs(METRIC_CRS)
    targets: dict[str, dict[str, Any]] = {}
    for source_id, role in (
        ("noaa_us_maritime_limits", "U.S. agency boundary reference"),
        (
            "nrcan_canadian_geopolitical_boundaries_lines",
            "Canadian-government cartographic boundary reference",
        ),
    ):
        selected = metric.loc[
            metric["SOURCE_DATASET_ID"].eq(source_id)
            & metric.geometry.geom_type.isin(["LineString", "MultiLineString"])
        ]
        accuracy = pd.to_numeric(selected.get("SOURCE_POSITIONAL_ACCURACY_M"), errors="coerce")
        targets[source_id] = {
            "geometry": unary_union(selected.geometry.tolist()) if not selected.empty else None,
            "role": role,
            "accuracy_m": (
                float(accuracy.dropna().median())
                if accuracy is not None and accuracy.notna().any()
                else 0.0
            ),
        }

    dfo_source = config.sources["dfo_federal_marine_bioregions_support"]
    dfo = read_source_frame(dfo_source)
    pacific = dfo.loc[dfo.get("OCEAN_E", pd.Series(index=dfo.index, dtype="object")).eq("Pacific")]
    dfo_boundary = unary_union(pacific.to_crs(METRIC_CRS).geometry.tolist()).boundary
    targets[dfo_source.source_id] = {
        "geometry": dfo_boundary,
        "role": "ecosystem support used by canonical water geometry; not legal authority",
        "accuracy_m": 0.0,
    }

    polygons = metric.loc[metric["FEATURE_TYPE"].eq("country_water_reference_polygon")]
    canada = unary_union(polygons.loc[polygons["COUNTRY_CODE"].eq("CAN"), "geometry"].tolist())
    united_states = unary_union(
        polygons.loc[polygons["COUNTRY_CODE"].eq("USA"), "geometry"].tolist()
    )
    interface = (
        canada.boundary.intersection(united_states.boundary.buffer(100.0))
        if not canada.is_empty and not united_states.is_empty
        else None
    )
    targets["seascape_territorial_water_support"] = {
        "geometry": interface if interface is not None and not interface.is_empty else None,
        "role": "derived country-water support interface; not legal authority",
        "accuracy_m": 0.0,
    }
    return targets


def _reconciliation_rows(
    artifact: gpd.GeoDataFrame,
    config_path: str | Path,
) -> gpd.GeoDataFrame:
    metric = artifact.to_crs(METRIC_CRS)
    ibc = metric.loc[metric["SOURCE_DATASET_ID"].eq("international_boundary_commission_v1_3")]
    targets = _comparison_targets(artifact, config_path)
    rows: list[dict[str, Any]] = []
    for _, source_row in ibc.iterrows():
        points = _sample_line(source_row.geometry)
        scale_denominator = pd.to_numeric(
            source_row.get("SOURCE_SCALE_DENOMINATOR"), errors="coerce"
        )
        ibc_precision = float(scale_denominator) * 0.0005 if pd.notna(scale_denominator) else 0.0
        for comparison_source_id, target in targets.items():
            target_geometry = target["geometry"]
            distances = (
                np.asarray([point.distance(target_geometry) for point in points], dtype=float)
                if target_geometry is not None and not target_geometry.is_empty
                else np.asarray([], dtype=float)
            )
            comparison_precision = float(target["accuracy_m"] or 0.0)
            status, tolerance = _status(
                distances,
                max(ibc_precision, comparison_precision),
            )
            finite = distances[np.isfinite(distances)]
            statistics = {
                "MIN_DISTANCE_M": float(np.min(finite)) if finite.size else None,
                "MEDIAN_DISTANCE_M": float(np.median(finite)) if finite.size else None,
                "P95_DISTANCE_M": float(np.percentile(finite, 95)) if finite.size else None,
                "MAX_DISTANCE_M": float(np.max(finite)) if finite.size else None,
                "FRACTION_WITHIN_PRECISION": (
                    float(np.mean(finite <= tolerance)) if finite.size else None
                ),
                "FRACTION_WITHIN_5KM": (float(np.mean(finite <= 5_000.0)) if finite.size else None),
            }
            rows.append(
                {
                    "SOURCE_FEATURE_ID": source_row["SOURCE_FEATURE_ID"],
                    "SECTION_NUMBER": source_row.get("SECTION_NUMBER"),
                    "SECTION_NAME": source_row.get("SECTION_NAME"),
                    "MARINE_SEGMENT_CLASS": _marine_class(str(source_row.get("SECTION_NAME"))),
                    "SOURCE_SCALE": source_row.get("SOURCE_SCALE"),
                    "SOURCE_SCALE_DENOMINATOR": (
                        int(scale_denominator) if pd.notna(scale_denominator) else None
                    ),
                    "IBC_PRECISION_PROXY_M": ibc_precision or None,
                    "COMPARISON_SOURCE_ID": comparison_source_id,
                    "COMPARISON_ROLE": target["role"],
                    "COMPARISON_POSITIONAL_ACCURACY_M": comparison_precision or None,
                    "ANALYSIS_CRS": METRIC_CRS,
                    "SAMPLE_SPACING_M": SAMPLE_SPACING_M,
                    "SAMPLE_COUNT": len(points),
                    "COMPARISON_TOLERANCE_M": tolerance,
                    "RECONCILIATION_STATUS": status,
                    "BOUNDARY_QC_REASON": (
                        f"Directional IBC-to-source distance check; {status}. Source geometries "
                        "were compared as published and were not snapped, averaged, or replaced."
                    ),
                    **statistics,
                    "geometry": source_row.geometry,
                }
            )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=METRIC_CRS).to_crs("EPSG:4326")


def _apply_reconciliation_qc(
    artifact: gpd.GeoDataFrame,
    reconciliation: gpd.GeoDataFrame,
    config_path: str | Path,
) -> gpd.GeoDataFrame:
    output = artifact.copy()
    primary_sources = {
        "noaa_us_maritime_limits",
        "nrcan_canadian_geopolitical_boundaries_lines",
    }
    for source_feature_id, rows in reconciliation.groupby("SOURCE_FEATURE_ID", sort=False):
        primary = rows.loc[rows["COMPARISON_SOURCE_ID"].isin(primary_sources)]
        unresolved = primary.loc[
            primary["RECONCILIATION_STATUS"].isin(
                {
                    "divergence_within_5km_review_required",
                    "unresolved_divergence",
                    "comparison_geometry_unavailable",
                }
            )
        ]
        status = "unresolved_source_divergence" if not unresolved.empty else "source_compared"
        summary = "; ".join(
            f"{row.COMPARISON_SOURCE_ID}={row.RECONCILIATION_STATUS}" for row in rows.itertuples()
        )
        mask = output["SOURCE_FEATURE_ID"].eq(source_feature_id)
        output.loc[mask, "RECONCILIATION_STATUS"] = status
        output.loc[mask, "QC_STATUS"] = (
            "review_required" if not unresolved.empty else "pass_with_limitations"
        )
        output.loc[mask, "BOUNDARY_QC_REASON"] = (
            "Source-scale directional reconciliation completed with no snapping; " + summary
        )
        output.loc[mask, "QC_REASON"] = output.loc[mask, "BOUNDARY_QC_REASON"]

    independent = output["SOURCE_DATASET_ID"].isin(
        {"noaa_us_maritime_limits", "nrcan_canadian_geopolitical_boundaries_lines"}
    )
    output.loc[independent, "RECONCILIATION_STATUS"] = "independent_reference_preserved"

    config = load_governance_config(config_path)
    country_source = config.sources["nrcan_canadian_geopolitical_country_area"]
    country_area = read_source_frame(country_source).to_crs(METRIC_CRS)
    canada_reference = unary_union(country_area.geometry.tolist())
    metric = output.to_crs(METRIC_CRS)
    for index, row in metric.loc[
        metric["FEATURE_TYPE"].eq("country_water_reference_polygon")
    ].iterrows():
        total_area = row.geometry.area
        canada_fraction = (
            row.geometry.intersection(canada_reference).area / total_area if total_area else 0.0
        )
        expected_fraction = (
            canada_fraction if row.get("COUNTRY_CODE") == "CAN" else 1.0 - canada_fraction
        )
        consistent = expected_fraction >= 0.995
        output.loc[index, "COUNTRY_ALLOCATION_MATCH_FRACTION"] = expected_fraction
        output.loc[index, "COUNTRY_ALLOCATION_CHECK_SOURCE"] = country_source.source_id
        output.loc[index, "RECONCILIATION_STATUS"] = (
            "country_allocation_consistent" if consistent else "country_allocation_review_required"
        )
        output.loc[index, "QC_STATUS"] = "support_only" if consistent else "review_required"
        output.loc[index, "BOUNDARY_QC_REASON"] = (
            f"Country allocation agrees {expected_fraction:.6f} with the archived Canadian "
            "country-area reference. The polygon remains assembled seascape spatial support, "
            "not legal jurisdiction authority; exterior segments and source precision are unresolved."
        )
        output.loc[index, "QC_REASON"] = output.loc[index, "BOUNDARY_QC_REASON"]
    return output


def _related_artifact(path: Path, *, rows: int, geometry_types: list[str]) -> dict[str, Any]:
    return {
        "path": str(path),
        "rows": rows,
        "geometry_types": geometry_types,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def publish_reconciliation(
    artifact_path: str | Path,
    config_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Update the canonical artifact and publish boundary, polygon, and QC sidecars."""

    artifact_path = Path(artifact_path)
    artifact = gpd.read_parquet(artifact_path)
    reconciliation = _reconciliation_rows(artifact, config_path)
    output = _apply_reconciliation_qc(artifact, reconciliation, config_path)
    validate_governance_geometry(output)
    atomic_write_geoparquet(output, artifact_path, overwrite=True)

    output_dir = artifact_path.parent
    segments_path = output_dir / "authoritative_boundary_segments.parquet"
    country_path = output_dir / "country_water_polygons.parquet"
    reconciliation_path = output_dir / "boundary_reconciliation.parquet"
    segments = output.loc[output.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    countries = output.loc[output["FEATURE_TYPE"].eq("country_water_reference_polygon")].copy()
    validate_governance_geometry(segments)
    validate_governance_geometry(countries)
    atomic_write_geoparquet(segments, segments_path, overwrite=overwrite)
    atomic_write_geoparquet(countries, country_path, overwrite=overwrite)
    atomic_write_geoparquet(reconciliation, reconciliation_path, overwrite=overwrite)

    config = load_governance_config(config_path)
    manifest_path = config.collections["international_boundaries"].manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact"].update(
        rows=int(len(output)),
        geometry_types=sorted(set(output.geometry.geom_type.astype(str))),
        columns=[str(column) for column in output.columns],
        sha256=sha256_file(artifact_path),
        bytes=artifact_path.stat().st_size,
    )
    manifest["authority_policy"] = {
        "source_geometries_preserved_without_snapping": True,
        "legal_instruments_and_official_records_control": True,
        "seascape_territorial_water_role": "spatial_support_and_clipping_only",
        "seascape_territorial_water_is_legal_authority": False,
        "country_water_polygon_status": "derived_reference_geometry",
    }
    unresolved = reconciliation.loc[
        reconciliation["MARINE_SEGMENT_CLASS"].isin(["marine", "mixed_land_marine"])
        & reconciliation["RECONCILIATION_STATUS"].isin(
            {
                "divergence_within_5km_review_required",
                "unresolved_divergence",
                "comparison_geometry_unavailable",
                "no_comparable_geometry_near_section",
            }
        )
    ]
    manifest["reconciliation"] = {
        "method": "directional IBC-to-source sampled nearest-distance comparison",
        "analysis_crs": METRIC_CRS,
        "sample_spacing_m": SAMPLE_SPACING_M,
        "source_geometry_modified": False,
        "ibc_precision_proxy": "0.5 mm at retained section mapping scale",
        "comparison_sources": sorted(reconciliation["COMPARISON_SOURCE_ID"].unique()),
        "unresolved_marine_comparisons": int(len(unresolved)),
        "unresolved_marine_sections": sorted(unresolved["SECTION_NAME"].dropna().unique()),
    }
    manifest["related_artifacts"] = {
        "authoritative_boundary_segments": _related_artifact(
            segments_path,
            rows=len(segments),
            geometry_types=sorted(set(segments.geometry.geom_type.astype(str))),
        ),
        "country_water_polygons": _related_artifact(
            country_path,
            rows=len(countries),
            geometry_types=sorted(set(countries.geometry.geom_type.astype(str))),
        ),
        "boundary_reconciliation": _related_artifact(
            reconciliation_path,
            rows=len(reconciliation),
            geometry_types=sorted(set(reconciliation.geometry.geom_type.astype(str))),
        ),
    }
    atomic_write_json(manifest_path, manifest, overwrite=True)
    return artifact_path
