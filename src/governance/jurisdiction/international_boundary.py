"""Actual international line intersections, independent of country-water assignment.

Use retained full source lines without snapping or polygon perimeter extraction.
Closed native H3 cells include shared-edge and vertex contacts. A missing hit is
unknown unless an explicit, source/grid-bound geographic inventory acceptance
certifies absence; a complete download receipt alone never does that.
"""
from __future__ import annotations
from functools import lru_cache
from types import SimpleNamespace
import copy
import hashlib
import json
import geopandas as gpd
import h3
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from shapely.geometry import Polygon
from governance.memberships import MEMBERSHIP_TYPE, definition, prepare_records, memberships, validate_memberships
from governance.jurisdiction.geographic_water import _original
from governance.jurisdiction.international_boundaries.normalize import normalize

METHOD = 'international-boundary-intersection-1'
COLUMN = GROUP = 'federal_waters__international_boundary'
MEMBERS = GROUP + '__feature_memberships_v1'
COUNT = GROUP + '__recorded_feature_count'
SOURCES = ('international_boundary_commission_v1_3', 'noaa_us_maritime_limits', 'nrcan_canadian_geopolitical_boundaries_lines')
FILTERS = {
    SOURCES[0]: 'Commission international boundary sections; original line geometry only',
    SOURCES[1]: 'RULEID in (1, 4, 5): international land boundary, international maritime boundary with EEZ, international maritime boundary; exclude RULEID 2/3/7/8 and all other limits',
    SOURCES[2]: 'TYPE_E=INTERN only; exclude provincial, EEZ, territorial and other limit lines',
}
LIMITATION = ('True means the full cell intersects a retained mapped international border line, including edge or corner contact. '
              'False requires verified complete geographic line support. Current sources are partial: no-hit cells remain unknown. '
              'This is boundary presence, separate from the International water-assignment category; mapping reference only, not legal authority.')


def select_lines(frame, source_id):
    """Use source boundary classes, never names, coastlines or EEZ perimeters."""
    if source_id == SOURCES[1]:
        selected = frame.loc[frame['RULEID'].isin([1, 4, 5])].copy()
    elif source_id == SOURCES[2]:
        selected = frame.loc[frame['TYPE_E'].eq('INTERN')].copy()
    elif source_id == SOURCES[0]:
        selected = frame.copy()
    else:
        raise ValueError('Unsupported international line source')
    identity = {SOURCES[0]:'SectionNum', SOURCES[1]:'BOUND_ID', SOURCES[2]:'UUID'}[source_id]
    if identity not in selected.columns or selected[identity].isna().any() or selected[identity].astype(str).str.strip().eq('').any():
        raise ValueError('International boundary requires stable original source identifiers')
    if selected.crs.to_epsg() != 4326 or any(g is None or g.is_empty or not g.is_valid or g.geom_type not in ('LineString', 'MultiLineString') for g in selected.geometry):
        raise ValueError('International boundary support requires valid EPSG:4326 lines')
    return selected


@lru_cache(maxsize=6)
def _lines(path, checksum, source_id):
    # Path/checksum identity was verified before this cache is consulted.
    raw = gpd.read_parquet(path)
    original = json.loads(pq.read_schema(path).metadata[b'governance_original'])['source']
    source = SimpleNamespace(**original, source_limitation=original.get('limitation'))
    selected = select_lines(raw, source_id)
    native = normalize(selected, source)
    rows = []
    for _, row in native.iterrows():
        for part in shapely.get_parts(row.geometry):
            record = row.to_dict()
            record['geometry'] = part
            # Full-original parts differ from the older clipped native parts.
            # Their digest IDs remain stable across grids, row order and reruns.
            digest = hashlib.sha256(shapely.to_wkb(shapely.normalize(part))).hexdigest()[:24]
            record['GEOMETRY_PART_ID'] = f"{row.SOURCE_FEATURE_ID}:original-line:{digest}"
            rows.append(record)
    if not rows:
        return (), (), {'source_rows':len(raw), 'selected_rows':len(selected), 'line_parts':0}
    native = gpd.GeoDataFrame(rows, crs=4326)
    return tuple(native.geometry), tuple(prepare_records(native)), {'source_rows':len(raw), 'selected_rows':len(selected), 'line_parts':len(native)}


