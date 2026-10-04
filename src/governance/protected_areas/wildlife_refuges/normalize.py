"""Keep refuge systems, status and source attributes distinct; infer no legal dates."""
from governance.shared.normalization import base_record, clean, records_frame

CANADIAN_TYPES = frozenset({'National Wildlife Area', 'Marine National Wildlife Area',
                          'Migratory Bird Sanctuary'})


def normalize(frame, source):
    if source.source_id not in {'fws_national_wildlife_refuges', 'eccc_wildlife_areas_sanctuaries'}:
        raise ValueError(f'Unsupported refuge source: {source.source_id}')
    us = source.source_id == 'fws_national_wildlife_refuges'
    rows = []
    seen = set()
    for _, row in frame.iterrows():
        kind = clean(row.get('RSL_TYPE' if us else 'TYPE_E'))
        if kind not in ({'NWR'} if us else CANADIAN_TYPES):
            continue
        oid = clean(row.get('OBJECTID'))
        if oid is None or oid in seen:
            raise ValueError('Unique snapshot OBJECTID required for refuge features')
        seen.add(oid)
        identity = f'{source.source_id}:{oid}'
        record = base_record(
            source, source_feature_id=identity, governance_feature_id=identity,
            feature_name=clean(row.get('ORGNAME' if us else 'NAME_E')),
            feature_type='wildlife_refuge_inventory_reference',
            authority=source.provider,
            jurisdiction='United States reference inventory' if us else 'Canada reference inventory',
            legal_authority=None, legal_source_url=None,
            source_coverage_status='partial_selected_refuge_systems',
        )
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None,
                      REFUGE_SYSTEM_TYPE=kind, geometry=row.geometry)
        for name, value in row.items():
            if name != frame.geometry.name:
                record[('FWS_' if us else 'ECCC_') + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)
