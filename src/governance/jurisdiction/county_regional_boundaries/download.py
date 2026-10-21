"""Explicit bounded Census archive and BC district snapshot acquisition."""
from governance.shared.acquisition import download_direct_snapshot, download_arcgis_snapshot, AcquisitionBudget
from governance.shared.config import DEFAULT_CONFIG_PATH, load_governance_config


def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    config = load_governance_config(config_path)
    paths = []
    for source_id in config.collections['county_regional_boundaries'].source_ids:
        source = config.sources[source_id]
        if source_id == 'bc_abms_regional_districts':
            paths.append(download_arcgis_snapshot(source, bbox=config.bbox_tuple, overwrite=overwrite,
                         budget=AcquisitionBudget(max_bytes=64_000_000, max_features=100, max_pages=100)))
        else:
            paths.append(download_direct_snapshot(source, overwrite=overwrite, max_bytes=100_000_000))
    return paths
