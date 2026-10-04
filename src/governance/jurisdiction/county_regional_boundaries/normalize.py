"""Preserve Census county identifiers; do not infer legal or Canadian coverage."""
import re

from governance.shared.normalization import base_record, clean, records_frame


def normalize(frame, source):
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
