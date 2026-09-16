"""Expose distinct MPA authority/status groups as independent map layers."""

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
    values = (
        (
            "marine_protected_areas.us_state_tribal_local",
            "U.S. state, Tribal, territorial, and local MPA inventory",
            "us_state_tribal_local_reference",
            "#238B45",
            False,
        ),
        (
            "marine_protected_areas.us_federal",
            "U.S. federal MPA program inventory",
            "us_federal_program_reference",
            "#006D2C",
            False,
        ),
        (
            "marine_protected_areas.canada_active",
            "Canada Oceans Act designated MPAs",
            "canada_active_oceans_act",
            "#41AB5D",
            True,
        ),
        (
            "marine_protected_areas.canada_aoi",
            "Canada Oceans Act Areas of Interest",
            "canada_area_of_interest",
            "#A1D99B",
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
            filters=(("MAP_GROUP", map_group),),
        )
        for layer_id, display_name, map_group, color, default_visible in values
    ]
