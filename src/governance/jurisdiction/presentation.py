"""Administrative presentation only; source/legal reference types stay distinct."""
FAMILY_KEY = 'administrative_boundaries'
FAMILY_NAME = 'Administrative Boundaries'
COLLECTIONS = ('county_regional_boundaries', 'federal_waters', 'state_provincial_waters', 'tribal_first_nations_areas')


def annotate_fields(fields):
    for name, field in fields.items():
        if name.startswith(tuple(collection+'__' for collection in COLLECTIONS)):
            field['display_family'] = FAMILY_NAME


def annotate_catalog(catalog):
    present = [name for name in COLLECTIONS if name in catalog.get('areas', {})]
    if not present:
        return
    catalog.setdefault('feature_families', {})[FAMILY_KEY] = {
        'display_name': FAMILY_NAME, 'source_collections': present,
        'interpretation': 'Presentation grouping only. Regional/state/country assignments and international boundary retain their existing definitions. BIA land areas and NRCan reserve administrative geometry remain distinct references, not traditional territories or blanket sovereignty claims.'}
    for name in present:
        catalog['areas'][name]['presentation_family'] = FAMILY_KEY
