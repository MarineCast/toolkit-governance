"""Configuration for federal maritime-zone limits."""

from pathlib import Path

from governance.shared.config import GovernanceConfig, load_governance_config

COLLECTION_ID = "federal_waters"
DEFAULT_CONFIG_PATH = "config/data/governance/jurisdiction/federal_waters.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> GovernanceConfig:
    config = load_governance_config(path)
    if COLLECTION_ID not in config.collections:
        raise ValueError(f"Governance config does not define {COLLECTION_ID}.")
    return config
