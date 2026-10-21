"""One pinned, coordinate-defined USCG RNA; no inferred shoreline segments."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import geopandas as gpd
from shapely.geometry import Polygon

from governance.shared.normalization import base_record, records_frame

SOURCE_ID = 'uscg_lockheed_rna_20261015'
FEATURE_ID = 'us.cfr33.165.1336:a2'
PAIR = re.compile(r'(\d+)°(\d+)′\s*(\d+(?:\.\d+)?)″\s*N\s+(\d+)°(\d+)′\s*(\d+(?:\.\d+)?)″\s*W')


def source_frame(path):
    root = ET.fromstring(Path(path).read_bytes())
    if root.tag != 'DIV8' or root.get('N') != '165.1336':
        raise ValueError('USCG named-rule identity drift')
    paragraphs = [''.join(p.itertext()).strip() for p in root.findall('P')]
    boundary = [p for p in paragraphs if p.startswith('(2) All waters inside an area beginning at')]
    if len(boundary) != 1 or '[Datum: NAD 1983]' not in boundary[0] or 'shore' in boundary[0].lower():
        raise ValueError('USCG boundary needs reviewed datum/shoreline support')
    pairs = PAIR.findall(boundary[0])
    if len(pairs) != 4:
        raise ValueError('USCG four-corner boundary schema drift')
    coordinates = []
    for latd, latm, lats, lond, lonm, lons in pairs:
        parts = [float(v) for v in (latd, latm, lats, lond, lonm, lons)]
        if not (0 <= parts[0] <= 90 and 0 <= parts[3] <= 180 and all(0 <= parts[i] < 60 for i in (1, 2, 4, 5))):
            raise ValueError('Invalid USCG source coordinate')
        coordinates.append((-(parts[3]+parts[4]/60+parts[5]/3600), parts[0]+parts[1]/60+parts[2]/3600))
    polygon = Polygon(coordinates)
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError('Invalid USCG area; no automatic repair')
    # The rule defines waters "inside an area" by four successive corners. Closing
    # its final edge is the bounded-area interpretation; no coastline is inserted.
    frame = gpd.GeoDataFrame([{'ZONE_ID': FEATURE_ID, 'BOUNDARY_TEXT': boundary[0],
        'SOURCE_DATUM': 'NAD83 (EPSG:4269)', 'SOURCE_COORDINATES': pairs,
        'RULE_TEXT': '\n'.join(paragraphs), 'geometry': polygon}], crs=4269)
    frame = frame.to_crs(4326)
    frame.attrs['geometry_derivation'] = 'Four source corners in NAD83 transformed to EPSG:4326; closing final edge of explicitly defined inside-area; no coastline support'
    frame.attrs['excluded_scope'] = '165.1336(a)(1), Pacific Sound Resources: unresolved shoreline closure; all other Part 165 areas outside this named source'
    return frame


def normalize(frame, source):
    rows = []
    for _, row in frame.iterrows():
        if row.ZONE_ID != FEATURE_ID or 'NAD83' not in row.SOURCE_DATUM:
            raise ValueError('Unqualified USCG feature/datum')
        record = base_record(source, source_feature_id=FEATURE_ID, governance_feature_id=FEATURE_ID,
            feature_name='Lockheed Shipyard', feature_type='regulated_navigation_area_seabed_restriction',
            authority='United States Coast Guard', jurisdiction='United States; Washington',
            legal_authority='33 CFR 165.1336(a)(2), (b), (c)',
            legal_source_url='https://www.ecfr.gov/on/2026-10-15/title-33/section-165.1336',
            source_coverage_status='partial_one_named_coordinate_area')
        record.update(COUNTRY='United States', EXCLUSION_CATEGORY='seabed_disturbance_restriction',
            PROHIBITED_ACTIVITY='Seabed disturbance, including anchoring, dragging, trawling and spudding',
            PERMITTED_ACTIVITY='Transit and navigation otherwise permitted',
            RESTRICTION_STATUS='mandatory_rule_reference_subject_to_exceptions',
            ACTIVATION_CONDITION='Standing rule reference; no real-time enforcement/currentness determination',
            TEMPORAL_KIND='standing_rule_reference_unknown_effective_interval',
            RULE_CLAUSE='33 CFR 165.1336(a)(2), (b)(1)-(3), (c)',
            EXCEPTIONS='Remediation with EPA advance notice to COTP; source preserves Muckleshoot/Suquamish treaty fishing provisions; COTP waiver may apply. See full rule.',
            SOURCE_BOUNDARY_TEXT=row.BOUNDARY_TEXT, SOURCE_DATUM=row.SOURCE_DATUM,
            SOURCE_RULE_TEXT=row.RULE_TEXT, geometry=row.geometry)
        rows.append(record)
    return records_frame(rows, frame.crs)
