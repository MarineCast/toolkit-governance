"""The selected interface preserves scientific values and native support."""
import copy

import pyarrow as pa

from governance.delivery import project_delivery
from governance.maintenance.catalog import build_catalog
from governance.protected_areas.wildlife_refuges.interface import SCIENTIFIC_FEATURES, annotate_fields


def test_catalog_and_delivery_expose_three_refuge_features_only():
    prefix = 'wildlife_refuges__'
    names = ['recorded_feature_count', 'recorded_polygon_union_area_fraction', 'recorded_line_union_length_m', 'recorded_point_feature_count', 'feature_memberships_v1']
    fields = {prefix + name + tail: {'definition': 'retained'} for name in names for tail in ('', '_status')}
    fields['ports__recorded_feature_count'] = {'definition': 'unrelated'}
    before = copy.deepcopy(fields)
    annotate_fields(fields)
    assert {name for name, field in fields.items() if field.get('map_feature')} == set(SCIENTIFIC_FEATURES)
    assert fields['ports__recorded_feature_count'] == before['ports__recorded_feature_count']
    assert all(field['definition'] == 'retained' for field in fields.values() if field is not fields['ports__recorded_feature_count'])
    assert build_catalog()['collections']['wildlife_refuges']['scientific_features'] == SCIENTIFIC_FEATURES
    assert fields[prefix + 'recorded_polygon_union_area_fraction']['display_scale'] == 100


def test_delivery_keeps_raw_fraction_status_and_other_family():
    groups = ('wildlife_refuges', 'critical_habitat')
    columns = {'H3_INDEX': ['cell']}
    for group in groups:
        for suffix, value, dtype in [('FEATURE_COUNT', 2, pa.int64()), ('POLYGON_COVERAGE_FRAC', .425, pa.float64()), ('LINE_LENGTH_M', None, pa.float64()), ('POINT_COUNT', None, pa.int64())]:
            columns[group + '__' + suffix] = pa.array([value], type=dtype)
    metadata = {'native_manifests': {group: {'manifest': {'source_completeness': 'partial', 'sources': [{'source_id': group, 'runtime_status': 'available'}]}} for group in groups},
                'grid': {}, 'area_crs': 'EPSG:6933', 'length_crs': 'EPSG:32610', 'temporal_support': 'static', 'config_hash': 'fixture'}
    table, envelope = project_delivery(pa.table(columns), metadata, 6)
    name = 'wildlife_refuges__recorded_polygon_union_area_fraction'
    assert table[name].to_pylist() == [.425]
    assert table[name + '_status'].to_pylist() == ['partial']
    assert envelope['fields'][name]['units'] == '1'
    assert envelope['fields'][name]['display_unit'] == '%'
    assert envelope['fields']['critical_habitat__recorded_feature_count']['map_feature'] is True
    assert envelope['fields']['critical_habitat__recorded_feature_count']['display_name'] == 'Critical Habitat Count'
