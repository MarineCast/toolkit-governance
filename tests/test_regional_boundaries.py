import copy
import hashlib
import json

import geopandas as gpd
import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import Polygon, box

from governance.jurisdiction.county_regional_boundaries.interface import (
    ASSIGNMENT, COUNT, GROUP, SOURCES, populate_features,
)
from governance.jurisdiction.county_regional_boundaries.normalize import normalize
from governance.memberships import validate_memberships
from governance.shared.config import load_governance_config


def fixture(tmp_path, resolution=6):
    cell = h3.latlng_to_cell(48.5, -123.5, resolution)
    poly = Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cell)])
    # Same name across countries must remain two identities; county only touches
    # the cell's west-most vertex, district overlaps the entire cell.
    x, y = min(poly.exterior.coords, key=lambda point: point[0])
    geometries = [box(x - 1, y - .1, x, y + .1), poly]
    attrs = [{'GEOID': ['53055'], 'NAME': ['Shared name']},
             {'LGL_ADMIN_AREA_ID': [257], 'ADMIN_AREA_NAME': ['Shared name'], 'WHEN_UPDATED': [123456789]}]
    bindings = {}
    for source, geometry, attributes in zip(SOURCES, geometries, attrs):
        path = tmp_path / f'OriginalData/{source}/geometry.parquet'
        path.parent.mkdir(parents=True)
        gpd.GeoDataFrame(attributes, geometry=[geometry], crs=4326).to_parquet(path, index=False)
        table = pq.read_table(path)
        record = {'source_id': source, 'provider': source, 'legal_citation': 'reference',
                  'url': 'https://example.test', 'retrieved_at_utc': None,
                  'source_as_of': 'snapshot', 'limitation': 'partial'}
        pq.write_table(table.replace_schema_metadata({**table.schema.metadata,
            b'governance_original': json.dumps({'source': record}).encode()}), path)
        bindings[source] = {'path': str(path.relative_to(tmp_path)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    table = pa.table({'h3_index': [cell, h3.latlng_to_cell(40, -125, resolution)],
        COUNT: pa.array([1, None], pa.int64()),
        GROUP + '__recorded_line_union_length_m': [None, None],
        COUNT + '_status': ['partial', 'unknown'], 'other__metric': [10, 20]})
    meta = {'fields': {name: {} for name in table.column_names}, 'coverage': {}, 'original_data': bindings}
    return table, meta


@pytest.mark.parametrize('resolution', [6, 8])
def test_two_fields_all_contacts_pairing_nulls_and_exact_replay(tmp_path, resolution):
    table, meta = fixture(tmp_path, resolution)
    result = populate_features(table, meta, tmp_path)
    assert {name for name in result.column_names if name.startswith(GROUP + '__')} == {COUNT, ASSIGNMENT}
    assert result[COUNT].to_pylist() == [2, None]
    assert result['other__metric'].equals(table['other__metric'])
    entries = result[ASSIGNMENT][0].as_py()
    assert {record['feature_name'] for entry in entries for record in entry['records']} == {'Shared name'}
    assert {record['source_dataset_id'] for entry in entries for record in entry['records']} == set(SOURCES)
    assert result.equals(populate_features(result, meta, tmp_path))
    assert all('missing_reason_field' not in meta['fields'][name] for name in (COUNT, ASSIGNMENT))
    validate_memberships(result, meta['fields'])
    with pytest.raises(ValueError, match='count mismatch'):
        validate_memberships(result.set_column(result.column_names.index(COUNT), COUNT, pa.array([1, None], pa.int64())), meta['fields'])
    for key, value in [('implicit_null_status', 'observed'), ('coverage_reference', 'other')]:
        changed = copy.deepcopy(meta['fields']); changed[ASSIGNMENT][key] = value
        with pytest.raises(ValueError): validate_memberships(result, changed)
    meta['original_data'][SOURCES[0]]['sha256'] = 'corrupt'
    with pytest.raises(ValueError, match='binding mismatch'): populate_features(table, meta, tmp_path)


def test_bc_normalization_preserves_attributes_dates_ids_and_excludes_stikine():
    source = load_governance_config().sources[SOURCES[1]]
    raw = gpd.GeoDataFrame({'LGL_ADMIN_AREA_ID': [257, 361],
        'ADMIN_AREA_NAME': ['Capital Regional District', 'Stikine Region (Unincorporated)'],
        'WHEN_UPDATED': [123456789, 987654321], 'OIC_MO_YEAR': ['2025', None]},
        geometry=[box(-124, 48, -123, 49)] * 2, crs=4326)
    native = normalize(raw, source)
    assert native.SOURCE_FEATURE_ID.tolist() == [SOURCES[1] + ':257']
    assert native.BC_ABMS_WHEN_UPDATED.tolist() == ['123456789']
    assert native.BC_ABMS_OIC_MO_YEAR.tolist() == ['2025']
    assert native.EFFECTIVE_START.isna().all() and native.LEGAL_AUTHORITY.isna().all()
    assert not native.MODEL_ELIGIBLE.any()
    raw.loc[1, 'LGL_ADMIN_AREA_ID'] = 257
    with pytest.raises(ValueError, match='LGL_ADMIN_AREA_ID'): normalize(raw, source)


def test_missing_sources_unavailable_never_zero(tmp_path):
    table, meta = fixture(tmp_path); meta['original_data'] = {}
    result = populate_features(table, meta, tmp_path)
    assert result[COUNT].to_pylist() == [None, None]
    assert meta['fields'][COUNT]['implicit_null_status'] == 'unavailable'
    assert meta['coverage'][GROUP]['metric_support_state'] == 'unavailable'


def test_invalid_polygon_repair_preserves_original_and_deduplicates_parts(tmp_path):
    table, meta = fixture(tmp_path)
    path = tmp_path / meta['original_data'][SOURCES[1]]['path']
    original_metadata = pq.read_schema(path).metadata[b'governance_original']
    raw = gpd.read_parquet(path)
    raw.geometry = [Polygon([(-124, 48), (-123, 49), (-124, 49), (-123, 48), (-124, 48)])]
    assert not raw.geometry.iloc[0].is_valid
    raw.to_parquet(path, index=False)
    original_table = pq.read_table(path)
    pq.write_table(original_table.replace_schema_metadata({**original_table.schema.metadata,
        b'governance_original': original_metadata}), path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    meta['original_data'][SOURCES[1]]['sha256'] = checksum
    result = populate_features(table, meta, tmp_path)
    assert result[COUNT].to_pylist() == [2, None]
    bc = next(entry for entry in result[ASSIGNMENT][0].as_py() if entry['feature_id'].startswith(SOURCES[1]))
    assert len(bc['records'][0]['geometry_part_ids']) == 2
    assert meta['coverage'][GROUP]['source_audit'][SOURCES[1]]['repaired_feature_ids'] == [SOURCES[1] + ':257']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum


def test_normal_build_and_offline_originals_rebuild_compact_interface(tmp_path, monkeypatch, snapshot_fixture):
    import yaml
    from governance.products import build_products, validate_products
    from governance.workspace import initialize_workspace
    workspace = tmp_path / 'workspace'; initialize_workspace(workspace)
    monkeypatch.setenv('GOVERNANCE_WORKSPACE', str(workspace))
    config_path = workspace / 'config/data/governance/governance.yaml'
    values = yaml.safe_load(config_path.read_text())
    values['collections'] = {GROUP: values['collections'][GROUP]}
    values['collections'][GROUP]['source_ids'] = [SOURCES[1]]
    values['sources'] = {SOURCES[1]: values['sources'][SOURCES[1]]}
    config_path.write_text(yaml.safe_dump(values))
    source = load_governance_config().sources[SOURCES[1]]
    raw = gpd.GeoDataFrame({'OBJECTID': [1], 'LGL_ADMIN_AREA_ID': [257], 'ADMIN_AREA_NAME': ['Capital Regional District']},
                          geometry=[box(-124, 48, -123, 49)], crs=4326)
    source.snapshot_path.parent.mkdir(parents=True)
    source.snapshot_path.write_text(json.dumps(snapshot_fixture(source, raw)))
    grid = tmp_path / 'grid.parquet'
    pq.write_table(pa.table({'H3_INDEX': [h3.latlng_to_cell(48.5, -123.5, r) for r in (6, 8)], 'H3_RESOLUTION': [6, 8]}), grid)
    output = build_products([grid], tmp_path / 'Governance', config_path=config_path, allow_partial=True)
    assert validate_products(output)['status'] == 'passed'
    replay = build_products([grid], tmp_path / 'replay', config_path=config_path, original_data=output, allow_partial=True)
    for resolution in (6, 8):
        table = pq.read_table(output / f'governance-r{resolution}-static.parquet')
        assert set(table.column_names) == {'h3_index', COUNT, ASSIGNMENT}
        assert table[COUNT].to_pylist() == [1]
        assert table.equals(pq.read_table(replay / f'governance-r{resolution}-static.parquet'), check_metadata=False)
