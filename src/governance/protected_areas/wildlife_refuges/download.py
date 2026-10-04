"""Require an explicitly bounded and filtered official refuge snapshot."""
from governance.shared.acquisition import SourceUnavailableError, resolve_source_path
from governance.shared.config import DEFAULT_CONFIG_PATH, load_governance_config


def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    config = load_governance_config(config_path)
    paths = [resolve_source_path(config.sources[source_id])
             for source_id in config.collections['wildlife_refuges'].source_ids]
    if overwrite or any(path is None for path in paths):
        raise SourceUnavailableError(
            'Refuge acquisition requires explicitly budgeted, filtered FWS/ECCC snapshots. '
            'Provision snapshot_schema_version=1 inputs with metadata, query extent, '
            'selection predicate, complete object-ID roster and retrieval time; see DATA_SOURCES.md.'
        )
    return paths
