"""Distinct Coast Guard administrative references, not operational jurisdiction."""
from governance.shared.normalization import base_record, clean, records_frame

SOURCES = {
    'uscg_app_sectors': ('uscg_sector', 'FID', 'NAME', 'USCG sector reference', 'USCG_'),
    'ccg_western_region': ('ccg_administrative_region', 'OBJECTID_1', 'Name', 'CCG administrative region reference; not a U.S. sector', 'CCG_'),
}


def normalize(frame, source):
    if source.source_id not in SOURCES:
        raise ValueError(f'Unsupported Coast Guard source: {source.source_id}')
    role, id_field, name_field, description, prefix = SOURCES[source.source_id]
    rows, seen = [], set()
    for _, row in frame.iterrows():
        oid = clean(row.get(id_field))
        if oid is None or oid in seen:
            raise ValueError('Unique original Coast Guard source ID required')
        seen.add(oid)
        if row.geometry is None or row.geometry.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError('Coast Guard reference requires polygon geometry')
        identity = f'{source.source_id}:{oid}'
        record = base_record(source, source_feature_id=identity, governance_feature_id=identity,
            feature_name=clean(row.get(name_field)), feature_type='coast_guard_administrative_reference',
            authority=source.provider, jurisdiction=None, legal_authority=None, legal_source_url=None,
            source_coverage_status='partial_app_grid_selected_administrative_units')
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None, ADMIN_UNIT_ROLE=role,
                      ADMIN_UNIT_DESCRIPTION=description, geometry=row.geometry)
        for name, value in row.items():
            if name != frame.geometry.name:
                record[prefix + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)


def metric_groups(collection='coast_guard_sectors'):
    return {f'{collection}__{spec[0]}': {'collection': collection, 'role': spec[0],
            'role_field': 'ADMIN_UNIT_ROLE', 'source_id': source, 'description': spec[3],
            'geometry_family': 'polygon', 'identity': 'Distinct source administrative unit IDs; not precise operational or sovereign jurisdiction.',
            'overlap_policy': 'Union within this agency/unit-type group only. USCG sectors and CCG administrative regions are not equivalent units and must not be summed as unique jurisdiction or operational coverage.'}
            for source, spec in SOURCES.items()}
