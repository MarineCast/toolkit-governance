import copy
import json
import zlib
from pathlib import Path

import h3
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from governance.app_only import compact_table, restore_support, rename_table, SUPPORT_KEY
from governance.app_contract import contract
from governance.app_view import readable_names
from governance.compact import compact_products
from governance.memberships import MEMBERSHIP_TYPE, RECORD_FIELDS, definition
from governance.products import validate_metric_table, validate_products
from governance.shared.artifacts import sha256_file


@pytest.fixture
def scientific_table():
    def member(identity, status):
        record = dict.fromkeys(RECORD_FIELDS)
        record.update(source_dataset_id='fixture', source_feature_id=identity,
                      feature_name=identity, area_hierarchy_level=status, geometry_part_ids=[identity + ':part'])
        return {'feature_id': identity, 'records': [record]}
    columns = {'h3_index': pa.array([h3.latlng_to_cell(48+i*.1, -123, 6) for i in range(3)], pa.string())}
    fields = {'h3_index': {'definition': 'Native H3 identity', 'units': None}}
    for group, values, states in [
        ('marine_conservation_areas', [[member('site-a', 'Designated')], None, []], ['partial', 'unknown', 'observed']),
        ('proposed_interim_conservation_references', [[member('site-a', 'Interim')], [member('site-b', 'Proposed')], []], ['partial', 'partial', 'observed']),
    ]:
        name = group + '__feature_memberships_v1'
        count = group + '__recorded_feature_count'
        columns[name] = pa.array(values, MEMBERSHIP_TYPE)
        columns[count] = pa.array([len(value) if value is not None else None for value in values], pa.int64())
        fields[name] = definition(group)
        fields[count] = {'definition': 'Distinct recorded features', 'units': 'count', 'missing_reason_field': count+'_status'}
        for column in [name, count]:
            columns[column+'_status'] = pa.array(states, pa.string())
            fields[column+'_status'] = {'definition': 'Recorded support', 'units': None}
    table = pa.table(columns)
    metadata = {'schema_version': 1, 'model_eligible': False, 'fields': fields,
                'spatial': {'h3_resolution': 6}, 'temporal': {'type': 'static'},
                'original_data': {}, 'collections': {}}
    validate_metric_table(table, metadata)
    return table, metadata


def test_exact_partition_and_status_qualified_assignment(scientific_table, tmp_path):
    original, metadata = scientific_table
    public, context = compact_table(original, metadata, tmp_path/'audit')
    assert public.column_names == ['h3_index', 'conservation_area_count', 'conservation_area_membership']
    assert not any(name.endswith('_status') for name in public.column_names)
    assignment = public['conservation_area_membership'].to_pylist()
    assert assignment[0] == ['site-a', 'site-a [Interim]']
    assert assignment[1] == ['site-b [Proposed]']
    assert assignment[2] == []
    assert public['conservation_area_count'].to_pylist() == [1, None, 0]
    restored, restored_metadata = restore_support(public, context)
    assert restored.equals(original, check_metadata=False)
    assert restored_metadata == metadata
    validate_metric_table(public, context)
    assert not (tmp_path/'audit').exists()
    assert context['application_contract']['version'] == 5
    assert 'path' not in context['embedded_support']
    path = tmp_path/'final.parquet'
    pq.write_table(public.replace_schema_metadata({**public.schema.metadata, b'governance':json.dumps(context).encode()}),path)
    on_disk = pq.read_table(path)
    assert restore_support(on_disk, context)[0].equals(original, check_metadata=False)
    reordered, _ = restore_support(public.take([2, 0, 1]), context)
    assert reordered.equals(original.take([2, 0, 1]), check_metadata=False)


