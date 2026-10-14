"""ODFW published KML reference; original records, multipart boundaries and holes."""
import io
import zipfile
from xml.etree import ElementTree as ET
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from governance.shared.normalization import base_record, clean, records_frame

NS = {'k':'http://www.opengis.net/kml/2.2'}


def source_frame(path):
    with zipfile.ZipFile(path) as archive:
        name = 'OregonMarineReserves_KMZ_GoogleEarth.kmz'
        info = archive.getinfo(name)
        if info.file_size > 4_000_000:
            raise ValueError('ODFW compressed member exceeds byte budget')
        with zipfile.ZipFile(io.BytesIO(archive.read(name))) as kmz:
            if kmz.getinfo('doc.kml').file_size > 4_000_000:
                raise ValueError('ODFW KML exceeds byte budget')
            content=kmz.read('doc.kml')
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        raise ValueError('Unsupported KML entity declarations')
    rows=[];seen=set()
    root=ET.fromstring(content)
    for item in root.findall('.//k:Placemark',NS):
        identity=item.attrib.get('id');name=item.findtext('k:name',namespaces=NS)
        if not identity or identity in seen or not name:
            raise ValueError('ODFW schema drift: original placemark IDs/names required')
        seen.add(identity)
        parts=[]
        def ring(element):
            if element is None or not element.text:
                raise ValueError('Missing ODFW polygon coordinates')
            coordinates=[tuple(map(float,coordinate.split(',')[:2])) for coordinate in element.text.split()]
            if len(coordinates)<4 or coordinates[0]!=coordinates[-1]:
                raise ValueError('ODFW polygon ring is not explicitly closed')
            return coordinates
        for polygon in item.findall('.//k:Polygon',NS):
            exterior=ring(polygon.find('k:outerBoundaryIs/k:LinearRing/k:coordinates',NS))
            holes=[ring(hole) for hole in polygon.findall('k:innerBoundaryIs/k:LinearRing/k:coordinates',NS)]
            parts.append(Polygon(exterior,holes))
        if not parts:
            raise ValueError('ODFW source contains a nonpolygon placemark')
        rows.append({'ODFW_RECORD_ID':identity,'ODFW_NAME':name,'ODFW_DESCRIPTION':item.findtext('k:description',namespaces=NS),
                     'geometry':parts[0] if len(parts)==1 else MultiPolygon(parts)})
    if not rows:
        raise ValueError('ODFW published source roster unexpectedly empty')
    return gpd.GeoDataFrame(rows,crs=4326)


def normalize(frame,source):
    rows=[]
    for _,row in frame.iterrows():
        identity=clean(row.get('ODFW_RECORD_ID'));name=clean(row.get('ODFW_NAME'))
        if not identity or not name:
            raise ValueError('ODFW source ID/name required')
        kind='marine_reserve' if 'Marine Reserve' in name else 'seabird_protection_area' if 'Seabird' in name else 'marine_protected_area'
        record=base_record(source,source_feature_id=f'{source.source_id}:{identity}',governance_feature_id=f'odfw_reference:{identity}',
            feature_name=name,feature_type='odfw_published_protected_boundary_reference',authority=source.provider,
            jurisdiction='Oregon',legal_authority='OAR 635-012; OAR 141-142; OAR 736-029',legal_source_url='https://oregonmarinereserves.com/rules/',source_coverage_status='partial_published_oregon_reference')
        record.update(SOURCE_RECORD_ID=identity,DESIGNATION_ID=f'USA:ODFW_KML:{identity}',AUTHORITY_ID='USA:ODFW',COUNTRY_CODE='USA',
            DESIGNATION_STATUS='active_reference_inventory',EFFECTIVE_STATUS='source_listing_not_current_instrument_verification',
            MPA_PROGRAM='Oregon Marine Reserves and MPAs',MAP_GROUP='oregon_published_reference',MANAGEMENT_AUTHORITY=source.provider,
            GOVERNING_RULE_STATUS='consult_controlling_oregon_administrative_rules',SOURCE_DESIGNATION_TYPE=kind,
            SOURCE_ZONE_NAME=name,SOURCE_MARINE_AREA_KM2=None,SOURCE_TOTAL_SITE_AREA_KM2=None,SOURCE_AREA_KM2=None,
            ESTABLISHMENT_YEAR=None,ESTABLISHMENT_DATE_PRECISION='unknown',
            MPA_QC_REASON='Published 2016 KML is a reference representation; current OARs and source agency verification control.',
            ODFW_DESCRIPTION=row.get('ODFW_DESCRIPTION'),geometry=row.geometry)
        rows.append(record)
    return records_frame(rows,frame.crs)
