import json

import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from shapely.geometry import LineString, Point

from governance.h3_matrix import _grid, export_h3_matrix, overlay_collection
from governance.shared.artifacts import (
    finalize_manifest,
    manifest_payload,
    source_record,
)
from governance.shared.config import load_governance_config
from governance.shared.schema import CANONICAL_FIELDS
from governance.workspace import initialize_workspace


def native_frame(geometries, feature_ids=None):
    rows = []
    for i, geometry in enumerate(geometries):
        row = {key: None for key in CANONICAL_FIELDS}
        row.update(
            GOVERNANCE_FEATURE_ID=(
                feature_ids or [f"feature-{j}" for j in range(len(geometries))]
            )[i],
            GEOMETRY_PART_ID=f"part-{i}",
            MODEL_ELIGIBLE=False,
            MEASUREMENT_STATUS="observed",
            SOURCE_COVERAGE_STATUS="partial",
            FEATURE_NAME=f"Name {i}",
            SOURCE_DATASET_ID="test-source",
            geometry=geometry,
        )
        rows.append(row)
    return gpd.GeoDataFrame(rows, crs=4326)


@pytest.fixture
def grid_path(tmp_path):
    path = tmp_path / "grid.parquet"
    cells = [h3.latlng_to_cell(48.5, -123, 6), h3.latlng_to_cell(49.5, -123, 6)]
    pq.write_table(pa.table({"H3_INDEX": cells, "H3_RESOLUTION": [6, 6]}), path)
    return path


def test_polygon_parts_union_and_partial_missingness(grid_path):
    grid = _grid(grid_path)
    polygon = grid.geometry.iloc[0]
    native = native_frame([polygon, polygon], ["same-feature", "same-feature"])
    columns = overlay_collection(
        grid, native, completeness="partial", length_crs="EPSG:32610"
    )
    assert columns["FEATURE_COUNT"].to_pylist() == [1, None]
    assert columns["POLYGON_COVERAGE_FRAC"].to_pylist()[0] == pytest.approx(1)
    assert columns["POLYGON_COVERAGE_FRAC"].to_pylist()[1] is None
    assert columns["LINE_LENGTH_M"].to_pylist() == [None, None]
    assert columns["NATIVE_GEOMETRY_PART_ID"].to_pylist() == [
        ["part-0", "part-1"],
        None,
    ]
    assert (
        columns["INTERSECTION_STATUS"].to_pylist()[1]
        == "no_recorded_geometry_under_partial_coverage"
    )


def test_line_union_and_point_count(grid_path):
    grid = _grid(grid_path)
    centre = grid.geometry.iloc[0].centroid
    line = LineString([(centre.x - 0.002, centre.y), (centre.x + 0.002, centre.y)])
    native = native_frame([line, line, Point(centre)])
    columns = overlay_collection(
        grid, native, completeness="partial", length_crs="EPSG:32610"
    )
    assert columns["FEATURE_COUNT"].to_pylist() == [3, None]
    assert columns["POINT_COUNT"].to_pylist() == [1, None]
    expected = gpd.GeoSeries([line], crs=4326).to_crs(32610).length.iloc[0]
    assert columns["LINE_LENGTH_M"].to_pylist()[0] == pytest.approx(expected, rel=1e-5)
    assert columns["POLYGON_COVERAGE_FRAC"].to_pylist() == [None, None]


def test_complete_named_roster_does_not_imply_grid_absence(grid_path):
    grid = _grid(grid_path)
    native = native_frame([grid.geometry.iloc[0]])
    columns = overlay_collection(
        grid,
        native,
        completeness="complete_current_noaa_west_coast_sanctuary_roster",
        length_crs="EPSG:32610",
    )
    assert columns["FEATURE_COUNT"].to_pylist() == [1, None]
    assert (
        columns["INTERSECTION_STATUS"].to_pylist()[1]
        == "no_recorded_geometry_under_partial_coverage"
    )
    assert (
        columns["SOURCE_COMPLETENESS"].to_pylist()[1]
        == "complete_current_noaa_west_coast_sanctuary_roster"
    )


