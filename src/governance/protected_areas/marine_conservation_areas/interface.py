"""Marine conservation sites from retained inventories; no legal equivalence inferred.

The four source collections remain acquisition/provenance owners. Their legacy
arrays remain hidden compatibility/support records. The public map interface is
one site assignment, unique-site count and full-cell union coverage.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import re

import geopandas as gpd
import h3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from shapely.geometry import Polygon

from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition, validate_memberships

GROUP = 'marine_conservation_areas'
REFERENCE = 'proposed_interim_conservation_references'
LEGACY = ('marine_protected_areas', 'conservation_designations', 'wildlife_refuges', 'national_marine_sanctuaries')
METHOD = 'marine-conservation-sites-1'
COUNT = GROUP + '__recorded_feature_count'
ASSIGNMENT = GROUP + '__feature_memberships_v1'
COVERAGE = GROUP + '__recorded_polygon_union_area_fraction'
SCIENTIFIC_FEATURES = {
    ASSIGNMENT: {'display_name': 'Marine Conservation Area Assignment'},
    COUNT: {'display_name': 'Marine Conservation Area Count'},
    COVERAGE: {'display_name': 'Marine Conservation Area Coverage', 'display_unit': '%', 'display_scale': 100},
}
NOAA = 'noaa_mpa_inventory_2023'
ECCC = ('eccc_marine_classification', 'eccc_wildlife_areas_sanctuaries')
FWS = 'fws_national_wildlife_refuges'
DFO = 'dfo_oceans_act_marine_protected_areas'
AOI = 'dfo_oceans_act_areas_of_interest'
ODFW = 'odfw_marine_reserves_2016'
# Reviewed explicit provider-ID pairs, not a name-based matching algorithm.
# Confirmation requires matching agency/site class and whole-site polygon IoU >= .60.
# NOAA NWR93 additionally links FWS ORGCODE=13533 in its official profile URL.
FWS_NOAA = {13529: 'NWR155', 13534: 'NWR46', 13533: 'NWR93', 13552: 'NWR124',
            13555: 'NWR147', 13539: 'NWR38', 13532: 'NWR200'}
SANCTUARIES = {
    'noaa_onms_channel_islands_boundary': ('CINMS', 'NMS1', 'Channel Islands'),
    'noaa_onms_chumash_heritage_boundary': ('CHNMS', None, 'Chumash Heritage'),
    'noaa_onms_cordell_bank_boundary': ('CBNMS', 'NMS2', 'Cordell Bank'),
    'noaa_onms_greater_farallones_boundary': ('GFNMS', 'NMS8', 'Greater Farallones'),
    'noaa_onms_monterey_bay_boundary': ('MBNMS', 'NMS11', 'Monterey Bay'),
    'noaa_onms_olympic_coast_boundary': ('OCNMS', 'NMS13', 'Olympic Coast'),
}
# A regulation identifies the whole designated DFO site across its source zones.
# CPCAD links are explicit reviewed parent IDs; geometry concordance is required.
DFO_CPCAD = {'SOR-2008-124': '700070000', 'SOR-2010-190': '700080000',
             'SOR-2016-280': '700090000', 'SOR-2017-15': '700100000',
             'SOR-2024-122': '700790000'}
LIMITATION = ('Recorded existing/designated marine conservation sites, with PA, OECM and other designations kept distinct; '
              'not a count of legally equivalent MPAs or proof of current law. Proposed AOIs and interim zones are excluded. '
              'Marine scope requires explicit provider marine classification or a reviewed marine-site crosswalk. '
              'Mixed marine/terrestrial NOAA site and matched FWS boundaries retain their full recorded extents. '
              'Unresolved cross-inventory identities remain separate; unmatched FWS marine scope is unqualified. '
              'Positive results are partial inventory summaries; no-hit cells remain unknown, never zero.')


def _text(value):
    return None if value is None or pd.isna(value) else str(value).strip() or None


def _id(value):
    value = _text(value)
    if value is None:
        raise ValueError('Conservation source identity is required')
    return str(int(float(value))) if re.fullmatch(r'\d+(?:\.0+)?', value) else value


def _hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _polygon(geometry):
    """Repair for calculation only; retain polygon dimensions and original bytes."""
    geometry = shapely.make_valid(geometry) if not geometry.is_valid else geometry
    parts = []
    def visit(g):
        if g.geom_type == 'Polygon':
            parts.append(g)
        elif hasattr(g, 'geoms'):
            for part in g.geoms:
                visit(part)
    visit(geometry)
    return shapely.union_all(parts)


def _iou(left, right):
    a = gpd.GeoSeries([_polygon(shapely.union_all([_polygon(g) for g in left]))], crs=4326).to_crs(6933).iloc[0]
    b = gpd.GeoSeries([_polygon(shapely.union_all([_polygon(g) for g in right]))], crs=4326).to_crs(6933).iloc[0]
    union = a.union(b).area
    return a.intersection(b).area / union if union else 0


def _source_frames(root, bindings):
    frames = {}
    for source, binding in bindings.items():
        if source not in {NOAA, *ECCC, FWS, DFO, AOI, ODFW, *SANCTUARIES}:
            continue
        name = f'OriginalData/{source}/geometry.parquet'
        path = (Path(root) / binding['path']).resolve()
        if binding['path'] != name or not path.is_relative_to(Path(root).resolve()) or _hash(path) != binding['sha256']:
            raise ValueError(f'Conservation original binding mismatch: {source}')
        original = json.loads(pq.read_schema(path).metadata[b'governance_original'])
        if original['source']['source_id'] != source:
            raise ValueError('Conservation original source identity mismatch')
        frame = gpd.read_parquet(path)
        if frame.crs.to_epsg() != 4326:
            raise ValueError('Conservation originals require EPSG:4326')
        frames[source] = frame
    return frames


def prepare_sources(frames):
    """Classify original records with explicit IDs; retain exclusions and crosswalk evidence."""
    geoms, descriptors, references, audit, record_context = [], [], [], [], {}
    noaa = frames.get(NOAA)
    accepted_fws, dfo_links = {}, {}
    if noaa is not None and FWS in frames:
        for code, site in FWS_NOAA.items():
            a = frames[FWS][frames[FWS].ORGCODE.map(_id) == str(code)]
            b = noaa[noaa.Site_ID == site]
            if a.empty or b.empty:
                continue
            valid = (set(a.RSL_TYPE) == {'NWR'} and set(b.Design) == {'National Wildlife Refuge'}
                     and set(b.Marine).issubset({'Marine', 'Mixed', 'Interface'})
                     and all('fws.gov' in str(value) for value in b.URL))
            ratio = _iou(a.geometry.to_numpy(), b.geometry.to_numpy()) if valid else 0
            if ratio < .60:
                audit.append({'kind': 'unresolved_fws_crosswalk', 'fws_orgcode': code, 'noaa_site_id': site, 'iou': ratio})
                continue
            accepted_fws[str(code)] = site
            audit.append({'kind': 'accepted_source_id_crosswalk', 'fws_orgcode': code, 'noaa_site_id': site,
                          'iou': ratio, 'evidence': 'Pinned provider-ID pair; same FWS site system and designation; official NOAA FWS URL; whole-site geometry concordance >= 0.60; names are corroboration only'})
    if DFO in frames and ECCC[0] in frames:
        dfo, eccc = frames[DFO], frames[ECCC[0]]
        for regulation, parent in DFO_CPCAD.items():
            a = dfo[dfo.REGULATION.str.contains(regulation, regex=False, na=False)]
            b = eccc[eccc.PARENT_ID.map(_id) == parent]
            if a.empty or b.empty:
                continue
            ratio = _iou(a.geometry.to_numpy(), b.geometry.to_numpy())
            valid = set(b.BIOME) == {'M'} and set(b.PA_OECM_DF) == {1} and set(b.STATUS) == {1}
            if valid and ratio >= .60:
                dfo_links[regulation] = parent
                audit.append({'kind': 'accepted_source_id_crosswalk', 'dfo_regulation_id': regulation, 'cpcad_parent_id': parent,
                              'iou': ratio, 'evidence': 'Pinned regulation/parent-ID pair, Oceans Act PA classification and whole-site geometry concordance >= 0.60'})
            else:
                audit.append({'kind': 'unresolved_dfo_crosswalk', 'dfo_regulation_id': regulation, 'cpcad_parent_id': parent, 'iou': ratio})
    for source, frame in sorted(frames.items()):
        for _, row in frame.iterrows():
            raw = {str(k): _text(v) for k, v in row.items() if k != frame.geometry.name}
            oid = _id(row.get('OBJECTID', row.get('POLY_ID', row.get('ODFW_RECORD_ID', '1'))))
            source_id = f'{source}:{oid}'
            feature_id, name, kind, authority, country, status, classification, mechanism = None, None, None, None, None, None, None, None
            reference = False
            if source == NOAA:
                site = _text(row.get('Site_ID'))
                source_id = f'{source}:{site}'
                if not site or _text(row.get('Marine')) not in {'Marine', 'Mixed', 'Interface'}:
                    audit.append({'kind': 'excluded_unqualified_marine_scope', 'source_feature_id': source_id}); continue
                feature_id, name = f'noaa_mpa_site:{site}', _text(row.get('Site_Name'))
                kind, authority, country = _text(row.get('Design')), _text(row.get('Mgmt_Agen')), 'United States'
                classification, status, mechanism = _text(row.get('Category')), 'Existing inventory reference; not legally reverified', 'NOAA inventory; managing-agency instrument controls'
            elif source in ECCC:
                if _text(row.get('BIOME')) != 'M':
                    audit.append({'kind': 'excluded_terrestrial_zone', 'source_feature_id': source_id, 'parent_id': _id(row.get('PARENT_ID'))}); continue
                pair = (_id(row.get('PA_OECM_DF')), _id(row.get('STATUS')))
                classes = {('1','1'): ('PA', 'Designated'), ('2','1'): ('OECM', 'Designated'),
                           ('3','3'): ('Interim PA', 'Interim'), ('5','1'): ('Provider Not applicable', 'Designated')}
                if pair not in classes:
                    raise ValueError(f'Unqualified marine CPCAD class/status: {pair}')
                classification, status = classes[pair]
                reference = pair == ('3','3')
                feature_id, name = f'cpcad_parent:{_id(row.get("PARENT_ID"))}', _text(row.get('NAME_E'))
                kind, authority, country, mechanism = _text(row.get('TYPE_E')), _text(row.get('MGMT_E')), 'Canada', _text(row.get('MECH_E'))
            elif source == FWS:
                code = _id(row.get('ORGCODE'))
                if code not in accepted_fws:
                    audit.append({'kind': 'excluded_unqualified_fws_marine_scope', 'source_feature_id': source_id, 'orgcode': code, 'name': _text(row.get('ORGNAME'))}); continue
                feature_id, name = f'noaa_mpa_site:{accepted_fws[code]}', _text(row.get('ORGNAME'))
                kind, authority, country = 'National Wildlife Refuge', 'U.S. Fish and Wildlife Service', 'United States'
                classification, status, mechanism = 'Marine-site crosswalk; whole FWS boundary', 'Existing refuge inventory reference', 'FWS reference boundary; site-specific legal instrument not supplied'
            elif source in SANCTUARIES:
                acronym, site, label = SANCTUARIES[source]
                if (_text(row.get('SANCTUARY')) or acronym).upper() != acronym:
                    raise ValueError('Sanctuary provider-ID crosswalk changed')
                # Multiple polygon parts keep their source records, but count one sanctuary.
                feature_id, name = f'noaa_mpa_site:{site}' if site else f'onms_site:{acronym}', label + ' National Marine Sanctuary'
                if site and noaa is not None:
                    candidate = noaa[noaa.Site_ID == site]
                    if not candidate.empty and not (set(candidate.Design) == {'National Marine Sanctuary'} and set(candidate.Site_Name) == {name}):
                        raise ValueError('NOAA sanctuary identity evidence changed')
                kind, authority, country = 'National Marine Sanctuary', 'NOAA Office of National Marine Sanctuaries', 'United States'
                classification, status, mechanism = 'National Marine Sanctuary', 'Designated reference boundary', '15 CFR part 922; official regulation coordinates control'
                audit.append({'kind': 'accepted_sanctuary_source_id_crosswalk', 'source_feature_id': source_id, 'sanctuary_id': acronym, 'noaa_site_id': site})
            elif source == DFO:
                match = re.search(r'SOR-\d{4}-\d+', str(row.get('REGULATION')))
                # Never group zones by a cleaned site name.
                reg = match.group(0) if match else None
                feature_id = f'cpcad_parent:{dfo_links[reg]}' if reg in dfo_links else f'dfo_regulation:{reg}' if reg else f'dfo_unresolved_record:{oid}'
                name, kind, authority, country = _text(row.get('NAME_E')), 'Oceans Act Marine Protected Area', 'Fisheries and Oceans Canada', 'Canada'
                classification, status, mechanism = 'Oceans Act MPA', 'Designated', _text(row.get('REGULATION'))
                if not reg: audit.append({'kind': 'unresolved_dfo_site_identity', 'source_feature_id': source_id})
            elif source == AOI:
                reference = True
                feature_id, name = f'dfo_aoi_record:{oid}', _text(row.get('NAME_E'))
                kind, authority, country = 'Oceans Act Area of Interest point', 'Fisheries and Oceans Canada', 'Canada'
                classification, status, mechanism = 'Proposed AOI', 'Proposed / under assessment; not designated', None
            elif source == ODFW:
                # Placemark IDs identify reserve/MPA zones; no defensible whole-site
                # provider-ID crosswalk exists in this retained KML. Do not invent one.
                audit.append({'kind': 'unresolved_odfw_site_identity', 'source_feature_id': source_id, 'name': raw.get('ODFW_NAME')})
                continue
            else:
                continue
            record = dict.fromkeys(RECORD_FIELDS)
            record.update(source_dataset_id=source, source_feature_id=source_id, feature_name=name,
                          feature_type=kind, authority=authority, jurisdiction=country,
                          region=raw.get('State') or raw.get('LOC'), area_system_id=classification,
                          area_code=raw.get('ZONE_ID') or raw.get('Site_ID') or raw.get('ORGCODE') or oid,
                          area_title=mechanism, area_hierarchy_level=status, parent_area_code=raw.get('PARENT_ID'))
            record_context[source_id] = {'designation_type': kind, 'reporting_classification': classification,
                'designation_status': status, 'legal_mechanism': mechanism, 'site_identity': feature_id,
                'provider_parent_id': raw.get('PARENT_ID'), 'provider_zone_id': raw.get('ZONE_ID'),
                'provider_pa_oecm_df': raw.get('PA_OECM_DF'), 'provider_status': raw.get('STATUS'),
                'marine_scope': raw.get('BIOME') or raw.get('Marine') or classification}
            geometry = row.geometry
            if geometry is None or geometry.is_empty:
                continue
            if not reference or geometry.geom_type not in {'Point', 'MultiPoint'}:
                geometry = _polygon(geometry)
                if geometry.is_empty: continue
            digest = hashlib.sha256(shapely.to_wkb(shapely.normalize(geometry))).hexdigest()[:24]
            record['geometry_part_ids'] = [f'{source_id}:original:{digest}']
            if reference:
                references.append((geometry, feature_id, record))
            else:
                geoms.append(geometry); descriptors.append((feature_id, record))
    return geoms, descriptors, references, audit, record_context


def _merge(entries):
    features = {}
    for feature_id, record in entries:
        key = tuple(record[k] for k in RECORD_FIELDS)
        features.setdefault(feature_id, {}).setdefault(key, set()).update(record['geometry_part_ids'])
    return [{'feature_id': feature_id, 'records': [dict(zip(RECORD_FIELDS, key), geometry_part_ids=sorted(parts))
             for key, parts in sorted(records.items(), key=lambda item: json.dumps(item[0], ensure_ascii=True))]}
            for feature_id, records in sorted(features.items())]


def overlay(cells, geometries, descriptors, *, area=True):
    """Full-cell EPSG:6933 positive-area union; point references have no coverage."""
    rows, fractions = [None] * len(cells), [None] * len(cells)
    if not geometries:
        return rows, fractions
    from governance.shared.spatial import _antimeridian_intersection
    bounds = shapely.total_bounds([Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(c)]) for c in cells])
    extent = shapely.box(*bounds)
    clipped, selected = [], []
    for geometry, descriptor in zip(geometries, descriptors):
        part = _antimeridian_intersection(geometry, extent)
        if not part.is_empty:
            clipped.append(part); selected.append(descriptor)
    if not clipped: return rows, fractions
    descriptors = selected
    geometries = gpd.GeoSeries(clipped, crs=4326).to_crs(6933).to_numpy()
    tree = shapely.STRtree(geometries)
    for start in range(0, len(cells), 2048):
        grid = gpd.GeoSeries([Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(c)])
                             for c in cells[start:start+2048]], crs=4326).to_crs(6933).to_numpy()
        pairs = tree.query(grid, predicate='intersects')
        if not pairs.size: continue
        parts = shapely.intersection(grid[pairs[0]], geometries[pairs[1]])
        hits = {}
        for cell, index, part in zip(pairs[0], pairs[1], parts):
            if part.is_empty or (shapely.get_dimensions(geometries[index]) == 2 and part.area <= 0): continue
            hits.setdefault(int(cell), []).append((int(index), part))
        for i, found in hits.items():
            rows[start+i] = _merge([descriptors[index] for index, _ in found])
            if area:
                fraction = shapely.union_all([part for _, part in found]).area / grid[i].area
                if fraction < 0 or fraction > 1 + 1e-8:
                    raise ValueError('Conservation union exceeds full H3 support')
                fractions[start+i] = min(1., fraction)
    return rows, fractions


@lru_cache(maxsize=1)
def _prepare_cached(root, bindings_json):
    return prepare_sources(_source_frames(root, json.loads(bindings_json)))


def populate_features(table, metadata, original_root):
    """Shared normal exporter and targeted refresh; preserve all legacy support arrays."""
    if not set(LEGACY).intersection(metadata.get('collections', {})):
        return table
    bindings = {s: b for s, b in metadata.get('original_data', {}).items()
                if s in {NOAA, *ECCC, FWS, DFO, AOI, ODFW, *SANCTUARIES}}
    # Cache only hash-qualified originals across R6/R8; every call checks current bytes.
    for source, binding in bindings.items():
        if _hash(Path(original_root) / binding['path']) != binding['sha256']:
            raise ValueError(f'Conservation original checksum mismatch: {source}')
    geoms, descriptors, references, audit, context = _prepare_cached(str(Path(original_root).resolve()), json.dumps(bindings, sort_keys=True))
    cells = table['h3_index'].to_pylist()
    rows, fractions = overlay(cells, geoms, descriptors)
    ref_rows, _ = overlay(cells, [v[0] for v in references], [(v[1],v[2]) for v in references], area=False)
    fields, coverage = metadata['fields'], metadata['coverage']
    for name, field in fields.items():
        if name.startswith(tuple(group+'__' for group in LEGACY)):
            field.update(map_feature=False, superseded_by=GROUP, compatibility_support=True)
    for group, members, area_values in ((GROUP, rows, fractions), (REFERENCE, ref_rows, None)):
        count, assignment = group+'__recorded_feature_count', group+'__feature_memberships_v1'
        states = ['partial' if row else 'unknown' for row in members]
        values = {assignment: pa.array(members, MEMBERSHIP_TYPE), count: pa.array([len(row) if row else None for row in members], pa.int64())}
        descriptor = {**definition(group), 'definition': LIMITATION if group == GROUP else 'Proposed AOI points and provider interim marine zones, excluded from all Marine Conservation Area totals. No proposed boundary is inferred from a point.',
                      'scientific_method_version': METHOD, 'source_record_context': {r['source_feature_id']: context[r['source_feature_id']] for row in members or [] for e in row or [] for r in e['records']},
                      'count_semantics': 'List length equals distinct reviewed source-ID site count; source records and geometry parts never count as extra sites.'}
        fields[assignment] = descriptor
        fields[count] = {'units':'count', 'nullable':True, 'definition': descriptor['definition'], 'missing_reason_field':count+'_status', 'coverage_reference':group, 'scientific_method_version':METHOD}
        if area_values is not None:
            values[COVERAGE] = pa.array(area_values, pa.float64())
            fields[COVERAGE] = {'units':'1', 'nullable':True, 'definition':'Union of all eligible source polygons intersected with full H3 polygon / full H3 polygon area in EPSG:6933. Overlapping sites and duplicate inventory boundaries are never summed. '+LIMITATION,
                                'missing_reason_field':COVERAGE+'_status','coverage_reference':group,'scientific_method_version':METHOD}
        for name in list(values):
            values[name+'_status'] = pa.array(states, pa.string())
            fields[name+'_status'] = {'units':None,'nullable':False,'definition':'Partial recorded intersection or unknown no-hit; not exhaustive absence','enum':['partial','unknown'],'map_feature':False}
            fields[name].update(map_feature=name in SCIENTIFIC_FEATURES, **SCIENTIFIC_FEATURES.get(name, {}))
        if group == REFERENCE:
            fields[assignment].update(map_feature=True, display_name='Proposed / Interim Conservation Reference Assignment', display_family='Proposed / Interim Conservation References')
        for name,value in values.items():
            table = table.set_column(table.column_names.index(name), name, value) if name in table.column_names else table.append_column(name,value)
        coverage[group] = {'scientific_method_version':METHOD, 'geographic_inventory_coverage':{'status':'unknown'}, 'metric_support_state':'partial',
                           'source_bindings':bindings,'classification_and_identity_evidence':audit,'effect':descriptor['definition']}
    metadata['marine_conservation_unification'] = {'method':METHOD,'scientific_features':SCIENTIFIC_FEATURES,
        'source_collections':list(LEGACY), 'legacy_columns':'Retained hidden compatibility/support; non-additive; never labeled unique marine sites',
        'references':REFERENCE,'limitation':LIMITATION}
    validate_memberships(table, fields)
    return table
