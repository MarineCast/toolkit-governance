from governance.shared.config import DEFAULT_CONFIG_PATH
from governance.shared.layers import descriptor_for_collection

def layer_descriptor(config_path=DEFAULT_CONFIG_PATH):
    return descriptor_for_collection('traffic_separation_schemes', config_path)
