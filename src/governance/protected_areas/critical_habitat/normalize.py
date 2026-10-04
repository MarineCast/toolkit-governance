"""Retain NOAA NMFS proposed/designated entity-specific reference geometry."""
from governance.shared.normalization import base_record, records_frame, clean, date_value


def normalize(frame,source):
    rows=[]
    for _,row in frame.iterrows():
        identity=clean(row.get('OBJECTID'))
        if identity is None:raise ValueError('NOAA critical-habitat OBJECTID required')
        record=base_record(source,source_feature_id=f'{source.source_id}:{identity}',governance_feature_id=f'{source.source_id}:{identity}',
            feature_name=clean(row.get('LISTENTITY')) or clean(row.get('COMNAME')),feature_type='critical_habitat_inventory_reference',
            authority='NOAA National Marine Fisheries Service',jurisdiction='United States reference inventory',
            legal_authority=clean(row.get('ECFR')),legal_source_url=clean(row.get('ECFR')),source_coverage_status='partial_nmfs_only')
        record.update(EFFECTIVE_START=date_value(row.get('EFFECTDATE')),geometry=row.geometry)
        for name,value in row.items():
            if name!='geometry':record['NOAA_'+name]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)
