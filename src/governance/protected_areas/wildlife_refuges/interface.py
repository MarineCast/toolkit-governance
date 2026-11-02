"""Selected scientific interface; retained source and support fields are unchanged."""

SCIENTIFIC_FEATURES = {
    'wildlife_refuges__recorded_feature_count': {'display_name': 'Wildlife Refuge Count'},
    'wildlife_refuges__feature_memberships_v1': {'display_name': 'Wildlife Refuge Assignment'},
    'wildlife_refuges__recorded_polygon_union_area_fraction': {
        'display_name': 'Wildlife Refuge Coverage', 'display_unit': '%', 'display_scale': 100,
    },
}


def annotate_fields(fields):
    """Keep exactly three map choices; retain all other columns as support."""
    for name, field in fields.items():
        if name.startswith('wildlife_refuges__'):
            field.update(map_feature=name in SCIENTIFIC_FEATURES)
            field.update(SCIENTIFIC_FEATURES.get(name, {}))
