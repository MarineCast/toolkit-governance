"""Two-field regional reference interface on full closed native H3 cells."""
from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from types import SimpleNamespace

import geopandas as gpd
import h3
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from shapely.geometry import Polygon

from governance.jurisdiction.geographic_water import _original
from governance.memberships import MEMBERSHIP_TYPE, definition, prepare_records, memberships, validate_memberships
from .normalize import normalize

GROUP = 'county_regional_boundaries'
COUNT = GROUP + '__recorded_feature_count'
ASSIGNMENT = GROUP + '__feature_memberships_v1'
METHOD = 'regional-boundaries-closed-cell-intersection-1'
SOURCES = ('census_counties_2025', 'bc_abms_regional_districts')
SUPPORT = 'positive_partial_null_unknown_v1'
SCIENTIFIC_FEATURES = {
    COUNT: {'display_name': 'County / District Count'},
    ASSIGNMENT: {'display_name': 'County / District Assignment'},
}
LIMITATION = ('Recorded administrative reference polygons, not legal marine ownership or complete jurisdiction. '
              'Full closed native cell intersects retained original polygons, including edge/corner contact. '
              'All matching source-qualified county/district identities are retained; no dominant-area or nearest-shore assignment. '
              'Non-null values have partial inventory support; unmatched cells remain null, never inferred zero. '
              'BC Stikine unincorporated region and Northern Rockies Regional Municipality are not regional districts.')


def compact_features(table, fields, coverage):
    """Remove legacy diagnostics/status columns; retain paired count and assignment."""
    if COUNT not in table.column_names:
        return table
    removed = [name for name in table.column_names if name.startswith(GROUP + '__')
               and name not in SCIENTIFIC_FEATURES]
    table = table.drop(removed)
    for name in removed:
        fields.pop(name, None)
    fallback = fields.get(COUNT, {}).get('implicit_null_status', 'unknown')
    for name in SCIENTIFIC_FEATURES:
        fields[name].pop('missing_reason_field', None)
        fields[name].update(SCIENTIFIC_FEATURES[name], map_feature=True,
                            implicit_support=SUPPORT, implicit_null_status=fallback)
    fields[COUNT].update(units='count', nullable=True,
        definition='Count of distinct source-qualified counties / BC regional districts touched by the full closed native H3 cell. All matches count once, including edge/corner contacts.',
        coverage_reference=GROUP)
    fields[ASSIGNMENT].update(definition(GROUP))
    fields[ASSIGNMENT].pop('missing_reason_field')
    fields[ASSIGNMENT].update(SCIENTIFIC_FEATURES[ASSIGNMENT], map_feature=True,
        implicit_support=SUPPORT, implicit_null_status=fallback,
        definition='All county / BC regional district names and paired source IDs touched by the full closed native H3 cell, including edge/corner contacts.',
        missingness='Nonempty list and positive count: partial recorded inventory. Null: unknown or unavailable as declared by implicit_null_status. Zero and empty lists are unsupported.',
        category_semantics='Every matching original name and source-qualified identity; multiple matches remain paired, with no dominant-area assignment.')
    for name in SCIENTIFIC_FEATURES:
        fields[name]['interpretation'] = LIMITATION
    coverage.setdefault(GROUP, {}).update(metric_support_state='partial',
        support_encoding=SUPPORT, effect=LIMITATION)
    return table


@lru_cache(maxsize=4)
def _parts(path, checksum, source_id, bounds):
    raw = gpd.read_parquet(path)
    if raw.crs.to_epsg() != 4326:
        raise ValueError('Regional originals must use EPSG:4326')
    original = json.loads(pq.read_schema(path).metadata[b'governance_original'])['source']
    source = SimpleNamespace(**original, source_limitation=original.get('limitation'))
    selected = raw.loc[raw.geometry.intersects(shapely.box(*bounds))].copy()
    native = normalize(selected, source)
    rows, repaired_ids = [], []
    for _, row in native.iterrows():
        geometry = row.geometry
        if geometry is None or geometry.is_empty or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
            raise ValueError(f'Regional support requires original polygon geometry: {source_id}')
        if not geometry.is_valid:
            geometry = shapely.make_valid(geometry)
            repaired_ids.append(row.SOURCE_FEATURE_ID)
        for part in _polygon_parts(geometry):
            record = row.to_dict()
            record['geometry'] = part
            digest = hashlib.sha256(shapely.to_wkb(shapely.normalize(part))).hexdigest()[:24]
            record['GEOMETRY_PART_ID'] = f"{row.SOURCE_FEATURE_ID}:derived-polygon:{digest}"
            rows.append(record)
    if not rows:
        return (), (), {'source_rows': len(raw), 'selected_rows': len(native), 'parts': 0}
    native = gpd.GeoDataFrame(rows, crs=4326)
    return tuple(native.geometry), tuple(prepare_records(native)), {
        'source_rows': len(raw), 'selected_rows': len(selected), 'parts': len(native),
        'repaired_feature_ids': repaired_ids,
        'geometry_policy': 'Full original polygons; make_valid only for invalid polygons; retain only polygon-dimensional repair parts. OriginalData unchanged.'}


def _polygon_parts(geometry):
    if geometry.geom_type == 'Polygon':
        return [geometry] if not geometry.is_empty else []
    if geometry.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [part for child in geometry.geoms for part in _polygon_parts(child)]
    return []


def populate_features(table, metadata, original_root):
    """Replace only this family from checksum-bound original polygon sources."""
    if COUNT not in table.column_names:
        return table
    cells = table['h3_index'].to_pylist()
    grid = np.asarray([Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]) for cell in cells], dtype=object)
    bounds = tuple(shapely.total_bounds(grid))
    bindings, geometries, records, audit = {}, [], [], {}
    for source in SOURCES:
        binding = _original(original_root, metadata, source)
        if binding is None:
            continue
        geoms, paired, summary = _parts(str(binding[0]), binding[1], source, bounds)
        bindings[source] = copy.deepcopy(metadata['original_data'][source])
        geometries.extend(geoms); records.extend(paired); audit[source] = summary
    hits = [[] for _ in cells]
    if geometries:
        tree = shapely.STRtree(geometries)
        for start in range(0, len(cells), 4096):
            pairs = tree.query(grid[start:start + 4096], predicate='intersects')
            for cell_index, polygon_index in zip(*pairs):
                hits[start + int(cell_index)].append(int(polygon_index))
    rows = [memberships(records, indexes) if indexes else None for indexes in hits]
    values = {COUNT: pa.array([len(row) if row is not None else None for row in rows], type=pa.int64()),
              ASSIGNMENT: pa.array(rows, type=MEMBERSHIP_TYPE)}
    fields, coverage = metadata['fields'], metadata['coverage']
    for name, value in values.items():
        fields.setdefault(name, {}).update(implicit_null_status='unknown' if bindings else 'unavailable')
        if name in table.column_names:
            table = table.set_column(table.column_names.index(name), name, value)
        else:
            table = table.append_column(name, value)
    table = compact_features(table, fields, coverage)
    coverage[GROUP].update(metric_support_state='partial' if bindings else 'unavailable',
                          original_source_bindings=bindings, source_audit=audit,
                          gaps=[source for source in SOURCES if source not in bindings])
    for name in SCIENTIFIC_FEATURES:
        fields[name].update(scientific_method_version=METHOD, source_context={
            'original_source_bindings': bindings, 'source_audit': audit, 'limitation': LIMITATION})
    validate_memberships(table, fields)
    return table
