"""Checksum, atomic publication, and manifest contracts for governance artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import geopandas as gpd

from .config import GovernanceCollection, GovernanceConfig, GovernanceSource
from .schema import validate_governance_geometry

MANIFEST_SCHEMA_VERSION = 1


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_dataset(path: str | Path) -> str:
    """Hash one file or an entire sidecar-based vector dataset deterministically."""

    source = Path(path)
    if source.is_file() and source.suffix.lower() != ".shp":
        return sha256_file(source)
    if source.suffix.lower() == ".shp":
        candidates = sorted(source.parent.glob(f"{source.stem}.*"))
    elif source.is_dir():
        candidates = sorted(item for item in source.rglob("*") if item.is_file())
    else:
        raise FileNotFoundError(f"Governance source dataset does not exist: {source}")
    digest = hashlib.sha256()
    for candidate in candidates:
        digest.update(candidate.name.encode("utf-8"))
        digest.update(sha256_file(candidate).encode("ascii"))
    return digest.hexdigest()


def atomic_write_json(path: str | Path, payload: Any, *, overwrite: bool = False) -> Path:
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, destination)
    return destination


def atomic_write_geoparquet(
    frame: gpd.GeoDataFrame,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
    try:
        frame.to_parquet(temporary, index=False, compression="zstd")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def source_record(source: GovernanceSource, path: Path | None) -> dict[str, Any]:
    available = path is not None and path.exists()
    runtime_snapshot: dict[str, Any] = {}
    if available and path is not None and path.suffix.lower() == ".json":
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if int(snapshot.get("snapshot_schema_version", 0)) == 1:
            runtime_snapshot = {
                "retrieved_at_utc": snapshot.get("retrieved_at_utc"),
                "server_filtered_runtime": snapshot.get("server_filtered"),
                "requested_bbox_wgs84": snapshot.get("requested_bbox_wgs84"),
                "service_layer_name": snapshot.get("metadata_response", {}).get("name"),
                "service_version": snapshot.get("metadata_response", {}).get("currentVersion"),
            }
            if snapshot.get("receipt_times_by_page"):
                runtime_snapshot.update(
                    receipt_times_by_page=True,
                    temporal_note=snapshot.get("temporal_note"),
                    page_receipts=[{k: v for k, v in page.items() if k != "response"}
                                   for page in snapshot.get("pages", [])],
                )
    elif available and path is not None:
        metadata_path = path.with_suffix(f"{path.suffix}.metadata.json")
        if metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            runtime_snapshot = {
                "retrieved_at_utc": metadata.get("retrieved_at_utc"),
                "download_bytes": metadata.get("bytes"),
                "download_sha256": metadata.get("sha256"),
            }
    return {
        "source_id": source.source_id,
        "provider": source.provider,
        "url": source.url,
        "snapshot_path": str(path.resolve()) if available and path is not None else None,
        "snapshot_sha256": sha256_dataset(path) if available and path is not None else None,
        "archive_member": source.archive_member,
        "archive_layer": source.archive_layer,
        "expected_sha256": source.expected_sha256,
        "source_as_of": source.source_as_of,
        "license": source.license_name,
        "attribution": source.attribution,
        "legal_citation": source.legal_citation,
        "redistribution": source.redistribution,
        "authority_scope": source.authority_scope,
        "configured_status": source.source_status,
        "server_filter_configured": source.server_filter,
        "page_size_configured": source.page_size,
        "runtime_status": "available" if available else "unavailable",
        **runtime_snapshot,
        "coverage": dict(source.coverage),
        "limitation": source.source_limitation,
    }


def manifest_payload(
    *,
    config: GovernanceConfig,
    collection: GovernanceCollection,
    frame: gpd.GeoDataFrame,
    sources: Sequence[Mapping[str, Any]],
    clip_diagnostics: Sequence[Mapping[str, Any]],
    limitations: Sequence[str],
) -> dict[str, Any]:
    validate_governance_geometry(frame)
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "product": f"governance.{collection.category}.{collection.collection_id}",
        "build_time_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "config_path": str(config.path),
        "config_sha256": sha256_file(config.path),
        "config_hash": config.config_hash,
        "common_config_path": str(config.common_config_path),
        "common_config_sha256": sha256_file(config.common_config_path),
        "area_name": config.area_name,
        "resolved_bounds_wgs84": dict(config.bounds),
        "clipping_method": config.clip_method,
        "clipping_tolerance_degrees": config.clip_tolerance_degrees,
        "native_geometry_contract": True,
        "h3_resolution": None,
        "model_eligible": False,
        "sources": [dict(value) for value in sources],
        "clip_diagnostics": [dict(value) for value in clip_diagnostics],
        "artifact": {
            "dataset_id": f"governance.{collection.category}.{collection.collection_id}",
            "path": str(collection.artifact_path),
            "rows": int(len(frame)),
            "geometry_types": sorted(set(frame.geometry.geom_type.astype(str))),
            "columns": [str(column) for column in frame.columns],
        },
        "source_completeness": "partial",
        "availability_semantics": {
            "missing_source": "unavailable, never observed absence",
            "empty_intersection": "not false or zero without complete authoritative coverage",
        },
        "known_limitations": list(limitations),
    }


def finalize_manifest(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    overwrite: bool = True,
) -> Path:
    content = dict(payload)
    artifact_path = Path(str(content["artifact"]["path"]))
    if not artifact_path.is_file():
        raise FileNotFoundError(f"Governance artifact does not exist: {artifact_path}")
    content["artifact"] = dict(content["artifact"])
    content["artifact"]["sha256"] = sha256_file(artifact_path)
    content["artifact"]["bytes"] = artifact_path.stat().st_size
    return atomic_write_json(path, content, overwrite=overwrite)


def load_manifest(path: str | Path, *, verify_artifact: bool = True) -> dict[str, Any]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(payload.get("manifest_schema_version", 0)) != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"Unsupported governance manifest: {manifest_path}")
    if payload.get("h3_resolution") is not None:
        raise ValueError("Governance manifest cannot declare an H3 resolution.")
    if payload.get("model_eligible") is not False:
        raise ValueError("Governance manifest must be model-ineligible by default.")
    if verify_artifact:
        artifact = payload.get("artifact", {})
        artifact_path = Path(str(artifact.get("path", "")))
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Manifest artifact does not exist: {artifact_path}")
        if sha256_file(artifact_path) != artifact.get("sha256"):
            raise ValueError(f"Governance artifact checksum mismatch: {artifact_path}")
    return payload
