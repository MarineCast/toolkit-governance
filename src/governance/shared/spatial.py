"""Deterministic, antimeridian-safe clipping to the shared full AOI."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely import affinity, make_valid
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .config import GovernanceConfig


@dataclass(frozen=True)
class ClipDiagnostics:
    source_rows: int
    repaired_rows: int
    intersecting_rows: int
    excluded_rows: int
    output_parts: int
    clipped_source_rows: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def full_area_polygon(config: GovernanceConfig) -> Polygon:
    west, south, east, north = config.bbox_tuple
    return box(west, south, east, north)


def _unwrap_coordinates(coordinates: Iterable[tuple[float, ...]]) -> list[tuple[float, ...]]:
    values = [tuple(value) for value in coordinates]
    if not values:
        return []
    output = [values[0]]
    previous_x = float(values[0][0])
    for coordinate in values[1:]:
        x = float(coordinate[0])
        while x - previous_x > 180.0:
            x -= 360.0
        while x - previous_x < -180.0:
            x += 360.0
        output.append((x, *coordinate[1:]))
        previous_x = x
    return output


def _unwrap_geometry(geometry: BaseGeometry) -> BaseGeometry:
    if isinstance(geometry, Point):
        return geometry
    if isinstance(geometry, LineString):
        return LineString(_unwrap_coordinates(geometry.coords))
    if isinstance(geometry, Polygon):
        exterior = _unwrap_coordinates(geometry.exterior.coords)
        interiors = [_unwrap_coordinates(ring.coords) for ring in geometry.interiors]
        return Polygon(exterior, interiors)
    if isinstance(geometry, MultiPoint):
        return MultiPoint([_unwrap_geometry(item) for item in geometry.geoms])
    if isinstance(geometry, MultiLineString):
        return MultiLineString([_unwrap_geometry(item) for item in geometry.geoms])
    if isinstance(geometry, MultiPolygon):
        return MultiPolygon([_unwrap_geometry(item) for item in geometry.geoms])
    if isinstance(geometry, GeometryCollection):
        return GeometryCollection([_unwrap_geometry(item) for item in geometry.geoms])
    return geometry


def _dimension_family(geometry: BaseGeometry) -> str:
    if geometry.geom_type in {"Point", "MultiPoint"}:
        return "point"
    if geometry.geom_type in {"LineString", "MultiLineString", "LinearRing"}:
        return "line"
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        return "polygon"
    return "collection"


def _parts(geometry: BaseGeometry, family: str) -> list[BaseGeometry]:
    if geometry.is_empty:
        return []
    if _dimension_family(geometry) == family and not geometry.geom_type.startswith("Multi"):
        return [geometry]
    if hasattr(geometry, "geoms"):
        output: list[BaseGeometry] = []
        for item in geometry.geoms:
            output.extend(_parts(item, family))
        return output
    return []


def _antimeridian_intersection(geometry: BaseGeometry, aoi: Polygon) -> BaseGeometry:
    unwrapped = _unwrap_geometry(geometry)
    intersections = []
    for x_offset in (-360.0, 0.0, 360.0):
        candidate = affinity.translate(unwrapped, xoff=x_offset)
        if candidate.intersects(aoi):
            clipped = candidate.intersection(aoi)
            if not clipped.is_empty:
                intersections.append(clipped)
    return unary_union(intersections) if intersections else GeometryCollection()


def _measure(geometry: BaseGeometry) -> float:
    if geometry.is_empty:
        return 0.0
    family = _dimension_family(geometry)
    series = gpd.GeoSeries([geometry], crs="EPSG:4326").to_crs("EPSG:6933")
    if family == "polygon":
        return float(series.area.iloc[0])
    if family == "line":
        return float(series.length.iloc[0])
    return 1.0


def _stable_part_sort_key(geometry: BaseGeometry) -> tuple[str, str]:
    digest = hashlib.sha256(geometry.wkb).hexdigest()
    return geometry.geom_type, digest


def clip_to_full_area(
    frame: gpd.GeoDataFrame,
    config: GovernanceConfig,
    *,
    source_id_column: str = "SOURCE_FEATURE_ID",
) -> tuple[gpd.GeoDataFrame, ClipDiagnostics]:
    """Repair and clip each source feature without inventing enclosing polygons."""

    if not isinstance(frame, gpd.GeoDataFrame):
        raise TypeError("clip_to_full_area requires a GeoDataFrame.")
    if source_id_column not in frame:
        raise ValueError(f"Missing source identity column: {source_id_column}")
    if frame[source_id_column].isna().any():
        raise ValueError(f"{source_id_column} cannot contain null values.")
    if frame.crs is None:
        raise ValueError("Source governance geometry must declare a CRS.")
    work = frame.to_crs(config.clip_crs).copy()
    aoi = full_area_polygon(config)
    rows: list[dict[str, object]] = []
    repaired_rows = 0
    intersecting_rows = 0
    clipped_source_rows = 0

    for _, row in work.iterrows():
        original = row.geometry
        if original is None or original.is_empty:
            continue
        family = _dimension_family(original)
        repaired = original if original.is_valid else make_valid(original)
        repaired_rows += int(not original.is_valid)
        if family == "collection":
            raise ValueError(
                f"Unsupported mixed source geometry for {row[source_id_column]!r}: "
                f"{repaired.geom_type}"
            )
        clipped = _antimeridian_intersection(repaired, aoi)
        parts = sorted(_parts(clipped, family), key=_stable_part_sort_key)
        if not parts:
            continue
        intersecting_rows += 1
        source_measure = _measure(repaired)
        retained_measure = sum(_measure(part) for part in parts)
        retained_fraction = (
            min(1.0, max(0.0, retained_measure / source_measure)) if source_measure > 0 else None
        )
        clipped_flag = retained_fraction is not None and retained_fraction < 1.0 - 1.0e-12
        clipped_source_rows += int(clipped_flag)
        min_x, min_y, max_x, max_y = original.bounds
        base = row.drop(labels=[work.geometry.name]).to_dict()
        source_feature_id = str(row[source_id_column])
        for part_index, part in enumerate(parts, start=1):
            output = dict(base)
            output.update(
                GEOMETRY_PART_ID=f"{source_feature_id}:part-{part_index:03d}",
                CLIPPED_TO_FULL_AREA=bool(clipped_flag),
                SOURCE_MIN_LON=float(min_x),
                SOURCE_MIN_LAT=float(min_y),
                SOURCE_MAX_LON=float(max_x),
                SOURCE_MAX_LAT=float(max_y),
                RETAINED_GEOMETRY_TYPE=part.geom_type,
                RETAINED_MEASURE_FRACTION=retained_fraction,
                geometry=part,
            )
            rows.append(output)

    output_frame = (
        gpd.GeoDataFrame(rows, geometry="geometry", crs=config.clip_crs)
        if rows
        else gpd.GeoDataFrame(
            columns=[*work.columns, "GEOMETRY_PART_ID"], geometry="geometry", crs=config.clip_crs
        )
    )
    if not output_frame.empty:
        output_frame = output_frame.sort_values(
            [source_id_column, "GEOMETRY_PART_ID"], kind="stable"
        ).reset_index(drop=True)
        allowed = aoi.buffer(config.clip_tolerance_degrees)
        outside = output_frame.geometry.map(
            lambda geometry: not geometry.difference(allowed).is_empty
        )
        if outside.any():
            bad_ids = output_frame.loc[outside, source_id_column].astype(str).head(5).tolist()
            raise ValueError(f"Governance geometry remains outside full_area: {bad_ids}")

    diagnostics = ClipDiagnostics(
        source_rows=int(len(work)),
        repaired_rows=repaired_rows,
        intersecting_rows=intersecting_rows,
        excluded_rows=int(len(work) - intersecting_rows),
        output_parts=int(len(output_frame)),
        clipped_source_rows=clipped_source_rows,
    )
    return output_frame, diagnostics


def concatenate_clipped_frames(frames: Iterable[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    values = [frame for frame in frames if not frame.empty]
    if not values:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame(
        pd.concat(values, ignore_index=True), geometry="geometry", crs="EPSG:4326"
    )