@pytest.mark.parametrize('version', [4, 5])
def test_rejects_corrupt_missing_or_misaligned_support(scientific_table, tmp_path, version):
    original, metadata = scientific_table
    public, context = compact_table(original, metadata, tmp_path/'audit', naming_version=version)
    column = 'conservation_area_membership'
    values = public[column].to_pylist()
    values[0][0] = 'wrong'
    changed = public.set_column(public.column_names.index(column), column, pa.array(values, pa.list_(pa.string())))
    with pytest.raises(ValueError, match='public view'):
        restore_support(changed, context)
    changed = public.set_column(0, 'h3_index', pa.array([public['h3_index'][0].as_py()]*3))
    with pytest.raises(ValueError, match='Duplicate'):
        restore_support(changed, context)
    if version == 4:
        path = Path(context['app_only_audit']['path'])
        path.write_bytes(path.read_bytes()+b'changed')
        with pytest.raises(ValueError, match='checksum'):
            restore_support(public, context)
        missing = copy.deepcopy(context)
        missing['app_only_audit']['path'] = str(tmp_path/'missing.parquet')
        with pytest.raises(FileNotFoundError):
            restore_support(public, missing)
    else:
        for schema_metadata in ({}, {SUPPORT_KEY:public.schema.metadata[SUPPORT_KEY]+b'changed'}):
            with pytest.raises(ValueError, match='checksum'):
                restore_support(public.replace_schema_metadata(schema_metadata), context)
        for binding in ({}, None):
            changed = {**context, 'embedded_support':binding}
            with pytest.raises(ValueError,match='support binding'):
                validate_metric_table(public,changed)
        missing = {key:value for key,value in context.items() if key != 'embedded_support'}
        with pytest.raises(ValueError,match='requires scientific support'):
            restore_support(public,missing)


def test_v2_alias_upgrade_reuses_audit_and_preserves_types_nulls(scientific_table, tmp_path):
    original, metadata = scientific_table
    current, context = compact_table(original, metadata, tmp_path/'audit', naming_version=3)
    inverse = {new: old for old, new in contract()['column_aliases'].items()}
    legacy = current.rename_columns([inverse[name] for name in current.column_names])
    legacy_context = copy.deepcopy(context)
    legacy_context['fields'] = {inverse[name]: field for name, field in context['fields'].items()}
    legacy_context['application_contract'].update(version=2, columns=legacy.column_names)
    legacy_context['application_contract'].pop('column_aliases')
    audit_path = Path(context['app_only_audit']['path'])
    before = audit_path.read_bytes()
    restored, _ = restore_support(legacy, legacy_context)
    assert restored.equals(original, check_metadata=False)
    renamed, renamed_context = rename_table(legacy, legacy_context)
    assert renamed.equals(current, check_metadata=False)
    assert renamed_context['app_only_audit'] == context['app_only_audit']
    assert audit_path.read_bytes() == before
    validate_metric_table(renamed, renamed_context)
    renamed_context['application_contract']['column_aliases']['h3_index'] = 'wrong'
    with pytest.raises(ValueError, match='alias mapping'):
        restore_support(renamed, renamed_context)


def test_readable_labels_preserve_overlap_missing_names_and_source_meanings():
    def member(identity, **record):
        return {'feature_id': identity, 'records': [record]}
    assert readable_names('country_membership', [
        member('ca', jurisdiction='CAN', feature_name='Canada water support'),
        member('us', jurisdiction='USA', feature_name='United States water support'),
    ]) == ['Canada', 'United States']
    assert readable_names('state_province_membership', [
        member('bc', region='BC', feature_name='Canada water support'),
        member('wa', region='WA', feature_name='Clallam County'),
    ]) == ['British Columbia', 'Washington']
    shared = [member('a', feature_name='Shared name'), member('b', feature_name='Shared name')]
    assert readable_names('county_district_membership', shared) == ['Shared name']
    assert readable_names('county_district_membership', shared + [member('unnamed')]) == ['Shared name', None]
    assert readable_names('county_district_membership', None) is None
    assert readable_names('county_district_membership', []) == []
    assert readable_names('fisheries_management_area_membership', [
        member('area-7', feature_name='7', area_title='San Juan Islands', area_code='7'),
    ]) == ['San Juan Islands']


def test_v3_upgrade_retains_every_original_struct_and_count(scientific_table, tmp_path):
    from governance.app_only import upgrade_table
    original, metadata = scientific_table
    typed, typed_metadata = compact_table(original, metadata, tmp_path/'v3', naming_version=3)
    public, current = upgrade_table(typed, typed_metadata)
    assert public['conservation_area_membership'].type == pa.list_(pa.string())
    assert public['conservation_area_count'].equals(typed['conservation_area_count'])
    restored, context = restore_support(public, current)
    assert restored.equals(original, check_metadata=False)
    assert context == metadata
    audit = pq.read_table(pa.BufferReader(zlib.decompress(public.schema.metadata[SUPPORT_KEY])))
    for name in original.column_names:
        if name.endswith('__feature_memberships_v1'):
            assert audit[name].equals(original[name])
    assert 'app_only_audit' not in current
    assert Path(typed_metadata['app_only_audit']['path']).is_file()


