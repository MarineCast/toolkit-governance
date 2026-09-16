"""Configuration for international boundaries."""

from pathlib import Path

from governance.shared.config import GovernanceConfig, load_governance_config

COLLECTION_ID = "international_boundaries"
DEFAULT_CONFIG_PATH = "config/data/governance/jurisdiction/international_boundaries.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> GovernanceConfig:
    config = load_governance_config(path)
    if COLLECTION_ID not in config.collections:
        raise ValueError(f"Governance config does not define {COLLECTION_ID}.")
    return config
