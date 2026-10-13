"""ADF&G groundfish statistical reporting system; no equivalence to WDFW recreation."""
from governance.shared.normalization import base_record, clean, records_frame, source_date


def normalize(frame,source):
    rows=[];seen=set()
    for _,row in frame.iterrows():
        oid=clean(row.get('OBJECTID'));code=clean(row.get('STAT_AREA'))
        if oid is None or code is None or oid in seen:
            raise ValueError('Unique ADFG OBJECTID and STAT_AREA required')
        seen.add(oid)
        if row.geometry is None or row.geometry.geom_type not in {'Polygon','MultiPolygon'}:
            raise ValueError('ADF&G groundfish statistical areas require polygons')
        # Provider codes are integer six-digit area numbers; never remove leading zeros.
        try:
            number=int(code)
            if str(number)!=code or not 100000<=number<=999999:raise ValueError()
        except ValueError:
            raise ValueError(f'ADFG STAT_AREA must be a six-digit integer code: {code!r}') from None
        record=base_record(source,source_feature_id=f'{source.source_id}:{oid}',governance_feature_id=f'adfg.groundfish.statistical:{code}',
            feature_name=f'ADF&G groundfish statistical area {code}',feature_type='groundfish_statistical_reporting_area',authority=source.provider,
            jurisdiction='Alaska provider reporting system; not legal water jurisdiction',legal_authority=None,legal_source_url=None,source_coverage_status='partial_adfg_groundfish_reporting_only')
        record.update(LEGAL_AUTHORITY=None,LEGAL_SOURCE_URL=None,MANAGEMENT_SYSTEM='ADF&G groundfish statistical reporting',
            AREA_SYSTEM_ID='adfg.groundfish.statistical',AREA_HIERARCHY_LEVEL='statistical_area',PARENT_AREA_CODE=None,
            FISHERY_SECTOR='commercial_reporting',AREA_CODE=code,AREA_TITLE=clean(row.get('REGISTRATION_AREA_NAME')),
            SECTOR_APPLICABILITY='groundfish reporting; shellfish applicability requires provider region qualification',
            GEOMETRY_VERSION=source.source_as_of,
            GEOMETRY_VALID_FROM=source_date(frame,'GEOMETRY_START_DATE',row.get('GEOMETRY_START_DATE'),arcgis_date=True),
            GEOMETRY_VALID_TO=source_date(frame,'GEOMETRY_END_DATE',row.get('GEOMETRY_END_DATE'),arcgis_date=True),geometry=row.geometry)
        for field,value in row.items():
            if field != frame.geometry.name:record['ADFG_'+field]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)
