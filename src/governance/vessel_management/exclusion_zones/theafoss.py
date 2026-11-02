"""Only the two self-contained four-corner areas; shoreline areas stay unselected."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import geopandas as gpd
from shapely.geometry import Polygon
from .washington import PAIR

def source_frame(path):
 root=ET.fromstring(Path(path).read_bytes())
 matches=[e for e in root.iter('DIV8') if e.get('N')=='165.1329']
 if len(matches)!=1:raise ValueError('Named Thea Foss rule identity drift')
 paragraphs=[''.join(p.itertext()).strip() for p in matches[0].findall('P')]
 rows=[]
 for number in (1,2):
  boundary=[p for p in paragraphs if p.startswith(f'({number}) All waters of the Thea Foss Waterway bounded by a line connecting')]
  if len(boundary)!=1 or '[Datum: NAD 1983]'not in boundary[0] or 'shore'in boundary[0].lower():raise ValueError('Thea Foss boundary needs review')
  text=boundary[0].replace('N,','N ')
  pairs=PAIR.findall(text)
  if len(pairs)!=4:raise ValueError('Thea Foss four-corner schema drift')
  coords=[]
  for a,b,c,d,e,f in pairs:
   a,b,c,d,e,f=map(float,(a,b,c,d,e,f))
   if not (0<=a<=90 and 0<=d<=180 and all(0<=x<60 for x in (b,c,e,f))):raise ValueError('Invalid source coordinate')
   coords.append((-(d+e/60+f/3600),a+b/60+c/3600))
  shape=Polygon(coords)
  if not shape.is_valid or shape.area<=0:raise ValueError('Invalid source ring')
  rows.append(dict(ZONE_ID=f'us.cfr33.165.1329:a{number}',RULE_CLAUSE=f'(a)({number}); (b), (c)',SOURCE_DATUM='NAD83 (EPSG:4269)',BOUNDARY_TEXT=boundary[0],RULE_TEXT='\n'.join(paragraphs),SOURCE_COORDINATES=pairs,geometry=shape))
 return gpd.GeoDataFrame(rows,crs=4269).to_crs(4326)
