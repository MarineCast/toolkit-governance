from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from governance.shared.config import load_governance_config
from governance.shared.spatial import clip_to_full_area, full_area_polygon


def test_full_area_clip_repairs_splits_and_preserves_stable_source_parts() -> None:
    config = load_governance_config()
    source = gpd.GeoDataFrame(
        {
            "SOURCE_FEATURE_ID": [
                "point",
                "boundary-point",
                "edge-line",
                "outside",
                "antimeridian",
                "bowtie",
                "multipart",
            ]
        },
        geometry=[
            Point(-125.0, 48.0),
            Point(-180.0, 40.0),
            LineString([(-130.0, 30.0), (-130.0, 40.0)]),
            Point(-100.0, 48.0),
            LineString([(179.0, 50.0), (-179.0, 50.0)]),
            Polygon(
                [
                    (-125.0, 40.0),
                    (-120.0, 45.0),
                    (-125.0, 45.0),
                    (-120.0, 40.0),
                    (-125.0, 40.0),
                ]
            ),
            MultiPolygon(
                [
                    Polygon(
                        [
                            (-126.0, 46.0),
                            (-124.0, 46.0),
                            (-124.0, 47.0),
                            (-126.0, 47.0),
                            (-126.0, 46.0),
                        ]
                    ),
                    Polygon(
                        [
                            (-101.0, 46.0),
                            (-99.0, 46.0),
                            (-99.0, 47.0),
                            (-101.0, 47.0),
                            (-101.0, 46.0),
                        ]
                    ),
                ]
            ),
        ],
        crs="EPSG:4326",
    )
    first, diagnostics = clip_to_full_area(source, config)
    second, _ = clip_to_full_area(source, config)

    assert "outside" not in set(first["SOURCE_FEATURE_ID"])
    assert diagnostics.repaired_rows == 1
    assert diagnostics.excluded_rows == 1
    assert diagnostics.output_parts > diagnostics.intersecting_rows
    assert first["GEOMETRY_PART_ID"].tolist() == second["GEOMETRY_PART_ID"].tolist()
    assert first["GEOMETRY_PART_ID"].is_unique
    assert first.geometry.is_valid.all()
    assert first.geometry.map(
        lambda geometry: geometry.difference(full_area_polygon(config)).is_empty
    ).all()
    antimeridian = first.loc[first["SOURCE_FEATURE_ID"].eq("antimeridian")]
    assert not antimeridian.empty
    assert antimeridian.total_bounds[0] == -180.0
    assert "boundary-point" in set(first["SOURCE_FEATURE_ID"])
    assert first.loc[first["SOURCE_FEATURE_ID"].eq("multipart"), "CLIPPED_TO_FULL_AREA"].all()


def test_full_area_clip_can_return_an_explicit_empty_collection() -> None:
    config = load_governance_config()
    source = gpd.GeoDataFrame(
        {"SOURCE_FEATURE_ID": ["outside"]},
        geometry=[Point(0.0, 0.0)],
        crs="EPSG:4326",
    )
    output, diagnostics = clip_to_full_area(source, config)
    assert output.empty
    assert diagnostics.excluded_rows == 1
