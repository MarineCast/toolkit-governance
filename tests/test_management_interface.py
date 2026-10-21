import copy

import pyarrow as pa
import pytest

from governance.fisheries_management.management_areas.interface import (
    ASSIGNMENT, COUNT, GROUP, SUPPORT, compact_features,
)
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition, validate_memberships


def fixture(state='partial'):
    record = dict.fromkeys(RECORD_FIELDS)
    record.update(source_dataset_id='wdfw', source_feature_id='7', feature_name='Area Seven', geometry_part_ids=['part-1'])
    entry = {'feature_id': 'wdfw:7', 'records': [record]}
    rows = [[entry], [] if state == 'observed' else None] if state in ('observed', 'partial') else [None, None]
    table = pa.table({COUNT: pa.array([len(row) if row is not None else None for row in rows], pa.int64()),
                      ASSIGNMENT: pa.array(rows, MEMBERSHIP_TYPE),
                      COUNT + '_status': [state] * 2, ASSIGNMENT + '_status': [state] * 2,
                      GROUP + '__recorded_polygon_union_area_fraction': [1., None], 'other__metric': [0, None]})
    fields = {name: {} for name in table.column_names}
    fields[COUNT] = {'units': 'count', 'missing_reason_field': COUNT + '_status', 'definition': 'Retained definition'}
    fields[ASSIGNMENT] = definition(GROUP)
    return table, fields, {GROUP: {'metric_support_state': state}}


@pytest.mark.parametrize('state', ['observed', 'partial', 'unknown', 'unavailable', 'not_applicable'])
def test_compaction_preserves_values_source_records_and_exact_support(state):
    table, fields, coverage = fixture(state)
    original = copy.deepcopy(fields)
    result = compact_features(table, fields, coverage)
    assert result.column_names == [COUNT, ASSIGNMENT, 'other__metric']
    for name in result.column_names:
        assert result[name].equals(table[name])
    assert set(fields) == set(result.column_names)
    for name in (COUNT, ASSIGNMENT):
        assert fields[name]['implicit_support'] == SUPPORT
        assert fields[name]['implicit_status'] == state
        assert fields[name]['definition'] == original[name]['definition']
        assert 'missing_reason_field' not in fields[name]
    assert result.equals(compact_features(result, fields, coverage))
    wrong = copy.deepcopy(fields); wrong[COUNT]['implicit_status'] = 'observed' if state != 'observed' else 'partial'
    with pytest.raises(ValueError): validate_memberships(result, wrong)


def test_compaction_refuses_loss_of_nonuniform_support():
    table, fields, coverage = fixture()
    table = table.set_column(table.column_names.index(COUNT + '_status'), COUNT + '_status', pa.array(['partial', 'unknown']))
    with pytest.raises(ValueError, match='uniform'):
        compact_features(table, fields, coverage)
