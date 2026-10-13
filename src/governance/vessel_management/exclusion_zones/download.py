from governance.shared.pipeline import download_collection
from governance.shared.config import DEFAULT_CONFIG_PATH

def download(config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    return download_collection('exclusion_zones', config_path, overwrite=overwrite)
