import copy
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from governance.app_contract import annotate_catalog, contract, project_app_contract


def test_projection_preserves_values_and_rejects_dangling_support():
    name = 'critical_habitat__recorded_feature_count'
    status = name + '_status'
    table = pa.table({'h3_index': ['cell-a', 'cell-b'], name: [2, None],
                      status: ['partial', 'unknown'], 'unused': [9, 8]})
    metadata = {'spatial': {'h3_resolution': 6}, 'fields': {
        'h3_index': {}, name: {'missing_reason_field': status},
        status: {}, 'unused': {},
    }}
    original = copy.deepcopy(metadata)
    selected = project_app_contract(table, metadata)
    assert selected.column_names == ['h3_index', name, status]
    for field in selected.column_names:
        assert selected[field].equals(table[field])
        assert metadata['fields'][field] == original['fields'][field]
    assert selected[name].to_pylist() == [2, None]
    with pytest.raises(ValueError, match='Incomplete application support'):
        project_app_contract(table.drop([status]), original)
    metadata['spatial']['h3_resolution'] = 7
    with pytest.raises(ValueError, match='resolutions 6 and 8'):
        project_app_contract(table, metadata)


def test_catalog_dates_require_explicit_data_update_evidence(tmp_path):
    path = tmp_path / 'geometry.parquet'
    original = {'receipt': {'metadata_response': {'editingInfo': {
        'dataLastEditDate': 1704067200000, 'lastEditDate': 1735689600000,
    }}}}
    pq.write_table(pa.table({'id': [1]}).replace_schema_metadata(
        {b'governance_original': json.dumps(original).encode()}), path)
    catalog = {'last_updated_utc': '2026-10-20T00:00:00+00:00',
               'original_data': {'source': {'path': path.name}}}
    annotate_catalog(catalog, {'source': {'source_as_of': 'unknown',
                     'retrieved_at_utc': '2026-10-19T00:00:00+00:00'}}, tmp_path)
    dates = catalog['sources']['source']
    assert dates['source_updated_at'] == '2024-01-01T00:00:00+00:00'
    assert dates['observation_date'] is None
    assert dates['publication_date'] is None
    original['receipt']['metadata_response']['editingInfo'].pop('dataLastEditDate')
    pq.write_table(pa.table({'id': [1]}).replace_schema_metadata(
        {b'governance_original': json.dumps(original).encode()}), path)
    annotate_catalog(catalog, {'source': {'source_as_of': '2025 publication'}}, tmp_path)
    assert catalog['sources']['source']['source_updated_at'] is None


def test_packaged_contract_is_unique_and_scoped():
    spec = contract()
    assert len(spec['columns']) == len(set(spec['columns'])) == 61
    assert len(spec['features']) == 20
    assert len(spec['families']) == 7
    assert spec['resolutions'] == [6, 8]
    assert len(spec['compatibility_columns']) == 4