def _complete(coverage, cells, bindings):
    """Only explicit accepted geographic support for these exact bytes/grid."""
    q = coverage.get('geographic_inventory_coverage', {})
    grid_hash = hashlib.sha256(json.dumps(sorted(cells), separators=(',', ':')).encode()).hexdigest()
    return (q.get('status') == 'complete' and q.get('scope') == 'full_supplied_cells'
            and q.get('inventory') == 'actual_international_boundary_lines'
            and isinstance(q.get('evidence'), str) and bool(q['evidence'].strip())
            and q.get('original_source_bindings') == bindings and set(bindings) == set(SOURCES)
            and q.get('h3_indexes_sha256') == grid_hash)


def populate_features(table, metadata, original_root):
    """Add six boundary/support columns, leaving all existing columns intact."""
    if not any(name.startswith('federal_waters__') for name in table.column_names):
        return table
    bindings, geometries, records, audit = {}, [], [], {}
    for source in SOURCES:
        binding = _original(original_root, metadata, source)
        if binding is None:
            continue
        geoms, paired, counts = _lines(str(binding[0]), binding[1], source)
        bindings[source] = copy.deepcopy(metadata['original_data'][source])
        geometries.extend(geoms); records.extend(paired); audit[source] = counts
    cells = table['h3_index'].to_pylist()
    qualified = _complete(metadata.get('coverage', {}).get(GROUP, {}), cells, bindings)
    hits = [[] for _ in cells]
    if geometries:
        tree = shapely.STRtree(geometries)
        for start in range(0, len(cells), 4096):
            grid = np.asarray([Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]) for cell in cells[start:start+4096]], dtype=object)
            pairs = tree.query(grid, predicate='intersects')
            for cell_index, line_index in zip(*pairs):
                hits[start+int(cell_index)].append(int(line_index))
    rows = [memberships(records, indexes) if indexes else [] if qualified else None for indexes in hits]
    states = [('observed' if qualified else 'partial') if row else 'observed' if row == [] else 'unknown' if bindings else 'unavailable' for row in rows]
    values = {COLUMN:pa.array([None if row is None else bool(row) for row in rows], pa.bool_()),
              COLUMN+'_status':pa.array(states), MEMBERS:pa.array(rows, MEMBERSHIP_TYPE), MEMBERS+'_status':pa.array(states),
              COUNT:pa.array([None if row is None else len(row) for row in rows],pa.int64()), COUNT+'_status':pa.array(states)}
    for name, value in values.items():
        table = table.set_column(table.column_names.index(name), name, value) if name in table.column_names else table.append_column(name, value)
    fields = metadata['fields']
    meaning = LIMITATION + ' All independently published matching line records remain paired, without averaging or selecting a dominant source.'
    fields[COLUMN] = {'units':'1', 'nullable':True, 'definition':meaning, 'display_name':'International Boundary',
                      'value_semantics':'boolean_overlap', 'map_feature':True, 'missing_reason_field':COLUMN+'_status',
                      'coverage_reference':GROUP, 'support_membership_column':MEMBERS, 'support_limitation':LIMITATION,
                      'scientific_method_version':METHOD, 'original_source_bindings':bindings}
    fields[MEMBERS] = {**definition(GROUP), 'definition':'All actual international boundary lines with any nonempty closed-cell intersection, including shared edges and vertices',
                       'map_feature':False, 'original_source_bindings':bindings,
                       'geometry_lineage':'Original source IDs and names; original-line part IDs hash normalized full original line parts, independent of clipping, grid and row order'}
    fields[COUNT] = {'units':'count', 'nullable':True, 'definition':'Supporting distinct mapped international boundary feature count, not a selectable feature',
                    'map_feature':False, 'missing_reason_field':COUNT+'_status', 'coverage_reference':GROUP}
    for name in (COLUMN, MEMBERS, COUNT):
        fields[name+'_status'] = {'units':None,'nullable':False,'definition':'International line support: partial hits, unknown no-hit; observed false requires accepted complete geographic support',
                                 'map_feature':False,'enum':['observed','unknown','unavailable','not_applicable','partial']}
    prior = metadata.get('coverage', {}).get(GROUP, {}).get('geographic_inventory_coverage')
    metadata.setdefault('coverage', {})[GROUP] = {'method':METHOD, 'definition':meaning, 'source_filters':FILTERS,
        'source_selection_audit':audit, 'original_source_bindings':bindings,
        'intersection_policy':'Nonempty topological intersection of EPSG:4326 full closed H3 cell and original line; shared edges and vertex-only contacts included; no buffering, snapping or water-polygon perimeter extraction',
        'geographic_inventory_coverage':prior if qualified else {'status':'partial' if bindings else 'unavailable',
            'meaning':'Source receipt/roster completeness does not establish exhaustive geographic border support'},
        'legal_status':'mapping_reference_only', 'support_limitation':LIMITATION}
    validate_memberships(table, fields)
    return table
