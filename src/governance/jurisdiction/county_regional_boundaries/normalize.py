"""Preserve Census county and BC ABMS regional district identities."""
import re

from governance.shared.normalization import base_record, clean, records_frame


def normalize(frame, source):
    if source.source_id == 'bc_abms_regional_districts':
        return _districts(frame, source)
    if source.source_id != 'census_counties_2025':
        raise ValueError(f'Unsupported county source: {source.source_id}')
    rows = []
    seen = set()
    for _, row in frame.iterrows():
        geoid = clean(row.get('GEOID'))
        if geoid is None or not re.fullmatch(r'\d{5}', geoid) or geoid in seen:
            raise ValueError('Unique five-digit Census GEOID required; retain leading zeros')
        seen.add(geoid)
        identity = f'{source.source_id}:{geoid}'
        record = base_record(
            source, source_feature_id=identity, governance_feature_id=identity,
            feature_name=clean(row.get('NAMELSAD')) or clean(row.get('NAME')),
            feature_type='county_equivalent_statistical_reference',
            authority=source.provider, jurisdiction='United States cartographic reference',
            legal_authority=None, legal_source_url=None,
            source_coverage_status='partial_us_only_reference_inventory',
        )
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None,
                      LEGAL_BINDING_STATUS='non_binding_cartographic_reference',
                      geometry=row.geometry)
        for name, value in row.items():
            if name != frame.geometry.name:
                record['CENSUS_' + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)


def _districts(frame, source):
    rows, seen = [], set()
    for _, row in frame.iterrows():
        identifier = clean(row.get('LGL_ADMIN_AREA_ID'))
        name = clean(row.get('ADMIN_AREA_NAME'))
        if identifier is None or not re.fullmatch(r'\d+', identifier) or identifier in seen or not name:
            raise ValueError('Unique BC LGL_ADMIN_AREA_ID and ADMIN_AREA_NAME required')
        seen.add(identifier)
        if identifier == '361' and name == 'Stikine Region (Unincorporated)':
            continue  # Published in ABMS, but not a regional district.
        identity = f'{source.source_id}:{identifier}'
        record = base_record(
            source, source_feature_id=identity, governance_feature_id=identity,
            feature_name=name, feature_type='regional_district_administrative_reference',
            authority=source.provider, jurisdiction='British Columbia administrative reference',
            legal_authority=None, legal_source_url=None,
            source_coverage_status='partial_regional_reference_inventory',
        )
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None,
                      LEGAL_BINDING_STATUS='non_binding_cartographic_reference',
                      REGION='British Columbia', geometry=row.geometry)
        for key, value in row.items():
            if key != frame.geometry.name:
                record['BC_ABMS_' + key] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)
