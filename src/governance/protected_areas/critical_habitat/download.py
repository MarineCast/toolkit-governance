"""Explicit critical-habitat acquisition requires separately budgeted source snapshots."""
from governance.shared.config import load_governance_config,DEFAULT_CONFIG_PATH
from governance.shared.acquisition import resolve_source_path,SourceUnavailableError


def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    config=load_governance_config(config_path)
    paths=[resolve_source_path(config.sources[s]) for s in config.collections['critical_habitat'].source_ids]
    if overwrite or any(p is None for p in paths):
        raise SourceUnavailableError('Critical-habitat network acquisition needs an explicit bounded request plan. Provision ArcGIS snapshot_schema_version=1 inputs, retaining query extent/count and provider metadata; do not download the national line layer implicitly.')
    return paths
