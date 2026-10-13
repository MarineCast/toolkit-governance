"""DFO Pacific V3.1 subarea reference; hierarchy is not WDFW reporting equivalence."""
from uuid import UUID
from governance.shared.normalization import base_record, clean, records_frame


def positive_integer(value,field):
    try:
        if isinstance(value, bool):raise ValueError()
        number=int(value)
        if float(value)!=number or number<=0:raise ValueError()
        return str(number)
    except (TypeError,ValueError,OverflowError):
        raise ValueError(f'DFO PFMA {field} must be a positive integer') from None


def normalize(frame,source):
    declared_name = frame.attrs.get('layer_metadata', {}).get('name')
    if declared_name is not None and declared_name != 'DFO_BC_PFMA_SUBAREAS_50K_V3_1':
        raise ValueError('DFO Pacific layer/version schema drift')
    rows=[];seen=set()
    for _,row in frame.iterrows():
        oid=clean(row.get('OBJECTID'));globalid=clean(row.get('GLOBALID'))
        area=positive_integer(row.get('MGNT_AREA'),'MGNT_AREA')
        subarea=positive_integer(row.get('SUBAREA_'),'SUBAREA_')
        if oid is None or globalid is None or oid in seen:
            raise ValueError('DFO PFMA requires unique original OBJECTID and GLOBALID')
        try:UUID(globalid.strip('{}'))
        except ValueError:raise ValueError('DFO PFMA malformed GLOBALID') from None
        seen.add(oid)
        if row.geometry is None or row.geometry.geom_type not in {'Polygon','MultiPolygon'}:
            raise ValueError('DFO PFMA subarea requires polygon geometry')
        code=f'{area}-{subarea}'
        record=base_record(source,source_feature_id=f'{source.source_id}:{oid}',governance_feature_id=f'dfo.pacific.pfma.subarea:{code}',
            feature_name=clean(row.get('NAME')) or f'DFO Pacific subarea {code}',feature_type='pacific_fishery_management_subarea_reference',
            authority=source.provider,jurisdiction='DFO Pacific reference system; no legal-water jurisdiction inferred',
            legal_authority='Pacific Fishery Management Area Regulations 2007; source GIS is reference only',
            legal_source_url='https://www.pac.dfo-mpo.gc.ca/fm-gp/maps-cartes/areas-secteurs/index-eng.html',source_coverage_status='partial_dfo_pacific_subareas_reference')
        record.update(MANAGEMENT_SYSTEM='DFO Pacific Fishery Management subareas',AREA_SYSTEM_ID='dfo.pacific.pfma.subareas',
            AREA_HIERARCHY_LEVEL='subarea',PARENT_AREA_CODE=area,FISHERY_SECTOR='multi_fishery_reference_requires_applicability_review',
            AREA_CODE=code,AREA_TITLE=clean(row.get('NAME')),PROVIDER_GLOBAL_ID=globalid,
            SECTOR_APPLICABILITY='Area hierarchy reference only; fisheries, species, gear and orders require controlling instruments',
            GEOMETRY_VERSION='DFO_BC_PFMA_SUBAREAS_50K_V3_1',geometry=row.geometry)
        for field,value in row.items():
            if field != frame.geometry.name:record['DFO_PFMA_'+field]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)
