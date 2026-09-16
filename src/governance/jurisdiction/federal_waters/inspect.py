"""Expose the federal maritime-zone map-layer descriptor."""

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


def layer_descriptors(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> list[GovernanceLayerDescriptor]:
    """Expose each legally distinct maritime-zone source as its own map toggle."""

    values = (
        (
            "federal_waters.us_territorial_sea",
            "U.S. territorial sea limit",
            "noaa_us_territorial_sea_dynamic",
            "#2166AC",
            True,
        ),
        (
            "federal_waters.us_contiguous_zone",
            "U.S. contiguous zone limit",
            "noaa_us_contiguous_zone_dynamic",
            "#4393C3",
            False,
        ),
        (
            "federal_waters.us_eez",
            "U.S. exclusive economic zone limit",
            "noaa_us_eez_dynamic",
            "#92C5DE",
            True,
        ),
        (
            "federal_waters.canada_eez_reference",
            "Canadian EEZ reference limit",
            "nrcan_canadian_geopolitical_boundaries_lines",
            "#053061",
            True,
        ),
    )
    return [
        descriptor_for_collection(
            COLLECTION_ID,
            config_path,
            layer_id=layer_id,
            display_name=display_name,
            color=color,
            default_visible=default_visible,
            filters=(("SOURCE_DATASET_ID", source_id),),
        )
        for layer_id, display_name, source_id, color, default_visible in values
    ]
