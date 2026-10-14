"""Retain NOAA NMFS proposed/designated entity-specific reference geometry."""
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


def normalize(frame,source):
    rows=[]
    for _,row in frame.iterrows():
        identity=clean(row.get('OBJECTID'))
        if identity is None:raise ValueError('NOAA critical-habitat OBJECTID required')
        record=base_record(source,source_feature_id=f'{source.source_id}:{identity}',governance_feature_id=f'{source.source_id}:{identity}',
            feature_name=clean(row.get('LISTENTITY')) or clean(row.get('COMNAME')),feature_type='critical_habitat_inventory_reference',
            authority='NOAA National Marine Fisheries Service',jurisdiction='United States reference inventory',
            legal_authority=clean(row.get('ECFR')),legal_source_url=clean(row.get('ECFR')),source_coverage_status='partial_nmfs_only')
        record.update(EFFECTIVE_START=effective_date(frame, row.get('EFFECTDATE')),geometry=row.geometry)
        for name,value in row.items():
            if name!='geometry':record['NOAA_'+name]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)
