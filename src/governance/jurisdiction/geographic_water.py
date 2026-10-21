"""Geographic water assignment from retained polygons; no legal jurisdiction inference.

Countries use existing positive-area country-water memberships. WA/OR use explicit
Census STATEFP attributes intersected with U.S. water support. BC uses the retained
water polygon's explicit AREA=BRITISH_COLUMBIA. No nearest-coast extension or
high-seas complement is generated. Every original diagnostic remains unchanged.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import copy
import geopandas as gpd
import h3
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from shapely.geometry import Polygon
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition, validate_memberships
from governance.jurisdiction.water_assignments import FAMILIES, assignment_group, normalize_country, scientific_features

METHOD = 'geographic-water-assignment-1'
WATER = 'seascape_territorial_water_support'
COUNTIES = 'census_counties_2025'
COUNTRY_COLUMN = 'international_boundaries__feature_memberships_v1'
STATES = {'53': ('WA', 'Washington (WA)'), '41': ('OR', 'Oregon (OR)')}
LIMITATIONS = {
    'state_provincial_waters': 'Geographic model-water assignment: WA/OR administrative polygons clipped to U.S. water support; BC from the explicit British Columbia water region. Not legal marine ownership. Unmatched support remains unknown; no offshore extension.',
    'federal_waters': 'Geographic country assignment from retained model-water polygons; not federal administrative waters, EEZ or legal jurisdiction. International is not established by these sources; unmatched support remains unknown.',
}


def _hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _original(root, metadata, source):
    binding = metadata.get('original_data', {}).get(source)
    if not binding:
        return None
    path = (Path(root) / binding['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()) or binding['path'] != f'OriginalData/{source}/geometry.parquet' or _hash(path) != binding['sha256']:
        raise ValueError(f'Geographic assignment original binding mismatch: {source}')
    original = json.loads(pq.read_schema(path).metadata[b'governance_original'])
    if original['source']['source_id'] != source:
        raise ValueError('Geographic assignment source identity mismatch')
    return path, binding['sha256']


def _paired(record):
    return tuple(record[k] for k in RECORD_FIELDS)


def _merge(entries):
    grouped = {}
    for entry in entries:
        records = grouped.setdefault(entry['feature_id'], {})
        for record in entry['records']:
            records.setdefault(_paired(record), set()).update(record['geometry_part_ids'])
    return [{'feature_id': feature, 'records': [dict(zip(RECORD_FIELDS, key), geometry_part_ids=sorted(parts))
            for key, parts in sorted(records.items(), key=lambda item: json.dumps(item[0], ensure_ascii=True))]}
            for feature, records in sorted(grouped.items())]


def _record(**values):
    record = dict.fromkeys(RECORD_FIELDS)
    record.update(values)
    return record


@lru_cache(maxsize=2)
def _support(water_path, water_hash, county_path, county_hash):
    """Prepare retained full source pieces once across both native resolutions."""
    water = gpd.read_parquet(water_path)
    if water.crs.to_epsg() != 4326:
        raise ValueError('Water originals require EPSG:4326')
    counts, bc_ids, us = {}, set(), []
    for _, row in water.iterrows():
        country = normalize_country(row.get('NAME'))
        if country is None:
            continue
        counts[country] = counts.get(country, 0) + 1
        source_id = f"{WATER}:{country}:{counts[country]:02d}"
        if str(row.get('TYPE')).upper() != 'TERRITORIAL':
            continue
        if country == 'CAN' and row.get('AREA') == 'BRITISH_COLUMBIA':
            bc_ids.add(source_id)
        if country == 'USA' and row.get('AREA') == 'CONTIGUOUS':
            us.append((source_id, row.geometry))
    if not county_path or not us:
        return tuple(bc_ids), (), ()
    county = gpd.read_parquet(county_path, filters=[('STATEFP', 'in', list(STATES))])
    if county.crs.to_epsg() != 4326 or county.GEOID.duplicated().any():
        raise ValueError('County originals require EPSG:4326 and unique source GEOID')
    # Bound the large country source to the full WA/OR admin envelope, never to
    # cell centers or nearest coastline. The resulting pieces are grid-independent.
    bounds = shapely.box(*county.total_bounds)
    geoms, descriptors = [], []
    projected = county.to_crs(6933)
    for water_id, geometry in us:
        clipped = shapely.intersection(geometry, bounds)
        mask = gpd.GeoSeries([clipped], crs=4326).to_crs(6933).iloc[0]
        parts = shapely.intersection(projected.geometry.to_numpy(), mask)
        for (_, row), part in zip(projected.iterrows(), parts):
            if part.is_empty or part.area <= 0:
                continue
            code, title = STATES[row.STATEFP]
            geoid = str(row.GEOID)
            source_feature = f'{COUNTIES}:{geoid}'
            digest = hashlib.sha256(shapely.to_wkb(shapely.normalize(part))).hexdigest()[:24]
            record = _record(source_dataset_id=COUNTIES, source_feature_id=source_feature,
                feature_name=str(row.get('NAMELSAD') or row.get('NAME')), feature_type='geographic_state_water_polygon',
                authority='U.S. Census Bureau', jurisdiction='USA', region=code,
                area_system_id='geographic_state_province_water', area_code=code, area_title=title,
                geometry_part_ids=[f'{source_feature}:water:{water_id}:{digest}'])
            geoms.append(part)
            descriptors.append((code, water_id, record))
    return tuple(sorted(bc_ids)), tuple(geoms), tuple(descriptors)


def _country_memberships(table):
    rows = []
    for row in table[COUNTRY_COLUMN].to_pylist():
        entries = []
        for entry in row or []:
            records = []
            for record in entry['records']:
                if record['source_dataset_id'] == WATER and record['feature_type'] == 'country_water_reference_polygon' and normalize_country(record['jurisdiction']):
                    records.append(dict(record, feature_type='geographic_country_water_polygon'))
            if records:
                entries.append(dict(entry, records=records))
        rows.append(_merge(entries) or None)
    return rows


def _us_memberships(cells, pieces, descriptors, country_rows):
    result = [[] for _ in cells]
    if not pieces:
        return result
    grid = gpd.GeoSeries([Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]) for cell in cells], crs=4326).to_crs(6933)
    tree = shapely.STRtree(pieces)
    # Bounded vector chunks keep intersections temporary; full positive area in
    # EPSG:6933 is the criterion, including tiny/border-crossing memberships.
    for start in range(0, len(cells), 4096):
        local = grid.iloc[start:start + 4096].to_numpy()
        pairs = tree.query(local, predicate='intersects')
        if not pairs.size:
            continue
        intersections = shapely.intersection(local[pairs[0]], np.asarray(pieces, dtype=object)[pairs[1]])
        for cell_local, piece_index, intersection in zip(pairs[0], pairs[1], intersections):
            if intersection.is_empty or intersection.area <= 0:
                continue
            i = start + int(cell_local)
            code, water_id, county_record = descriptors[int(piece_index)]
            # Preserve both input lineages. A county-water piece requires the
            # corresponding retained country polygon membership in this full cell.
            support = [r for e in country_rows[i] or [] for r in e['records'] if r['source_feature_id'] == water_id]
            if not support:
                raise ValueError('County-water intersection lacks corresponding country source support')
            records = [county_record, *[dict(r, feature_type='geographic_state_water_polygon', region=code,
                area_system_id='geographic_state_province_water', area_code=code, area_title=STATES['53' if code == 'WA' else '41'][1]) for r in support]]
            result[i].append({'feature_id': f'geographic_state_province:USA:{code}', 'records': records})
    return result


def populate_features(table, metadata, original_root):
    """Reproduce only the two geographic assignment groups from retained originals.

    Used by normal export/build and narrow current-product updates. Source bytes,
    all other columns and original source-native memberships remain untouched.
    """
    if COUNTRY_COLUMN not in table.column_names or not any(assignment_group(f) + '__feature_memberships_v1' in table.column_names for f in FAMILIES):
        return table
    water = _original(original_root, metadata, WATER)
    if water is None:
        return table
    county = _original(original_root, metadata, COUNTIES)
    validate_memberships(table, metadata['fields'])
    bc_ids, pieces, descriptors = _support(str(water[0]), water[1], str(county[0]) if county else None, county[1] if county else None)
    countries = _country_memberships(table)
    states = _us_memberships(table['h3_index'].to_pylist(), pieces, descriptors, countries)
    for i, entries in enumerate(countries):
        for entry in entries or []:
            records = [dict(r, feature_type='geographic_province_water_polygon', region='BC',
                area_system_id='geographic_state_province_water', area_code='BC', area_title='British Columbia (BC)')
                for r in entry['records'] if r['source_feature_id'] in bc_ids]
            if records:
                states[i].append({'feature_id': 'geographic_state_province:CAN:BC', 'records': records})
    states = [_merge(entries) or None for entries in states]
    fields, coverage = metadata['fields'], metadata['coverage']
    for family, rows in [('state_provincial_waters', states), ('federal_waters', countries)]:
        used_sources = [WATER, COUNTIES] if family == 'state_provincial_waters' else [WATER]
        bindings = {source: copy.deepcopy(metadata['original_data'][source]) for source in used_sources if source in metadata['original_data']}
        group = assignment_group(family)
        column, count = group + '__feature_memberships_v1', group + '__recorded_feature_count'
        if column not in table.column_names:
            continue
        statuses = ['partial' if row else 'unknown' for row in rows]
        values = {column: pa.array(rows, MEMBERSHIP_TYPE), count: pa.array([len(row) if row else None for row in rows], pa.int64()),
                  column + '_status': pa.array(statuses), count + '_status': pa.array(statuses)}
        for name, array in values.items():
            table = table.set_column(table.column_names.index(name), name, array)
        meaning = (LIMITATIONS[family] + ' Membership means any positive-area overlap of the full native H3 cell with supported water geometry. '
                   'All geographic assignments and paired source IDs/names/parts are retained; no dominant assignment, nearest-land classification or high-seas complement. '
                   'Unknown and verified no-assignment are distinct; this partial source inventory does not certify absence.')
        fields[column] = {**definition(group), **scientific_features(family)[column], 'definition': meaning,
                          'map_feature': True, 'categorical_assignment': family, 'assignment_semantics': 'geographic',
                          'category_labels': FAMILIES[family]['categories'], 'support_limitation': LIMITATIONS[family],
                          'scientific_method_version': METHOD, 'original_source_bindings': bindings,
                          'category_semantics': 'Geographic derived categories. WA/OR REGION comes from explicit Census STATEFP 53/41; BC REGION comes from the retained water polygon AREA=BRITISH_COLUMBIA. Country records preserve the native country label. Original input attributes remain in OriginalData and original family memberships.',
                          'geometry_lineage': 'Country/water-source part IDs are retained. County-water piece IDs combine original county GEOID, original water source ID and the normalized EPSG:6933 derived geometry digest. New state feature IDs group explicit source region codes; all paired original source record IDs and names remain attached.'}
        fields[count].update(definition='Supporting count of distinct geographic assignment feature IDs; not a count of source counties or regulatory jurisdictions')
        coverage[group] = {'method': METHOD, 'definition': meaning, 'original_source_bindings': bindings,
            'geographic_inventory_coverage': {'status': 'partial', 'numerator': None, 'denominator': None,
                'meaning': 'Geographic modeling support only; no exhaustive legal water coverage or verified high-seas support'},
            'classification': 'geographic_admin_and_explicit_water_region' if family == 'state_provincial_waters' else 'geographic_country_water_support',
            'international_support': 'unavailable; never inferred as complement',
            'overlap_policy': 'Retain every positive-area assignment; full cells can cross states/countries', 'support_limitation': LIMITATIONS[family]}
    validate_memberships(table, fields)
    return table
