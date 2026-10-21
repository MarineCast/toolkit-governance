"""Historical port adapters remain importable; flat delivery belongs to Human."""


def retire_delivery(table, metadata):
    """Remove physical port derivatives, retaining original source bindings/bytes."""
    names = [name for name in table.column_names if name.startswith('ports__')]
    for name in names:
        metadata['fields'].pop(name, None)
    for name in list(metadata.get('coverage', {})):
        if name == 'ports' or name.startswith('ports__'):
            del metadata['coverage'][name]
    metadata.get('collections', {}).pop('ports', None)
    metadata['retired_collections'] = {**metadata.get('retired_collections', {}), 'ports': {
        'owner': 'toolkit-human', 'reason': 'Physical port source points are Human infrastructure',
        'original_lineage': 'Historical NGA original binding retained; validated Human native points preserve every previously delivered port ID and original point geometry'}}
    return table.drop(names)
