"""One WG active-area diagram, explicitly separate from the larger WG envelope."""
from pathlib import Path
import hashlib,re
import geopandas as gpd
from shapely.geometry import Polygon

SOURCE_ID='dnd_wg_active_reference_20261020'
FEATURE_ID='ca.dnd.notmar35:wg_active'
DOCUMENT_SHA256='508f18f9573a9dde66f0150feca9edce939c81367560a629b04d79121ce425e8'
DIAGRAM_SHA256='fe66fddfa12d61053bedb37ff663e52a29ef82822ad40142256fee38b7a14817'
# Transcribed A–E from the pinned official NOTMAR hazardous-area diagram and
# checked against Navy Nanoose practices section 8-1 (May 2025). Not WG's
# different four-point operations/airspace envelope in the Notice 35 table.
COORDINATES=[[-(124+7.70/60),49+21.35/60],[-(123+48.40/60),49+21/60],
 [-(123+48.40/60),49+14.38/60],[-(124+0.90/60),49+16.75/60],[-(124+7.70/60),49+19.35/60]]

def source_frame(path):
 path=Path(path);raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DOCUMENT_SHA256:raise ValueError('NOTMAR source-version drift')
 image=path.with_name('notmar-wg-active.jpg')
 if not image.exists() or hashlib.sha256(image.read_bytes()).hexdigest()!=DIAGRAM_SHA256:
  raise ValueError('Pinned NOTMAR active-area diagram companion missing or changed; acquire and qualify it explicitly')
 text=re.sub(r'<[^>]+>',' ',raw.decode())
 text=' '.join(text.replace('&nbsp;',' ').split())
 if not all(x in text for x in ['North American Datum 1983','vessels are required to remain clear whenever WG is active','secf-not35-img16-en.jpg' if False else 'Area WG constitutes']):
  raise ValueError('NOTMAR datum/mandatory activity evidence missing')
 p=Polygon(COORDINATES)
 if not p.is_valid or p.area<=0:raise ValueError('Invalid WG active-area ring')
 f=gpd.GeoDataFrame([dict(ZONE_ID=FEATURE_ID,SOURCE_DATUM='NAD83 (EPSG:4269); NOTMAR 35 explanatory note 5(b)',
  SOURCE_COORDINATES=COORDINATES,SOURCE_DOCUMENT_SHA256=DOCUMENT_SHA256,SOURCE_DIAGRAM_SHA256=DIAGRAM_SHA256,
  BOUNDARY_TEXT='Official hazardous-area diagram points A–B–C–D–E–A; 0.01 arc-minute printed precision; larger four-corner WG operations/airspace envelope is excluded',
  RULE_TEXT='NOTMAR 35 explanatory notes 5(b), 7 and WG hazardous-area notice: vessels required to remain clear whenever WG is active; entry requires specific Winchelsea Control authorization. Schedule generally daylight Monday–Saturday is not an activation record.',
  geometry=p)],crs=4269).to_crs(4326)
 f.attrs.update(geometry_derivation='Five manually transcribed/visually checked official diagram corners in NAD83 transformed to EPSG:4326; polygon closed along drawn E–A edge; native source precision retained',
  excluded_scope='Larger WG operations envelope, other practice areas, no-anchor zone, harbour shorelines and vessel-relative buffers not included')
 return f
