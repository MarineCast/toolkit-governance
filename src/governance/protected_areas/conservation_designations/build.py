from governance.shared.config import DEFAULT_CONFIG_PATH
from governance.shared.pipeline import build_collection
from .normalize import normalize

def build(config_path=DEFAULT_CONFIG_PATH, *, allow_partial=False, overwrite=False):
    return build_collection('conservation_designations', normalize, normalization_profile='eccc_reported_marine_classification', config_path=config_path, allow_partial=allow_partial, overwrite=overwrite)
