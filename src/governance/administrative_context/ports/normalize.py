"""NGA World Port Index physical point references, never port jurisdiction polygons."""
import re
import geopandas as gpd
from shapely.geometry import Point
from governance.shared.normalization import base_record, records_frame, clean


def coordinate(value, *, latitude):
    match=re.fullmatch(r'''\s*(\d{1,3})°(\d{1,2})['′](\d{1,2}(?:\.\d+)?)["″]([NSEW])\s*''',str(value))
    if not match: raise ValueError(f'Unsupported NGA coordinate: {value!r}')
    degrees,minutes,seconds,direction=match.groups()
    degrees,minutes,seconds=float(degrees),float(minutes),float(seconds)
    if minutes>60 or (minutes==60 and seconds!=0) or seconds>=60 or direction not in ('NS' if latitude else 'EW'):
        raise ValueError('Invalid NGA coordinate components')
    result=degrees+minutes/60+seconds/3600
    if result>(90 if latitude else 180):raise ValueError('NGA coordinate outside WGS84')
    return -result if direction in 'SW' else result


def source_frame(payload):
    rows=[]; ids=set()
    for item in payload['ports']:
        identity=str(item['portNumber'])
        if identity in ids:raise ValueError('Duplicate NGA port identity')
        ids.add(identity)
        rows.append({**item,'coordinate_conversion':'DMS arithmetic; exactly 60 minutes with zero seconds carries one degree; original strings retained','geometry':Point(coordinate(item['longitude'],latitude=False),coordinate(item['latitude'],latitude=True))})
    return gpd.GeoDataFrame(rows,geometry='geometry',crs=4326)


def normalize(frame,source):
    rows=[]
    for _,row in frame.iterrows():
        identity=str(row.portNumber)
        record=base_record(source,source_feature_id=identity,governance_feature_id='nga_wpi:'+identity,
            feature_name=clean(row.portName),feature_type='published_port_location_point',authority='NGA World Port Index',
            jurisdiction=None,legal_authority=None,legal_source_url=None,source_coverage_status='partial_published_port_inventory')
        record.update(LEGAL_AUTHORITY=None,LEGAL_SOURCE_URL=None,LEGAL_BINDING_STATUS='non_binding_physical_reference',
                      geometry=row.geometry)
        for name,value in row.items():
            if name!='geometry':record['NGA_'+name]=clean(value)
        rows.append(record)
    return records_frame(rows,frame.crs)
