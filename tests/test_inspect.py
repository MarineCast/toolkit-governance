from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import geopandas as gpd
from shapely.geometry import LineString

from governance.inspect import render_map
from governance.shared.config import load_governance_config
from governance.shared.layers import GovernanceLayerDescriptor


def test_consolidated_map_uses_grouped_multi_select_and_full_area(tmp_path) -> None:
    artifact = tmp_path / "layer.parquet"
    gpd.GeoDataFrame(
        {
            "FEATURE_NAME": ["Fixture boundary"],
            "FEATURE_TYPE": ["international_boundary"],
            "AUTHORITY": ["Fixture authority"],
            "JURISDICTION": ["Fixture"],
            "LEGAL_BINDING_STATUS": ["reference_geometry"],
            "EFFECTIVE_START": ["2020-01-01"],
            "EFFECTIVE_END": [None],
            "SOURCE_VINTAGE": ["2020-01-01"],
            "SOURCE_COVERAGE_STATUS": ["partial"],
            "QC_STATUS": ["review_required"],
            "QC_REASON": ["Fixture only"],
            "LEGAL_SOURCE_URL": ["https://example.test/legal"],
        },
        geometry=[LineString([(-125.0, 48.0), (-124.0, 49.0)])],
        crs="EPSG:4326",
    ).to_parquet(artifact, index=False)
    config = replace(
        load_governance_config(),
        map_path=tmp_path / "governance_layers.html",
        map_manifest_path=tmp_path / "governance_layers.manifest.json",
    )
    descriptor = GovernanceLayerDescriptor(
        collection_id="international_boundaries",
        category="jurisdiction",
        display_name="International boundaries",
        artifact_path=artifact,
        manifest_path=tmp_path / "unused-manifest.json",
        color="#1F78B4",
        default_visible=True,
        status="available",
        reason=None,
        geometry_types=("LineString",),
    )
    catalog = {
        "collections": {
            "international_boundaries": {
                "category": "jurisdiction",
                "display_name": "International boundaries",
                "implementation_status": "implemented",
                "map_layer": True,
            }
        }
    }
    output = render_map(
        config=config,
        catalog=catalog,
        descriptors=[descriptor],
        as_of=date(2026, 7, 30),
    )
    html = output.read_text(encoding="utf-8")
    assert "L.control.groupedLayers" in html
    assert "International boundaries [international_boundaries]" in html
    assert "Governance layer status" in html
    assert "Configured full_area" in html
    manifest = json.loads(config.map_manifest_path.read_text(encoding="utf-8"))
    assert manifest["grouped_multi_select"] is True
    assert manifest["rendered_layer_ids"] == ["international_boundaries"]
    assert manifest["resolved_bounds_wgs84"] == {
        "min_lon": -180.0,
        "min_lat": 32.0,
        "max_lon": -109.0,
        "max_lat": 72.0,
    }


def test_one_collection_can_publish_independent_filtered_map_layers(tmp_path) -> None:
    artifact = tmp_path / "zones.parquet"
    gpd.GeoDataFrame(
        {
            "FEATURE_NAME": ["Territorial", "EEZ"],
            "FEATURE_TYPE": ["zone_limit", "zone_limit"],
            "AUTHORITY": ["Fixture", "Fixture"],
            "JURISDICTION": ["USA", "USA"],
            "LEGAL_BINDING_STATUS": ["reference_geometry", "reference_geometry"],
            "EFFECTIVE_START": [None, None],
            "EFFECTIVE_END": [None, None],
            "SOURCE_VINTAGE": ["2026-01-01", "2026-01-01"],
            "SOURCE_COVERAGE_STATUS": ["partial", "partial"],
            "SOURCE_DATASET_ID": ["territorial", "eez"],
            "QC_STATUS": ["review_required", "review_required"],
            "QC_REASON": ["Fixture", "Fixture"],
            "LEGAL_SOURCE_URL": ["https://example.test", "https://example.test"],
        },
        geometry=[
            LineString([(-125.0, 48.0), (-124.0, 49.0)]),
            LineString([(-130.0, 48.0), (-129.0, 49.0)]),
        ],
        crs="EPSG:4326",
    ).to_parquet(artifact, index=False)
    config = replace(
        load_governance_config(),
        map_path=tmp_path / "split_layers.html",
        map_manifest_path=tmp_path / "split_layers.manifest.json",
    )
    common = {
        "collection_id": "federal_waters",
        "category": "jurisdiction",
        "artifact_path": artifact,
        "manifest_path": tmp_path / "unused.json",
        "default_visible": False,
        "status": "available",
        "reason": None,
        "geometry_types": ("LineString",),
    }
    descriptors = [
        GovernanceLayerDescriptor(
            **common,
            display_name="Territorial sea",
            color="#2166AC",
            layer_id="federal_waters.territorial",
            filters=(("SOURCE_DATASET_ID", "territorial"),),
        ),
        GovernanceLayerDescriptor(
            **common,
            display_name="EEZ",
            color="#92C5DE",
            layer_id="federal_waters.eez",
            filters=(("SOURCE_DATASET_ID", "eez"),),
        ),
    ]
    catalog = {
        "collections": {
            "federal_waters": {
                "category": "jurisdiction",
                "display_name": "Federal waters",
                "implementation_status": "implemented_partial",
                "map_layer": True,
            }
        }
    }
    output = render_map(
        config=config,
        catalog=catalog,
        descriptors=descriptors,
        as_of=date(2026, 7, 31),
    )
    html = output.read_text(encoding="utf-8")
    assert "Territorial sea [federal_waters.territorial]" in html
    assert "EEZ [federal_waters.eez]" in html
    manifest = json.loads(config.map_manifest_path.read_text(encoding="utf-8"))
    assert manifest["rendered_collection_ids"] == ["federal_waters"]
    assert manifest["rendered_layer_ids"] == [
        "federal_waters.eez",
        "federal_waters.territorial",
    ]
    assert [item["feature_count_total"] for item in manifest["layer_descriptors"]] == [
        1,
        1,
    ]
