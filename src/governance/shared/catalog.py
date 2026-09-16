"""Load and verify the generated governance feature catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import yaml

from .artifacts import load_manifest
from .config import DEFAULT_CONFIG_PATH, load_governance_config


def load_catalog(path: str | Path | None = None, *, config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config = load_governance_config(config_path)
    catalog_path = Path(path) if path is not None else config.catalog_path
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Governance catalog root must be a mapping: {catalog_path}")
    return payload


def validate_catalog(*, verify_artifacts: bool = False, config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config = load_governance_config(config_path)
    catalog = load_catalog(config.catalog_path, config_path=config_path)
    if int(catalog.get("schema_version", 0)) != 1:
        raise ValueError("Unsupported governance feature-catalog schema.")
    if catalog.get("area") != "full_area" or catalog.get("h3_products") is not False:
        raise ValueError("Governance catalog must declare full_area native geometry without H3.")
    collections = catalog.get("collections", {})
    from governance.maintenance.catalog import CATEGORY_COLLECTIONS

    leaf_ids = {name for names in CATEGORY_COLLECTIONS.values() for name in names}
    if set(collections) != leaf_ids:
        raise ValueError(
            "Governance catalog/leaf mismatch: "
            f"missing={sorted(leaf_ids.difference(collections))}, "
            f"extra={sorted(set(collections).difference(leaf_ids))}"
        )
    for collection_id, values in collections.items():
        for feature in values.get("features", []):
            if feature.get("model_eligible") is not False:
                raise ValueError(
                    f"Governance feature is model-eligible by default: {collection_id}"
                )
        if not verify_artifacts or not values.get("artifact"):
            continue
        configured = config.collections[collection_id]
        if not configured.artifact_path.is_file():
            continue
        load_manifest(configured.manifest_path, verify_artifact=True)
        frame = gpd.read_parquet(configured.artifact_path)
        expected = {feature["name"] for feature in values["features"]}
        actual = set(frame.columns)
        if expected != actual:
            raise ValueError(
                f"Governance catalog schema mismatch for {collection_id}: "
                f"missing={sorted(expected.difference(actual))}, "
                f"stale={sorted(actual.difference(expected))}"
            )
    return catalog
