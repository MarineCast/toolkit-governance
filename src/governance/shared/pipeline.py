"""Shared acquisition, clipping, validation, and publication pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import geopandas as gpd

from .acquisition import (
    SourceUnavailableError,
    acquire_collection_sources,
    read_source_frame,
    resolve_source_path,
)
from .artifacts import (
    publish_native_pair,
    manifest_payload,
    source_record,
)
from .config import (
    DEFAULT_CONFIG_PATH,
    GovernanceCollection,
    GovernanceConfig,
    GovernanceSource,
    load_governance_config,
)
from .coverage import write_coverage_matrix
from .schema import CANONICAL_FIELDS, validate_governance_geometry
from .spatial import clip_to_full_area, concatenate_clipped_frames

Normalizer = Callable[[gpd.GeoDataFrame, GovernanceSource], gpd.GeoDataFrame]


def _collection_is_complete(
    config: GovernanceConfig,
    collection: GovernanceCollection,
) -> bool:
    for source_id in collection.source_ids:
        source = config.sources[source_id]
        if resolve_source_path(source) is None:
            return False
        if any(status not in {"complete", "not_applicable"} for status in source.coverage.values()):
            return False
    return True


def build_collection(
    collection_id: str,
    normalizer: Normalizer,
    *,
    normalization_profile: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    allow_partial: bool = False,
    overwrite: bool = False,
) -> Path:
    """Build one collection with its layer-owned source normalizer."""

    config = load_governance_config(config_path)
    collection = config.collections[collection_id]
    if collection.normalization_profile != normalization_profile:
        raise ValueError(
            f"Governance collection {collection_id!r} expects normalization profile "
            f"{collection.normalization_profile!r}, not {normalization_profile!r}."
        )
    if not allow_partial and not _collection_is_complete(config, collection):
        raise ValueError(
            f"Governance collection {collection_id!r} has partial or unavailable full-AOI "
            "coverage; pass allow_partial=True for explicit research/context publication."
        )

    clipped_frames = []
    diagnostics = []
    records = []
    limitations = []
    available_sources = 0
    for source_id in collection.source_ids:
        source = config.sources[source_id]
        path = resolve_source_path(source)
        records.append(source_record(source, path))
        if path is None:
            limitations.append(f"{source_id}: unavailable — {source.source_limitation}")
            continue
        raw = read_source_frame(source, bbox=config.bbox_tuple)
        available_sources += 1
        from .registry import normalize_collection
        normalized = normalize_collection(raw, source, collection, normalizer=normalizer)
        if normalized.empty:
            from .schema import empty_governance_frame
            from governance.maintenance.catalog import EXTRA_FEATURES
            normalized = empty_governance_frame(extra_fields=[value[0] for value in EXTRA_FEATURES.get(collection_id, ())])
        if normalized.empty:
            limitations.append(f"{source_id}: successful source query with no selected records.")
        clipped, clip_diagnostic = clip_to_full_area(normalized, config)
        diagnostics.append({"source_id": source_id, **clip_diagnostic.to_dict()})
        clipped_frames.append(clipped)
        limitations.append(f"{source_id}: {source.source_limitation}")

    output = concatenate_clipped_frames(clipped_frames)
    if not available_sources:
        write_coverage_matrix(config_path, overwrite=True)
        raise SourceUnavailableError(
            f"No supported in-AOI source geometry is available for {collection_id}."
        )
    canonical = [column for column in CANONICAL_FIELDS if column in output.columns]
    extras = sorted(set(output.columns).difference(canonical))
    output = output[[*canonical[:-1], *extras, "geometry"]]
    validate_governance_geometry(output)
    payload = manifest_payload(
        config=config,
        collection=collection,
        frame=output,
        sources=records,
        clip_diagnostics=diagnostics,
        limitations=limitations,
    )
    publish_native_pair(output, collection.artifact_path, collection.manifest_path, payload, overwrite=overwrite)
    write_coverage_matrix(config_path, overwrite=True)
    return collection.artifact_path


def download_collection(
    collection_id: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    overwrite: bool = False,
) -> list[Path]:
    """Acquire every available source configured for one collection."""

    config = load_governance_config(config_path)
    paths = acquire_collection_sources(config, collection_id, overwrite=overwrite)
    write_coverage_matrix(config_path, overwrite=True)
    return paths
