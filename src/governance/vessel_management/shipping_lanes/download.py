from governance.shared.config import DEFAULT_CONFIG_PATH
from governance.vessel_management.routing import download as download_routing

def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    return download_routing('shipping_lanes', config_path, overwrite=overwrite)
