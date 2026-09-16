"""Reusable map-layer descriptors exposed by governance leaf inspectors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .artifacts import load_manifest
from .config import DEFAULT_CONFIG_PATH, load_governance_config


@dataclass(frozen=True)
class GovernanceLayerDescriptor:
    collection_id: str
    category: str
    display_name: str
    artifact_path: Path
    manifest_path: Path
    color: str
    default_visible: bool
    status: str
    reason: str | None
    geometry_types: tuple[str, ...]
    layer_id: str | None = None
    filters: tuple[tuple[str, str], ...] = ()

    def to_manifest_record(self) -> dict[str, Any]:
        output = asdict(self)
        output["artifact_path"] = str(self.artifact_path)
        output["manifest_path"] = str(self.manifest_path)
        return output


def descriptor_for_collection(
    collection_id: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    layer_id: str | None = None,
    display_name: str | None = None,
    color: str | None = None,
    default_visible: bool | None = None,
    filters: tuple[tuple[str, str], ...] = (),
) -> GovernanceLayerDescriptor:
    config = load_governance_config(config_path)
    collection = config.collections[collection_id]
    if not collection.artifact_path.is_file() or not collection.manifest_path.is_file():
        return GovernanceLayerDescriptor(
            collection_id=collection_id,
            category=collection.category,
            display_name=display_name or collection.display_name,
            artifact_path=collection.artifact_path,
            manifest_path=collection.manifest_path,
            color=color or collection.color,
            default_visible=(
                collection.default_visible if default_visible is None else default_visible
            ),
            status="unavailable",
            reason="Processed artifact or verified manifest has not been built.",
            geometry_types=(),
            layer_id=layer_id or collection_id,
            filters=filters,
        )
    manifest = load_manifest(collection.manifest_path, verify_artifact=True)
    return GovernanceLayerDescriptor(
        collection_id=collection_id,
        category=collection.category,
        display_name=display_name or collection.display_name,
        artifact_path=collection.artifact_path,
        manifest_path=collection.manifest_path,
        color=color or collection.color,
        default_visible=collection.default_visible if default_visible is None else default_visible,
        status="available",
        reason=None,
        geometry_types=tuple(manifest["artifact"].get("geometry_types", ())),
        layer_id=layer_id or collection_id,
        filters=filters,
    )
