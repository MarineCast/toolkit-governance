"""Expose the fisheries management-areas map-layer descriptor."""

from pathlib import Path

from governance.shared.layers import (
    GovernanceLayerDescriptor,
    descriptor_for_collection,
)

from .config import COLLECTION_ID, DEFAULT_CONFIG_PATH


def layer_descriptor(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> GovernanceLayerDescriptor:
    return descriptor_for_collection(COLLECTION_ID, config_path)