def legacy_delivery(tmp_path, scientific_table):
    table, metadata = scientific_table
    root = tmp_path/'Governance'
    root.mkdir()
    path = root/'governance-r6-static.parquet'
    pq.write_table(table.replace_schema_metadata({b'governance': json.dumps(metadata).encode()}), path)
    catalog = {'schema_version':1, 'domain':'governance', 'original_data':{}, 'areas':{},
               'built_at_utc':'2026-10-20T00:00:00+00:00',
               'tables':{'6':{'static':{'path':path.name,'sha256':sha256_file(path),'rows':3}}}}
    (root/'catalog.json').write_text(json.dumps(catalog))
    (root/'REVIEW_RESULTS.txt').write_text('Preserve my review note.')
    return root


def test_migration_preserves_note_dates_and_is_idempotent(scientific_table, tmp_path):
    root = legacy_delivery(tmp_path, scientific_table)
    compact_products(root)
    catalog = json.loads((root/'catalog.json').read_text())
    assert catalog['built_at_utc'] == '2026-10-20T00:00:00+00:00'
    assert (root/'REVIEW_RESULTS.txt').read_text() == 'Preserve my review note.'
    before = (root/'catalog.json').read_bytes()
    assert compact_products(root)['status'] == 'passed'
    assert (root/'catalog.json').read_bytes() == before
    assert not (tmp_path/'unused').exists()
    assert set(tmp_path.iterdir()) == {root}
    assert validate_products(root)['status'] == 'passed'


def test_failed_publication_restores_existing_delivery(scientific_table, tmp_path, monkeypatch):
    import governance.compact as module
    root = legacy_delivery(tmp_path, scientific_table)
    before = {p.name:p.read_bytes() for p in root.iterdir()}
    replace = module.os.replace
    failed = False
    def interrupted(source, target):
        nonlocal failed
        if Path(target) == root/'catalog.json' and not failed:
            failed = True
            raise OSError('injected publication interruption')
        return replace(source, target)
    monkeypatch.setattr(module.os, 'replace', interrupted)
    with pytest.raises(OSError, match='injected'):
        compact_products(root)
    assert {p.name:p.read_bytes() for p in root.iterdir()} == before
    assert validate_products(root)['status'] == 'passed'


def test_cleanup_protects_legacy_required_audits(scientific_table, tmp_path):
    from governance.products import cleanup_workspace_data
    from governance.workspace import initialize_workspace
    from governance._config.paths import workspace_scope
    workspace = tmp_path/'workspace'
    initialize_workspace(workspace)
    root = legacy_delivery(tmp_path, scientific_table)
    original, metadata = scientific_table
    audit_dir = workspace/'data/processed/domain/governance/legacy-support'
    public, context = compact_table(original, metadata, audit_dir, naming_version=4)
    path = root/'governance-r6-static.parquet'
    pq.write_table(public.replace_schema_metadata({b'governance':json.dumps(context).encode()}),path)
    catalog = json.loads((root/'catalog.json').read_text())
    catalog['tables']['6']['static']['sha256'] = sha256_file(path)
    catalog['audit_data'] = {'6':{'static':context['app_only_audit']}}
    (root/'catalog.json').write_text(json.dumps(catalog))
    before = Path(context['app_only_audit']['path']).read_bytes()
    with workspace_scope(workspace):
        assert cleanup_workspace_data(root) is False
    assert Path(context['app_only_audit']['path']).read_bytes() == before
    assert validate_products(root)['status'] == 'passed'
    # Explicit conversion leaves only self-contained final products; historical
    # input evidence remains untouched by conversion itself.
    compact_products(root)
    assert Path(context['app_only_audit']['path']).read_bytes() == before
    assert 'audit_data' not in json.loads((root/'catalog.json').read_text())
