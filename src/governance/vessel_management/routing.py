"""Typed routing components; source/chart identity is distinct from legal applicability."""
from pathlib import Path
import geopandas as gpd
from governance.shared.normalization import base_record, clean, records_frame
from governance.shared.config import DEFAULT_CONFIG_PATH, load_governance_config
from governance.shared.acquisition import resolve_source_path, SourceUnavailableError

# Verified CHS service renderer and linked provider dictionary; NOAA archive routeType.
# role -> (family, source ID, raw type, description, geometry family)
ROLES = {
    'chs_separation_line': ('traffic_separation_schemes', 'chs_routing_layer_2', 'TSELNE_L', 'CHS traffic separation line', 'line'),
    'chs_scheme_boundary': ('traffic_separation_schemes', 'chs_routing_layer_2', 'TSSBND_L', 'CHS traffic separation scheme outer boundary', 'line'),
    'chs_separation_zone': ('traffic_separation_schemes', 'chs_routing_layer_3', 'TSEZNE_A', 'CHS traffic separation zone', 'polygon'),
    'chs_scheme_crossing': ('traffic_separation_schemes', 'chs_routing_layer_3', 'TSSCRS_A', 'CHS traffic separation scheme crossing', 'polygon'),
    'chs_lane_part': ('traffic_separation_schemes', 'chs_routing_layer_4', 'TSSLPT_A', 'CHS traffic separation scheme lane part', 'polygon'),
    'chs_recommended_lane_part': ('shipping_lanes', 'chs_routing_layer_4', 'RCTLPT_A', 'CHS recommended traffic lane part', 'polygon'),
    'chs_two_way_route_part': ('shipping_lanes', 'chs_routing_layer_4', 'TWRTPT_A', 'CHS two-way route part', 'polygon'),
    'chs_navigation_line': ('shipping_lanes', 'chs_routing_layer_5', 'NAVLNE_L', 'CHS navigation line; not a traffic lane', 'line'),
    'chs_recommended_centerline': ('shipping_lanes', 'chs_routing_layer_5', 'RCRTCL_L', 'CHS recommended route centerline; undefined width', 'line'),
    'chs_recommended_track': ('shipping_lanes', 'chs_routing_layer_5', 'RECTRC_L', 'CHS track recommended to all or certain vessels', 'line'),
    'noaa_traffic_lane': ('traffic_separation_schemes', 'noaa_routing_2026', 'Traffic Lane', 'NOAA 2026 traffic lane reference', 'polygon'),
    'noaa_separation_zone': ('traffic_separation_schemes', 'noaa_routing_2026', 'Separation Zone', 'NOAA 2026 separation zone reference', 'polygon'),
    'noaa_fairway': ('shipping_lanes', 'noaa_routing_2026', 'Fairway', 'NOAA 2026 fairway reference', 'polygon'),
    'noaa_two_way_route': ('shipping_lanes', 'noaa_routing_2026', 'Two-Way Route', 'NOAA 2026 two-way route reference', 'polygon'),
    'noaa_recommended_route': ('shipping_lanes', 'noaa_routing_2026', 'Recommended Route', 'NOAA 2026 recommended route reference', 'polygon'),
}
NOAA_EXCLUDED_TYPES = {'Area To Be Avoided', 'Precautionary Area', 'Particularly Sensitive Sea Area'}


def noaa_source_frame(archive):
    """Read the selected 2026 GPKG with its original FID, never a row-order identity."""
    frame = gpd.read_file(f'/vsizip/{Path(archive).resolve()}/VesselRoutingMeasure.gpkg', fid_as_index=True)
    frame['SOURCE_FID'] = frame.index.astype(str)
    return frame.reset_index(drop=True)


def normalize(frame, source, *, collection):
    rows, seen = [], set()
    supported_sources = {spec[1] for spec in ROLES.values()}
    if source.source_id not in supported_sources:
        raise ValueError(f'Unsupported routing source: {source.source_id}')
    chs = source.source_id.startswith('chs_')
    source_roles = {spec[2]: (role, spec) for role, spec in ROLES.items() if spec[1] == source.source_id}
    for _, row in frame.iterrows():
        kind = clean(row.get('MERGE_SRC' if chs else 'routeType'))
        if not chs and kind in NOAA_EXCLUDED_TYPES:
            continue
        if kind not in source_roles:
            raise ValueError(f'Unrecognized routing type for {source.source_id}: {kind}')
        role, spec = source_roles[kind]
        if spec[0] != collection:
            continue
        if row.geometry is None or row.geometry.geom_type not in ({'LineString', 'MultiLineString'} if spec[4] == 'line' else {'Polygon', 'MultiPolygon'}):
            raise ValueError(f'Routing geometry/type mismatch: {role}')
        oid = clean(row.get('OBJECTID' if chs else 'SOURCE_FID'))
        if oid is None or oid in seen:
            raise ValueError('Unique source OBJECTID/FID required')
        seen.add(oid)
        record_id = f'{source.source_id}:{oid}'
        lnam = clean(row.get('LNAM')) if chs else None
        identity = f'chs:{kind}:{lnam}' if lnam else record_id
        record = base_record(source, source_feature_id=record_id, governance_feature_id=identity,
            feature_name=clean(row.get('OBJNAM' if chs else 'location')) or spec[3],
            feature_type='routing_component_reference', authority=source.provider,
            jurisdiction='Published source coverage; no jurisdiction inferred',
            legal_authority=None, legal_source_url=None, source_coverage_status='partial_selected_routing_inventory')
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None, ROUTING_ROLE=role,
                      ROUTING_SOURCE_TYPE=kind, ROUTING_IDENTITY_METHOD='CHS object LNAM within type; chart records retained' if lnam else 'snapshot source record ID; no logical route equivalence inferred',
                      geometry=row.geometry)
        for name, value in row.items():
            if name != frame.geometry.name:
                record[('CHS_' if chs else 'NOAA_ROUTING_') + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)


def metric_groups(collection):
    return {f'{collection}__{role}': {'collection': collection, 'role': role, 'source_id': spec[1],
            'description': spec[3], 'geometry_family': spec[4],
            'identity': 'Distinct source object IDs (CHS LNAM where present); not unique whole schemes or physical routes. Native source-record IDs and chart relationships retained.'}
            for role, spec in ROLES.items() if spec[0] == collection}


def download(collection, config_path=DEFAULT_CONFIG_PATH, *, overwrite=False):
    config = load_governance_config(config_path)
    paths = [resolve_source_path(config.sources[s]) for s in config.collections[collection].source_ids]
    if overwrite or any(path is None for path in paths):
        raise SourceUnavailableError('Routing acquisition requires explicitly budgeted CHS AOI snapshots and the separately pinned NOAA2026 archive/FID-preserving source frame; see routing DATA_SOURCES.md. Do not substitute the older live NOAA service.')
    return paths
