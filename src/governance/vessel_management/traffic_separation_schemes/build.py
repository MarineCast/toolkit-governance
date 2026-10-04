from governance.shared.config import DEFAULT_CONFIG_PATH
from governance.shared.pipeline import build_collection
from .normalize import normalize

def build(config_path=DEFAULT_CONFIG_PATH, *, allow_partial=False, overwrite=False):
    return build_collection('traffic_separation_schemes', normalize, normalization_profile='typed_chs_noaa_routing_reference', config_path=config_path, allow_partial=allow_partial, overwrite=overwrite)
