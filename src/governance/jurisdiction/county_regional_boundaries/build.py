from governance.shared.pipeline import build_collection
from governance.shared.config import DEFAULT_CONFIG_PATH
from .normalize import normalize


def build(config_path=DEFAULT_CONFIG_PATH, *, allow_partial=False, overwrite=False):
    return build_collection('county_regional_boundaries', normalize,
                            normalization_profile='county_bc_regional_reference',
                            config_path=config_path, allow_partial=allow_partial, overwrite=overwrite)
