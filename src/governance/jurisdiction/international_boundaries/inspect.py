"""Expose the international-boundaries map-layer descriptor."""

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
    """Keep the overlapping authority/reference sources independently selectable."""

    values = (
        (
            "international_boundaries.ibc",
            "IBC international-boundary reference",
            "international_boundary_commission_v1_3",
            "#08519C",
            True,
        ),
        (
            "international_boundaries.noaa",
            "NOAA international-boundary reference",
            "noaa_us_maritime_limits",
            "#3182BD",
            False,
        ),
        (
            "international_boundaries.nrcan",
            "NRCan international-boundary reference",
            "nrcan_canadian_geopolitical_boundaries_lines",
            "#6BAED6",
            False,
        ),
        (
            "international_boundaries.country_water_support",
            "Derived country-water support",
            "seascape_territorial_water_support",
            "#BDD7E7",
            False,
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