@pytest.mark.parametrize("mode", ["duplicate", "resolution", "invalid", "null"])
def test_grid_rejects_bad_identity(tmp_path, mode):
    cell = h3.latlng_to_cell(48.5, -123, 6)
    keys = {"H3_INDEX": [cell], "H3_RESOLUTION": [6]}
    if mode == "duplicate":
        keys = {"H3_INDEX": [cell, cell], "H3_RESOLUTION": [6, 6]}
    elif mode == "resolution":
        keys["H3_RESOLUTION"] = [8]
    elif mode == "invalid":
        keys["H3_INDEX"] = ["invalid"]
    else:
        keys["H3_INDEX"] = [None]
    path = tmp_path / "invalid.parquet"
    pq.write_table(pa.table(keys), path)
    with pytest.raises(ValueError):
        _grid(path)


@pytest.fixture
def workspace(tmp_path, monkeypatch, grid_path):
    root = tmp_path / "workspace"
    initialize_workspace(root)
    monkeypatch.setenv("GOVERNANCE_WORKSPACE", str(root))
    config_path = root / "config/data/governance/governance.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["collections"] = {
        "management_areas": config["collections"]["management_areas"]
    }
    config_path.write_text(yaml.safe_dump(config))
    config = load_governance_config()
    collection = config.collections["management_areas"]
    frame = native_frame([_grid(grid_path).geometry.iloc[0]])
    collection.artifact_path.parent.mkdir(parents=True)
    frame.to_parquet(collection.artifact_path, index=False)
    sources = [source_record(config.sources[s], None) for s in collection.source_ids]
    manifest = manifest_payload(
        config=config,
        collection=collection,
        frame=frame,
        sources=sources,
        clip_diagnostics=[],
        limitations=["synthetic offline fixture"],
    )
    finalize_manifest(collection.manifest_path, manifest)
    return config


def test_export_grain_provenance_and_fail_closed(workspace, grid_path, tmp_path):
    output = tmp_path / "overlay.parquet"
    with pytest.raises(ValueError, match="allow-partial"):
        export_h3_matrix(grid_path, output, length_crs="EPSG:32610")
    assert not output.exists()
    export_h3_matrix(grid_path, output, length_crs="EPSG:32610", allow_partial=True)
    table = pq.read_table(output)
    assert (
        table["H3_INDEX"].to_pylist()
        == pq.read_table(grid_path)["H3_INDEX"].to_pylist()
    )
    assert table["MODEL_ELIGIBLE"].to_pylist() == [False, False]
    metadata = json.loads(table.schema.metadata[b"governance_h3_matrix"])
    assert (
        metadata["native_manifests"]["management_areas"]["manifest"]["model_eligible"]
        is False
    )
    with pytest.raises(FileExistsError):
        export_h3_matrix(grid_path, output, length_crs="EPSG:32610", allow_partial=True)
    original = output.read_bytes()
    artifact = workspace.collections["management_areas"].artifact_path
    with artifact.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        export_h3_matrix(
            grid_path,
            output,
            length_crs="EPSG:32610",
            allow_partial=True,
            overwrite=True,
        )
    assert output.read_bytes() == original


def test_export_rejects_input_overwrite_and_nonmetric_crs(workspace, grid_path):
    with pytest.raises(ValueError, match="cannot replace"):
        export_h3_matrix(
            grid_path,
            grid_path,
            length_crs="EPSG:32610",
            allow_partial=True,
            overwrite=True,
        )
    with pytest.raises(ValueError, match="metre-based"):
        export_h3_matrix(
            grid_path,
            grid_path.parent / "out.parquet",
            length_crs="EPSG:4326",
            allow_partial=True,
        )


def test_export_detects_effective_config_drift(workspace, grid_path):
    raw = yaml.safe_load(workspace.path.read_text())
    raw["clipping"]["tolerance_degrees"] = 0.0001
    workspace.path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="configuration mismatch"):
        export_h3_matrix(
            grid_path,
            grid_path.parent / "out.parquet",
            length_crs="EPSG:32610",
            allow_partial=True,
        )
