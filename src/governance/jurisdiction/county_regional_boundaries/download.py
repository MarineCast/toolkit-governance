"""Explicitly bounded, checksum-pinned Census archive acquisition."""
from governance.shared.acquisition import download_direct_snapshot
from governance.shared.config import DEFAULT_CONFIG_PATH, load_governance_config


def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    config = load_governance_config(config_path)
    return [download_direct_snapshot(config.sources[source_id], overwrite=overwrite,
                                     max_bytes=100_000_000)
            for source_id in config.collections['county_regional_boundaries'].source_ids]
