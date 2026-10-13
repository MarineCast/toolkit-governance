"""Version-pinned TC instrument parser; excludes unresolved coast/border segments."""
from html.parser import HTMLParser
import re
import geopandas as gpd
from shapely.geometry import Polygon
from governance.shared.normalization import base_record, records_frame

class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.section=None;self.in_row=False;self.in_cell=False;self.cell='';self.cells=[];self.rows=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag=='h2':self.section=attributes.get('id')
        if tag=='tr':self.in_row=True;self.cells=[]
        if self.in_row and tag in {'td','th'}:self.in_cell=True;self.cell=''
        if self.in_cell and tag=='br':self.cell+=' '
    def handle_data(self,data):
        if self.in_cell:self.cell+=data
    def handle_endtag(self,tag):
        if tag in {'td','th'} and self.in_cell:self.cells.append(self.cell.strip());self.in_cell=False
        if tag=='tr' and self.in_row:self.rows.append((self.section,self.cells));self.in_row=False


def coordinate(value,axis):
    match=re.fullmatch(r'(\d{1,3})°(\d{1,2}(?:\.\d+)?)\s*[’\']([NSEW])',value)
    if not match or match[3] not in ('NS' if axis=='lat' else 'EW'):
        raise ValueError(f'TC coordinate schema drift: {value!r}')
    degrees,minutes=float(match[1]),float(match[2])
    if minutes>=60 or degrees+minutes/60>(90 if axis=='lat' else 180):raise ValueError('Invalid TC coordinate')
    return (degrees+minutes/60)*(-1 if match[3] in 'SW' else 1)


def source_frame(path):
    text=path.read_text()
    if '2026' not in text or 'June 1, 2026' not in text or 'November 30, 2026' not in text:
        raise ValueError('TC instrument version/date schema drift')
    parser=Tables();parser.feed(text)
    groups={};key=None
    for section,cells in parser.rows:
        if section not in {'schedule2','schedule3'}:continue
        if len(cells)==1:
            names={'1. Saturna Island':'saturna','2. Pender Island':'pender','1. Mouth of the Nitinat River':'nitinat','2. Swiftsure Bank':'swiftsure'}
            key=next((name for prefix,name in names.items() if cells[0].startswith(prefix)),None)
            if key is None:raise ValueError('TC fixed-zone heading schema drift')
            groups[key]={'section':section,'rows':[]}
        elif key is not None and len(cells)==4:
            groups[key]['rows'].append(cells)
    if set(groups)!={'saturna','pender','nitinat','swiftsure'}:
        raise ValueError('TC fixed-zone roster schema drift')
    rows=[]
    for key,item in groups.items():
        if key=='nitinat':
            if not any('along the coastline' in row[0] for row in item['rows']):
                raise ValueError('TC Nitinat support contract changed')
            continue
        coords=[]
        for instruction,lat,lon,label in item['rows']:
            if instruction not in {'beginning at','then to'}:
                raise ValueError('Unqualified TC boundary segment; no implicit closure or coastline')
            coords.append((coordinate(lon,'lon'),coordinate(lat,'lat')))
        if len(coords)<4 or coords[0]!=coords[-1]:raise ValueError('TC coordinate ring is not explicitly closed')
        polygon=Polygon(coords)
        if not polygon.is_valid:raise ValueError('TC coordinate ring is invalid; inspect instrument')
        rows.append({'TC_ZONE_ID':key,'TC_SCHEDULE':item['section'],'TC_COORDINATE_ROWS':item['rows'],'geometry':polygon})
    return gpd.GeoDataFrame(rows,crs=4326)


def normalize(frame,source,*,collection):
    rows=[]
    for _,row in frame.iterrows():
        exclusion=row.TC_SCHEDULE=='schedule2'
        if exclusion != (collection=='exclusion_zones'):continue
        clause='5-6' if exclusion else '7-8'
        record=base_record(source,source_feature_id=f'tc.2026:{row.TC_ZONE_ID}',governance_feature_id=f'tc.2026:{row.TC_ZONE_ID}',
            feature_name=row.TC_ZONE_ID.replace('_',' ').title(),feature_type='fixed_vessel_restriction_reference' if exclusion else 'fixed_speed_restriction_reference',
            authority=source.provider,jurisdiction='Southern British Columbia named instrument zones only',legal_authority='Canada Shipping Act 2001; 2026 interim order',
            legal_source_url=source.url,source_coverage_status='partial_named_instrument_closed_coordinate_rings')
        record.update(LEGAL_BINDING_STATUS='derived_reference_geometry',EFFECTIVE_START='2026-06-01',EFFECTIVE_END='2026-11-30',
            EFFECTIVE_DATE_PRECISION='day',EFFECTIVE_END_INCLUSIVE=True,INSTRUMENT_ID='tc.srkw.interim_order.2026',INSTRUMENT_VERSION='2026-05-22',
            RULE_CLAUSE=clause,ISSUING_AUTHORITY='Minister of Transport, Canada',APPLICABILITY='Vessels and persons operating vessels; instrument-specific exceptions apply',
            EXCEPTIONS='See sections 2, 5(2), 6(2)' if exclusion else 'See section 2; sections 7(2) and 8(2): vessels without motors',
            ORIGINAL_QUANTITY=None if exclusion else 10.,ORIGINAL_UNIT=None if exclusion else 'knots over ground',
            RESTRICTION_STATUS='instrument_version_reference_not_legal_currentness_certification',
            GEOMETRY_ROLE='closed_coordinate_ring_reference',TC_ZONE_ID=row.TC_ZONE_ID,
            TC_COORDINATE_ROWS=row.TC_COORDINATE_ROWS,
            UNIMPLEMENTED_SUPPORT='Nitinat coastline segment requires pinned authoritative coastline; approach rules require moving-animal context',geometry=row.geometry)
        rows.append(record)
    return records_frame(rows,frame.crs)
