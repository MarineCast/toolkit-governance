"""Full-AOI source and coverage matrix for governance collections."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifacts import atomic_write_json, sha256_file
from .config import DEFAULT_CONFIG_PATH, GovernanceConfig, load_governance_config


def build_coverage_matrix(config: GovernanceConfig) -> dict[str, Any]:
    collections: dict[str, Any] = {}
    for collection_id, collection in sorted(config.collections.items()):
        source_rows = []
        for source_id in collection.source_ids:
            source = config.sources[source_id]
            runtime_path = (
                source.local_path
                if source.local_path and source.local_path.exists()
                else source.snapshot_path
            )
            source_rows.append(
                {
                    "source_id": source_id,
                    "provider": source.provider,
                    "configured_status": source.source_status,
                    "runtime_status": (
                        "available"
                        if runtime_path is not None and runtime_path.exists()
                        else "unavailable"
                    ),
                    "coverage": dict(source.coverage),
                    "limitation": source.source_limitation,
                }
            )
        collections[collection_id] = {
            "category": collection.category,
            "artifact_path": str(collection.artifact_path),
            "artifact_status": "built" if collection.artifact_path.is_file() else "not_built",
            "sources": source_rows,
        }
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "area_name": config.area_name,
        "resolved_bounds_wgs84": dict(config.bounds),
        "common_config_path": str(config.common_config_path),
        "common_config_sha256": sha256_file(config.common_config_path),
        "coverage_regions": dict(config.coverage_regions),
        "coverage_semantics": {
            "complete": "authoritative source is complete for the named source scope",
            "partial": "some in-scope records exist; absence cannot be inferred",
            "unavailable": "required authoritative coverage is not configured or not acquired",
            "unknown": "source coverage has not been established",
            "not_applicable": "source authority does not apply to the region",
        },
        "collections": collections,
    }


def write_coverage_matrix(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    overwrite: bool = True,
) -> Path:
    config = load_governance_config(config_path)
    return atomic_write_json(
        config.coverage_matrix_path,
        build_coverage_matrix(config),
        overwrite=overwrite,
    )
