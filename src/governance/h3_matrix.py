"""Explicit, model-ineligible H3 overlays of verified native governance products."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, box
from shapely.ops import transform

from .shared.artifacts import load_manifest, sha256_dataset, sha256_file
from .shared.config import DEFAULT_CONFIG_PATH, load_governance_config
from .shared.schema import CANONICAL_FIELDS, validate_governance_geometry


def _grid(path: Path) -> gpd.GeoDataFrame:
    import h3

    table = pq.read_table(path, columns=["H3_INDEX", "H3_RESOLUTION"])
    if not pa.types.is_integer(table.schema.field("H3_RESOLUTION").type):
        raise ValueError("H3_RESOLUTION must have an integer type.")
    frame = table.to_pandas()
    if frame.empty or frame.isna().any().any() or frame.duplicated().any():
        raise ValueError(
            "H3 grid must have non-null unique cell/resolution keys and be nonempty."
        )
    polygons = []
    for cell, resolution in frame.itertuples(index=False, name=None):
        if not isinstance(cell, str) or not h3.is_valid_cell(cell):
            raise ValueError(f"Invalid H3 cell: {cell!r}")
        if h3.get_resolution(cell) != resolution:
            raise ValueError(f"H3 resolution mismatch: {cell}")
        vertices = [(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]
        if max(x for x, _ in vertices) - min(x for x, _ in vertices) > 180:
            raise ValueError(
                "Antimeridian-crossing H3 cells are unsupported by this overlay."
            )
        polygons.append(Polygon(vertices))
    output = gpd.GeoDataFrame(frame, geometry=polygons, crs=4326)
    if output.total_bounds[2] - output.total_bounds[0] > 180:
        raise ValueError("The H3 overlay requires a bounded non-antimeridian grid.")
    return output


def _attribute(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple, np.ndarray)):
        return json.dumps(
            value.tolist() if isinstance(value, np.ndarray) else value,
            default=str,
            sort_keys=True,
        )
    if pd.isna(value):
        return None
    return str(value)


def overlay_collection(
    grid: gpd.GeoDataFrame,
    native: gpd.GeoDataFrame,
    *,
    completeness: str,
    length_crs: str,
) -> dict[str, pa.Array]:
    """Overlay one validated native collection; preserve empty-intersection missingness."""
    if native.empty:
        if not set(CANONICAL_FIELDS).issubset(native.columns) or native.crs is None:
            raise ValueError('Empty overlay subset must retain its verified native schema/CRS')
    else:
        validate_governance_geometry(native)
    projected_grid = grid.to_crs(6933)
    extent = box(*grid.total_bounds)
    indexes = native.sindex.query(extent, predicate="intersects")
    local = native.iloc[indexes].copy().reset_index(drop=True)
    local.geometry = local.geometry.intersection(extent)
    projected = local.to_crs(6933)
    lengths = Transformer.from_crs(6933, length_crs, always_xy=True).transform
    matches: dict[int, list[tuple[int, Any, int]]] = defaultdict(list)
    if not local.empty:
        pairs = projected.sindex.query(projected_grid.geometry, predicate="intersects")
        intersections = shapely.intersection(
            projected_grid.geometry.to_numpy()[pairs[0]],
            projected.geometry.to_numpy()[pairs[1]],
        )
        for cell_index, feature_index, geometry in zip(
            pairs[0], pairs[1], intersections
        ):
            dimension = int(
                shapely.get_dimensions(projected.geometry.iloc[feature_index])
            )
            positive = (
                (dimension == 2 and geometry.area > 0)
                or (dimension == 1 and geometry.length > 0)
                or (dimension == 0 and not geometry.is_empty)
            )
            if positive:
                matches[int(cell_index)].append(
                    (int(feature_index), geometry, dimension)
                )
    size = len(grid)
    names = [column for column in native.columns if column != native.geometry.name]
    attributes = {name: [_attribute(value) for value in local[name]] for name in names}
    result: dict[str, list[Any]] = {
        key: [None] * size
        for key in (
            "FEATURE_COUNT",
            "POLYGON_COVERAGE_FRAC",
            "LINE_LENGTH_M",
            "POINT_COUNT",
        )
    }
    if completeness not in {
        "complete",
        "partial",
        "unknown",
        "unavailable",
        "not_applicable",
        "complete_current_noaa_west_coast_sanctuary_roster",
    }:
        raise ValueError(f"Unsupported source completeness: {completeness}")
    # A complete named roster is not complete authoritative coverage of the grid.
    coverage_state = (
        "partial"
        if completeness == "complete_current_noaa_west_coast_sanctuary_roster"
        else completeness
    )
    empty = f"no_recorded_geometry_under_{coverage_state}_coverage"
    result["INTERSECTION_STATUS"] = [empty] * size
    result["SOURCE_COMPLETENESS"] = [completeness] * size
    for name in names:
        result[f"NATIVE_{name}"] = [None] * size
    for cell_index, hits in matches.items():
        ids = {i for i, _, _ in hits}
        result["FEATURE_COUNT"][cell_index] = len(
            set(local.iloc[list(ids)]["GOVERNANCE_FEATURE_ID"])
        )
        result["INTERSECTION_STATUS"][cell_index] = "recorded_geometry_intersects"
        polygons = [geom for _, geom, dim in hits if dim == 2]
        lines = [geom for _, geom, dim in hits if dim == 1]
        points = {
            local.iloc[i]["GOVERNANCE_FEATURE_ID"] for i, _, dim in hits if dim == 0
        }
        if polygons:
            fraction = (
                shapely.union_all(polygons).area
                / projected_grid.geometry.iloc[cell_index].area
            )
            if fraction < -1e-10 or fraction > 1 + 1e-8:
                raise ValueError("Governance polygon fraction exceeds cell support.")
            result["POLYGON_COVERAGE_FRAC"][cell_index] = min(1.0, max(0.0, fraction))
        if lines:
            result["LINE_LENGTH_M"][cell_index] = transform(
                lengths, shapely.union_all(lines)
            ).length
        if points:
            result["POINT_COUNT"][cell_index] = len(points)
        for name in names:
            values = sorted(
                {attributes[name][i] for i in ids if attributes[name][i] is not None}
            )
            result[f"NATIVE_{name}"][cell_index] = values or None
    # Explicitly complete inventories support recorded zeros, still not legal absence.
    if completeness == "complete":
        for key in (
            "FEATURE_COUNT",
            "POLYGON_COVERAGE_FRAC",
            "LINE_LENGTH_M",
            "POINT_COUNT",
        ):
            for i in range(size):
                if i not in matches:
                    result[key][i] = 0
    types = {
        "FEATURE_COUNT": pa.int64(),
        "POINT_COUNT": pa.int64(),
        "POLYGON_COVERAGE_FRAC": pa.float64(),
        "LINE_LENGTH_M": pa.float64(),
        "INTERSECTION_STATUS": pa.string(),
        "SOURCE_COMPLETENESS": pa.string(),
    }
    return {
        key: pa.array(values, type=types.get(key, pa.list_(pa.string())))
        for key, values in result.items()
    }


def export_h3_matrix(
    grid_path: str | Path,
    output: str | Path,
    *,
    length_crs: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    allow_partial: bool = False,
    overwrite: bool = False,
) -> Path:
    """Write one explicit H3 overlay after validating every configured native product."""
    crs = CRS(length_crs)
    if (
        not crs.is_projected
        or not crs.axis_info
        or any(
            axis.unit_name.lower() not in ("metre", "meter") for axis in crs.axis_info
        )
    ):
        raise ValueError("length_crs must be a projected CRS with metre-based axes.")
    destination, source_grid = Path(output).resolve(), Path(grid_path).resolve()
    if destination.exists() and not overwrite:
        raise FileExistsError(destination)
    config = load_governance_config(config_path)
    input_paths = {
        source_grid,
        config.path.resolve(),
        config.common_config_path.resolve(),
    }
    for collection in config.collections.values():
        input_paths.update(
            (collection.artifact_path.resolve(), collection.manifest_path.resolve())
        )
    for source in config.sources.values():
        input_paths.update(
            p.resolve()
            for p in (source.local_path, source.snapshot_path)
            if p is not None
        )
    if destination in input_paths:
        raise ValueError(
            "Output cannot replace a grid, configuration, native product or raw input."
        )
    grid = _grid(source_grid)
    # Check the native clipping extent covers the entire consumer grid.
    west, south, east, north = grid.total_bounds
    b = config.bounds
    if (
        west < b["min_lon"]
        or east > b["max_lon"]
        or south < b["min_lat"]
        or north > b["max_lat"]
    ):
        raise ValueError("The grid extends beyond native full-area support.")
    arrays = {key: pa.array(grid[key]) for key in ("H3_INDEX", "H3_RESOLUTION")}
    arrays["MODEL_ELIGIBLE"] = pa.array([False] * len(grid))
    manifests = {}
    field_definitions = {}
    groups_metadata = {}
    for name, collection in config.collections.items():
        manifest = load_manifest(collection.manifest_path)
        if (
            Path(manifest["artifact"]["path"]).resolve()
            != collection.artifact_path.resolve()
        ):
            raise ValueError(f"Configured/native manifest path mismatch: {name}")
        native_config = load_governance_config(manifest["config_path"])
        if (
            manifest["config_hash"] != native_config.config_hash
            or native_config.collections[name] != collection
            or native_config.bounds != config.bounds
            or any(
                native_config.sources[s] != config.sources[s]
                for s in collection.source_ids
            )
            or sha256_file(native_config.common_config_path)
            != manifest["common_config_sha256"]
        ):
            raise ValueError(f"Native product configuration mismatch: {name}")
        completeness = manifest.get("source_completeness", "unknown")
        if completeness != "complete" and not allow_partial:
            raise ValueError(
                f"{name} coverage is {completeness}; pass --allow-partial explicitly."
            )
        records = manifest["sources"]
        if len(records) != len(collection.source_ids) or {
            r["source_id"] for r in records
        } != set(collection.source_ids):
            raise ValueError(f"Native source inventory mismatch: {name}")
        for record in records:
            snapshot = record.get("snapshot_path")
            if record.get("runtime_status") == "available" and not snapshot:
                raise ValueError(
                    f"Available source has no snapshot: {record['source_id']}"
                )
            if snapshot and sha256_dataset(snapshot) != record["snapshot_sha256"]:
                raise ValueError(f"Raw source checksum mismatch: {record['source_id']}")
        native = gpd.read_parquet(collection.artifact_path)
        print(
            f"Overlay {name}: {len(native):,} native parts on {len(grid):,} cells",
            flush=True,
        )
        validate_governance_geometry(native)
        if name in {'shipping_lanes', 'traffic_separation_schemes'}:
            from .vessel_management.routing import metric_groups
            groups = metric_groups(name)
            allowed_pairs = {(g['role'], g['source_id']) for g in groups.values()}
            if 'ROUTING_ROLE' not in native or not set(zip(native.ROUTING_ROLE, native.SOURCE_DATASET_ID)).issubset(allowed_pairs):
                raise ValueError(f'Unrecognized or missing routing roles: {name}')
        else:
            groups = {name: {'collection': name}}
        for prefix, group in groups.items():
            groups_metadata[prefix] = group
            subset = native.loc[(native.ROUTING_ROLE == group['role']) & (native.SOURCE_DATASET_ID == group['source_id'])] if 'role' in group else native
            group_completeness = completeness
            if 'source_id' in group and not any(r['source_id'] == group['source_id'] and r['runtime_status'] == 'available' for r in records):
                group_completeness = 'unavailable'
            columns = overlay_collection(
                grid, subset, completeness=group_completeness, length_crs=length_crs
            )
            for column, values in columns.items():
                key = f"{prefix}__{column}"
                arrays[key] = values
                unit = (
                    "proportion_of_full_cell"
                    if column == "POLYGON_COVERAGE_FRAC"
                    else (
                        "m"
                        if column == "LINE_LENGTH_M"
                        else (
                            "count"
                            if column in ("FEATURE_COUNT", "POINT_COUNT")
                            else (
                                "native_attribute_set_as_strings"
                                if column.startswith("NATIVE_")
                                else "category"
                            )
                        )
                    )
                )
                field_definitions[key] = {
                    "collection": name,
                    "variable": column,
                    "unit": unit,
                    "model_eligible": False,
                }
        manifests[name] = {
            "manifest_sha256": sha256_file(collection.manifest_path),
            "manifest": manifest,
        }
    import yaml

    catalog = yaml.safe_load(config.catalog_path.read_text())
    metadata = {
        "schema_version": 1,
        "product_id": "governance.h3_overlay_matrix",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "grain": ["H3_INDEX", "H3_RESOLUTION"],
        "model_eligible": False,
        "grid": {
            "path": str(source_grid),
            "sha256": sha256_file(source_grid),
            "rows": len(grid),
        },
        "config_hash": config.config_hash,
        "native_manifests": manifests,
        "catalog": catalog,
        "catalog_sha256": sha256_file(config.catalog_path),
        "fields": field_definitions,
        "metric_groups": groups_metadata,
        "area_crs": "EPSG:6933",
        "length_crs": crs.to_string(),
        "support": "full H3 polygon, positive-area/positive-length or point intersections",
        "missingness": "Empty intersections under partial, unknown or unavailable coverage remain null. No inference of legal or ecological absence.",
        "temporal_support": "Unfiltered native inventory snapshots; effective dates retained as attribute sets, not an as-of legal reconstruction.",
        "attribute_semantics": "Distinct native attribute sets are lists of strings, not aligned records; resolve feature/part IDs in checksum-verified native products.",
    }
    table = pa.table(arrays).replace_schema_metadata(
        {
            b"governance_h3_matrix": json.dumps(
                metadata, default=str, sort_keys=True
            ).encode()
        }
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
    try:
        pq.write_table(table, temporary, compression="zstd")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
