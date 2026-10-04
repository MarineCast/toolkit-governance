from governance.shared.config import DEFAULT_CONFIG_PATH, load_governance_config
from governance.shared.acquisition import resolve_source_path, SourceUnavailableError

def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    config=load_governance_config(config_path)
    paths=[resolve_source_path(config.sources[s]) for s in config.collections['conservation_designations'].source_ids]
    if overwrite or any(p is None for p in paths):
        raise SourceUnavailableError('Provision explicitly bounded provider snapshots with complete ID rosters, rights and page-level receipts; see DATA_SOURCES.md. No implicit national download.')
    return paths
