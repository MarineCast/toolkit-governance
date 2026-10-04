"""Archive bounded ArcGIS responses for governance sources without altering raw data."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests

from .artifacts import atomic_write_json, sha256_file
from .config import GovernanceConfig, GovernanceSource

HEADERS = {
    "User-Agent": "MarineCastGovernance/0.1 (+https://github.com/MarineCast/toolkit-governance)",
    "Accept": "application/json, application/geo+json, */*",
}


class SourceUnavailableError(RuntimeError):
    """Raised when no authoritative runtime snapshot exists for a source."""


def resolve_source_path(source: GovernanceSource) -> Path | None:
    if source.local_path is not None and source.local_path.exists():
        return source.local_path
    if source.snapshot_path is not None and source.snapshot_path.exists():
        return source.snapshot_path
    return None


def _response_json(url: str, *, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as error:
        content_type = response.headers.get("Content-Type", "unknown")
        raise RuntimeError(
            f"ArcGIS response is not JSON: {url}; content_type={content_type!r}; "
            f"response_prefix={response.text[:160]!r}"
        ) from error
    if not isinstance(payload, dict):
        raise ValueError(f"ArcGIS response is not an object: {url}")
    if payload.get("error"):
        raise RuntimeError(f"ArcGIS error from {url}: {payload['error']}")
    return payload


def download_arcgis_snapshot(
    source: GovernanceSource,
    *,
    bbox: tuple[float, float, float, float],
    overwrite: bool = False,
) -> Path:
    """Archive every raw GeoJSON response page plus the exact query contract."""

    if source.snapshot_path is None:
        raise ValueError(f"ArcGIS source {source.source_id!r} has no snapshot_path.")
    if source.snapshot_path.exists() and not overwrite:
        return source.snapshot_path

    layer_url = source.url.rstrip("/")
    metadata_params = {"f": "json"}
    metadata = _response_json(layer_url, params=metadata_params, timeout=60)
    service_page_size = int(metadata.get("maxRecordCount", 1000)) or 1000
    page_size = min(service_page_size, source.page_size or service_page_size)
    query_url = f"{layer_url}/query"
    west, south, east, north = bbox
    base_params: dict[str, Any] = {
        "f": "geojson",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "resultRecordCount": page_size,
    }
    if source.server_filter:
        base_params.update(
            {
                "geometry": f"{west},{south},{east},{north}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
            }
        )
    pages: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {**base_params, "resultOffset": offset}
        payload = _response_json(query_url, params=params, timeout=120)
        features = payload.get("features", [])
        if not isinstance(features, list):
            raise ValueError(f"ArcGIS features are not a list for {source.source_id}.")
        pages.append({"request_params": params, "response": payload})
        if len(features) < page_size:
            break
        offset += len(features)
        if len(pages) > 10000:
            raise RuntimeError(f"ArcGIS pagination did not terminate for {source.source_id}.")

    snapshot = {
        "snapshot_schema_version": 1,
        "source_id": source.source_id,
        "source_url": source.url,
        "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "server_filtered": source.server_filter,
        "requested_bbox_wgs84": [west, south, east, north],
        "metadata_request": {"url": layer_url, "params": metadata_params},
        "metadata_response": metadata,
        "query_url": query_url,
        "pages": pages,
    }
    return atomic_write_json(source.snapshot_path, snapshot, overwrite=overwrite)


def _validate_expected_checksum(source: GovernanceSource, path: Path) -> None:
    if source.expected_sha256 is None:
        return
    actual = sha256_file(path)
    if actual != source.expected_sha256:
        raise ValueError(
            f"Governance source checksum mismatch for {source.source_id}: "
            f"expected {source.expected_sha256}, received {actual}."
        )


def download_direct_snapshot(
    source: GovernanceSource,
    *,
    overwrite: bool = False,
    max_bytes: int | None = None,
) -> Path:
    """Archive an exact versioned file download plus request metadata."""

    if source.snapshot_path is None:
        raise ValueError(f"Direct source {source.source_id!r} has no snapshot_path.")
    destination = source.snapshot_path
    metadata_path = destination.with_suffix(f"{destination.suffix}.metadata.json")
    if destination.exists() and not overwrite:
        _validate_expected_checksum(source, destination)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
    try:
        with requests.get(source.url, headers=HEADERS, stream=True, timeout=180) as response:
            response.raise_for_status()
            received = 0
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        received += len(chunk)
                        if max_bytes is not None and received > max_bytes:
                            raise SourceUnavailableError(f'Download exceeds {max_bytes} byte cap: {source.source_id}')
                        handle.write(chunk)
        _validate_expected_checksum(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    atomic_write_json(
        metadata_path,
        {
            "snapshot_schema_version": 1,
            "source_id": source.source_id,
            "source_url": source.url,
            "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "archive_member": source.archive_member,
            "archive_layer": source.archive_layer,
        },
        overwrite=True,
    )
    return destination


def acquire_source(
    config: GovernanceConfig,
    source_id: str,
    *,
    overwrite: bool = False,
) -> Path | None:
    source = config.sources[source_id]
    if source.local_path is not None and source.local_path.exists():
        _validate_expected_checksum(source, source.local_path)
        return source.local_path
    if source.acquisition_type == "direct_archive":
        return download_direct_snapshot(source, overwrite=overwrite)
    if source.acquisition_type == "arcgis" or (
        source.acquisition_type == "local_vector_or_arcgis" and source.snapshot_path is not None
    ):
        return download_arcgis_snapshot(source, bbox=config.bbox_tuple, overwrite=overwrite)
    if source.source_status == "unavailable" or source.acquisition_type == "reference_only":
        return None
    raise SourceUnavailableError(
        f"Unsupported governance acquisition type: {source.acquisition_type}"
    )


def acquire_collection_sources(
    config: GovernanceConfig,
    collection_id: str,
    *,
    overwrite: bool = False,
) -> list[Path]:
    collection = config.collections[collection_id]
    paths = []
    for source_id in collection.source_ids:
        path = acquire_source(config, source_id, overwrite=overwrite)
        if path is not None:
            paths.append(path)
    return paths


def read_source_frame(source: GovernanceSource) -> gpd.GeoDataFrame:
    path = resolve_source_path(source)
    if path is None:
        raise SourceUnavailableError(f"No runtime snapshot is available for {source.source_id}.")
    if path.suffix.lower() != ".json":
        if source.archive_member and source.archive_layer:
            archive_dataset = f"/vsizip/{path.resolve()}/{source.archive_member}"
            frame = gpd.read_file(archive_dataset, layer=source.archive_layer)
        elif source.archive_member:
            frame = gpd.read_file(f"zip://{path.resolve()}!{source.archive_member}")
        elif path.suffix.lower() in {".parquet", ".geoparquet"}:
            frame = gpd.read_parquet(path)
        else:
            frame = gpd.read_file(path)
        if frame.crs is None:
            raise ValueError(f"Governance source has no CRS: {path}")
        return frame.to_crs("EPSG:4326")

    import json

    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if int(snapshot.get("snapshot_schema_version", 0)) != 1:
        raise ValueError(f"Unsupported governance ArcGIS snapshot: {path}")
    features: list[dict[str, Any]] = []
    for page in snapshot.get("pages", []):
        features.extend(page.get("response", {}).get("features", []))
    if not features:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    frame = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return frame
