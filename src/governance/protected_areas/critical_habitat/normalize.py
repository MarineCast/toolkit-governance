"""Retain source-specific NOAA NMFS and DFO aquatic habitat reference geometry."""
from datetime import datetime
import re
from governance.shared.normalization import base_record, records_frame, clean, source_date


def effective_date(frame, value):
    """Decode this NOAA string field's qualified formats; retain generic date guards."""
    fields = {f['name'].casefold(): f.get('type') for f in frame.attrs.get('layer_metadata', {}).get('fields', [])}
    declared = fields.get('effectdate')
    if isinstance(value, str) and declared in (None, 'esriFieldTypeString'):
        value = value.strip()
        if not value:
            return None
        for pattern, format_ in ((r'\d{2}/\d{2}/\d{4}', '%m/%d/%Y'),
                                 (r'\d{8}', '%Y%m%d')):
            if re.fullmatch(pattern, value):
                return datetime.strptime(value, format_).date().isoformat()
    return source_date(frame, 'EFFECTDATE', value, arcgis_date=True)


def normalize_dfo(frame, source):
    rows=[]
    for values in frame.itertuples(index=False, name=None):
        row=dict(zip(frame.columns,values));identity=clean(row.get('OBJECTID'))
        if row['geometry'] is None or row['geometry'].geom_type not in ('Polygon', 'MultiPolygon'):
            raise ValueError('DFO critical habitat requires provider polygon geometry')
        if identity is None: raise ValueError('DFO critical-habitat OBJECTID required')
        common=clean(row.get('COMMON_E'));population=clean(row.get('POP_E'))
        name=(common + ' [' + population + ']') if common and population else common
        record=base_record(source,source_feature_id=f'{source.source_id}:{identity}',governance_feature_id=f'{source.source_id}:{identity}',
            feature_name=name,feature_type='aquatic_critical_habitat_inventory_reference',authority='Fisheries and Oceans Canada',
            jurisdiction='Canada',legal_authority='Species at Risk Act; recovery documents and action plans',
            legal_source_url=clean(row.get('PROFILE_E')),source_coverage_status='partial_dfo_aquatic_only')
        record.update(REGION=clean(row.get('LEAD_REG_E')),AREA_SYSTEM_ID='Canada SARA aquatic critical habitat',AREA_CODE=identity,
                      AREA_TITLE=clean(row.get('Waterbody')),AREA_HIERARCHY_LEVEL=clean(row.get('CH_STATUS_E')),geometry=row['geometry'])
        for field,value in row.items():
            if field!='geometry': record['DFO_'+field]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)


def normalize(frame,source):
    from .eccc import SOURCE, normalize_eccc
    if source.source_id == SOURCE:
        return normalize_eccc(frame,source)
    if source.source_id == 'dfo_aquatic_critical_habitat':
        return normalize_dfo(frame,source)
    rows=[]
    # Pandas row Series deep-copy frame attrs, including the complete ID/receipt
    # roster. Tuple rows keep that evidence on the original frame without O(n²)
    # copying for large, fully acquired habitat inventories.
    for values in frame.itertuples(index=False, name=None):
        row=dict(zip(frame.columns,values))
        identity=clean(row.get('OBJECTID'))
        if identity is None:raise ValueError('NOAA critical-habitat OBJECTID required')
        record=base_record(source,source_feature_id=f'{source.source_id}:{identity}',governance_feature_id=f'{source.source_id}:{identity}',
            feature_name=clean(row.get('LISTENTITY')) or clean(row.get('COMNAME')),feature_type='critical_habitat_inventory_reference',
            authority='NOAA National Marine Fisheries Service',jurisdiction='United States reference inventory',
            legal_authority=clean(row.get('ECFR')),legal_source_url=clean(row.get('ECFR')),source_coverage_status='partial_nmfs_only')
        record.update(EFFECTIVE_START=effective_date(frame, row.get('EFFECTDATE')),geometry=row['geometry'])
        for name,value in row.items():
            if name!='geometry':record['NOAA_'+name]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)
