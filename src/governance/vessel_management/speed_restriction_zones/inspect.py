from governance.shared.layers import descriptor_for_collection
from governance.shared.config import DEFAULT_CONFIG_PATH

def layer_descriptors(config_path=DEFAULT_CONFIG_PATH):
    return [descriptor_for_collection('speed_restriction_zones', config_path)]
