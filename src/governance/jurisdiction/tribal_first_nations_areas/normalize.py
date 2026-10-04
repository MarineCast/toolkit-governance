"""Official provider administrative inventories, never territory or jurisdiction proof."""
from governance.shared.normalization import base_record, clean, records_frame

SOURCES = {
    'bia_administrative_lar': ('bia_land_area_reference', 'LARID', 'LARNAME', 'BIA_', 'BIA land-area reference; includes source-specific land classes, not a sovereignty extent'),
    'nrcan_indian_reserves': ('nrcan_indian_reserve_reference', 'adminAreaId', 'adminAreaNameEng', 'NRCAN_', 'NRCan reported Indian Reserve administrative reference; not traditional territory'),
}


def normalize(frame, source):
    if source.source_id not in SOURCES:
        raise ValueError(f'Unsupported administrative source: {source.source_id}')
    role, area_field, name_field, prefix, description = SOURCES[source.source_id]
    rows, seen = [], set()
    for _, row in frame.iterrows():
        oid, area = clean(row.get('OBJECTID')), clean(row.get(area_field))
        if oid is None or area is None or oid in seen:
            raise ValueError('Unique original record IDs and provider area identities required')
        seen.add(oid)
        if row.geometry is None or row.geometry.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError('Administrative reference requires polygon geometry')
        if source.source_id == 'nrcan_indian_reserves' and (
            clean(row.get('distributionTypeEng')) != 'Indian Reserve'
            or clean(row.get('jurisdictionEng')) != 'British Columbia'
        ):
            raise ValueError('Qualified NRCan scope is British Columbia Indian Reserve records only')
        record = base_record(source, source_feature_id=f'{source.source_id}:record:{oid}',
            governance_feature_id=f'{source.source_id}:area:{area}',
            feature_name=clean(row.get(name_field)), feature_type='provider_administrative_reference',
            authority=source.provider, jurisdiction=None, legal_authority=None, legal_source_url=None,
            source_coverage_status='partial_app_grid_selected_administrative_inventory')
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None, ADMIN_REFERENCE_ROLE=role,
            ADMIN_REFERENCE_DESCRIPTION=description, PROVIDER_AREA_ID=area, geometry=row.geometry)
        for name, value in row.items():
            if name != frame.geometry.name:
                record[prefix + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)


def metric_groups(collection='tribal_first_nations_areas'):
    return {f'{collection}__{spec[0]}': {'collection': collection, 'role': spec[0],
            'role_field': 'ADMIN_REFERENCE_ROLE', 'source_id': source, 'description': spec[4],
            'geometry_family': 'polygon',
            'identity': 'Distinct provider area identifiers, not a count of Tribes, Nations, rights holders or sovereign jurisdictions. Original source records and geometry-part relations remain available.',
            'overlap_policy': 'Union within this provider/system only. BIA land-area and NRCan Indian Reserve inventories are different concepts; never pool as unique territory, sovereignty, land title, fishing entitlement or complete administrative coverage.'}
            for source, spec in SOURCES.items()}
