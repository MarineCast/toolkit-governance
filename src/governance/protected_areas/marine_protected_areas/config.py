"""Configuration for marine protected areas."""

from pathlib import Path

from governance.shared.config import GovernanceConfig, load_governance_config

COLLECTION_ID = "marine_protected_areas"
DEFAULT_CONFIG_PATH = "config/data/governance/protected_areas/marine_protected_areas.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> GovernanceConfig:
    config = load_governance_config(path)
    if COLLECTION_ID not in config.collections:
        raise ValueError(f"Governance config does not define {COLLECTION_ID}.")
    return config
