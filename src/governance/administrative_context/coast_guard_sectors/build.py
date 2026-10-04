from governance.shared.config import DEFAULT_CONFIG_PATH
from governance.shared.pipeline import build_collection
from .normalize import normalize

def build(config_path=DEFAULT_CONFIG_PATH, *, allow_partial=False, overwrite=False):
    return build_collection('coast_guard_sectors', normalize, normalization_profile='distinct_coast_guard_administrative_reference', config_path=config_path, allow_partial=allow_partial, overwrite=overwrite)
