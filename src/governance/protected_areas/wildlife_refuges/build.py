from governance.shared.pipeline import build_collection
from governance.shared.config import DEFAULT_CONFIG_PATH
from .normalize import normalize


def build(config_path=DEFAULT_CONFIG_PATH, *, allow_partial=False, overwrite=False):
    return build_collection('wildlife_refuges', normalize,
                            normalization_profile='fws_eccc_selected_refuge_reference',
                            config_path=config_path, allow_partial=allow_partial, overwrite=overwrite)
