from governance.shared.config import DEFAULT_CONFIG_PATH
from governance.shared.layers import descriptor_for_collection

def layer_descriptor(config_path=DEFAULT_CONFIG_PATH):
    return descriptor_for_collection('conservation_designations', config_path)


def layer_descriptors(config_path=DEFAULT_CONFIG_PATH):
    from .normalize import metric_groups
    return [descriptor_for_collection('conservation_designations', config_path, layer_id=prefix,
                display_name=group['description'],
                filters=((group['role_field'], group['role']), ('SOURCE_DATASET_ID', group['source_id'])))
            for prefix, group in metric_groups().items()]
