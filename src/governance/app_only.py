"""Selected product columns with lossless scientific support in the final file.

The audit is a lossless partition of removed arrays, not another copy of sources.
Readers never need an application checkout to reconstruct the scientific table.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import zlib

import pyarrow as pa
import pyarrow.parquet as pq

from .app_contract import contract
from .app_view import combine_conservation, project_names, NAME_POLICY
from .shared.artifacts import sha256_file

AUDIT_KEY = b'governance_app_audit'
AUDIT_SCHEMA = 'governance.app.audit.v1'
SUPPORT_KEY = b'governance_support'
SUPPORT_SCHEMA = 'governance.embedded_support.v1'


def display_table(table, metadata, naming_version=5):
    """Materialize the app's selected view without changing input arrays."""
    view, context = combine_conservation(table, metadata)
    columns = [name for name in contract()['legacy_columns'] if name in view.column_names]
    if metadata['temporal']['type'] == 'dynamic':
        columns.insert(1, 'date')
    selected = view.select(columns)
    if naming_version >= 3:
        aliases = contract()['column_aliases']
        selected = selected.rename_columns([aliases.get(name, name) for name in columns])
        context = {**context, 'fields': {aliases.get(name, name): value for name, value in context['fields'].items()}}
    if naming_version >= 4:
        selected, context = project_names(selected, context)
    if naming_version >= 5:
        context = {**context, 'fields': {name: {**field, 'definition': field['definition'].replace('external audit', 'embedded scientific support')}
                   if name.endswith('_membership') else field for name, field in context['fields'].items()}}
    return selected, context


def compact_table(table, metadata, audit_directory=None, *, naming_version=5):
    """Retain support inside the product; v2–v4 writing is legacy compatibility."""
    if 'app_only_audit' in metadata or 'embedded_support' in metadata:
        raise ValueError('Already compact; restore support before projecting again')
    public, view = display_table(table, metadata, naming_version=naming_version)
    keys = ['h3_index'] + (['date'] if 'date' in table.column_names else [])
    retained = {old for old, new in contract()['column_aliases'].items() if new in public.column_names
                and not (naming_version >= 4 and new.endswith('_membership'))}
    removed = [name for name in table.column_names if name not in retained and name not in keys]
    audit = table.select(keys + removed)
    header = {'schema': AUDIT_SCHEMA, 'original_columns': table.column_names,
              'original_schema': base64.b64encode(table.schema.remove_metadata().serialize().to_pybytes()).decode(),
              'original_metadata': metadata}
    audit = audit.replace_schema_metadata({AUDIT_KEY: json.dumps(header, sort_keys=True).encode()})
    if naming_version == 5:
        # Compress the whole support member, including its scientific dictionary.
        # It is metadata of the final Parquet, never a retained sidecar file.
        buffer = pa.BufferOutputStream()
        pq.write_table(audit, buffer, compression='zstd')
        payload = zlib.compress(buffer.getvalue().to_pybytes())
        public = public.replace_schema_metadata({SUPPORT_KEY: payload})
        binding = {'schema': SUPPORT_SCHEMA, 'encoding': 'zlib_parquet_v1',
                   'sha256': hashlib.sha256(payload).hexdigest(),
                   'rows': audit.num_rows, 'columns': audit.column_names}
    else:
        if naming_version not in (2, 3, 4) or audit_directory is None:
            raise ValueError('Legacy support writing requires version 2–4 and an audit directory')
        directory = Path(audit_directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        kind = metadata['temporal']['type']
        path = directory / f"governance-r{metadata['spatial']['h3_resolution']}-{kind}-audit.parquet"
        with path.open('xb') as stream:
            pq.write_table(audit, stream, compression='zstd')
        binding = {'schema': AUDIT_SCHEMA, 'path': str(path), 'sha256': sha256_file(path),
                   'rows': audit.num_rows, 'columns': audit.column_names}
    context = copy.deepcopy(metadata)
    context['fields'] = {name: view['fields'][name] for name in public.column_names}
    context['embedded_support' if naming_version == 5 else 'app_only_audit'] = binding
    context['application_contract'] = {
        'version': naming_version,
        'column_aliases': contract()['column_aliases'], 'columns': public.column_names, 'supported_resolutions': contract()['resolutions'],
        'compatibility_columns': [], 'support_storage': 'embedded_governance_support_v1' if naming_version == 5 else 'external_governance_app_audit_v1',
        'identity_policy': 'Source-qualified records, overlapping memberships and native part IDs retained unchanged',
    }
    if naming_version >= 4:
        context['application_contract']['membership_representation'] = NAME_POLICY
    # Verify disk readback, the lossless partition and the derived display field.
    restored, original = restore_support(public, context)
    if not restored.equals(table, check_metadata=False) or original != metadata:
        raise ValueError('Scientific audit reconstruction mismatch')
    return public, context


def restore_support(table, metadata):
    """Verify and restore removed arrays, with exact H3/date row alignment."""
    embedded = 'embedded_support' in metadata
    legacy = 'app_only_audit' in metadata
    if not embedded and not legacy:
        if metadata.get('application_contract', {}).get('version') in (2, 3, 4, 5):
            raise ValueError('Projected governance requires scientific support')
        return table, metadata
    if embedded and legacy:
        raise ValueError('Multiple governance support bindings')
    binding = metadata['embedded_support' if embedded else 'app_only_audit']
    if not isinstance(binding, dict):
        raise ValueError('Unsupported governance support binding')
    application = metadata.get('application_contract', {})
    version = application.get('version', 2)
    if embedded:
        if version != 5 or binding.get('schema') != SUPPORT_SCHEMA or binding.get('encoding') != 'zlib_parquet_v1':
            raise ValueError('Unsupported embedded governance support binding')
    elif version not in (2, 3, 4) or binding.get('schema') != AUDIT_SCHEMA or not Path(binding['path']).is_absolute():
        raise ValueError('Unsupported governance audit binding')
    aliases = contract()['column_aliases'] if version >= 3 else {}
    if version >= 3 and application.get('column_aliases') != aliases:
        raise ValueError('Governance column alias mapping mismatch')
    if version >= 4 and application.get('membership_representation') != NAME_POLICY:
        raise ValueError('Governance membership name policy mismatch')
    inverse = {new: old for old, new in aliases.items()}
    native = table.rename_columns([inverse.get(name, name) for name in table.column_names])
    if embedded:
        payload = (table.schema.metadata or {}).get(SUPPORT_KEY)
        if payload is None or hashlib.sha256(payload).hexdigest() != binding['sha256']:
            raise ValueError('Governance embedded support checksum mismatch')
        audit = pq.read_table(pa.BufferReader(zlib.decompress(payload)))
    else:
        path = Path(binding['path'])
        if sha256_file(path) != binding['sha256']:
            raise ValueError('Governance audit checksum mismatch')
        audit = pq.read_table(path)
        if sha256_file(path) != binding['sha256']:
            raise ValueError('Governance audit changed during read')
    if audit.num_rows != binding['rows'] or audit.column_names != binding['columns'] or audit.num_rows != table.num_rows:
        raise ValueError('Governance audit shape mismatch')
    header = json.loads(audit.schema.metadata[AUDIT_KEY])
    if header['schema'] != AUDIT_SCHEMA:
        raise ValueError('Unsupported governance audit schema')
    keys = ['h3_index'] + (['date'] if 'date' in table.column_names else [])
    # Dynamic rows may repeat H3; join on both keys without serializing identities.
    source_keys = audit.select(keys).to_pandas()
    target_keys = table.select(keys).to_pandas()
    if source_keys.duplicated().any() or target_keys.duplicated().any():
        raise ValueError('Duplicate governance audit identity')
    source_keys['_audit_row'] = range(audit.num_rows)
    joined = target_keys.merge(source_keys, on=keys, how='left', validate='one_to_one', sort=False)
    if joined['_audit_row'].isna().any():
        raise ValueError('Governance audit identity mismatch')
    audit = audit.take(pa.array(joined['_audit_row'].tolist(), pa.int64()))
    schema = pa.ipc.read_schema(pa.BufferReader(base64.b64decode(header['original_schema'])))
    if schema.names != header['original_columns']:
        raise ValueError('Governance original schema mismatch')
    arrays = []
    for field in schema:
        source = audit if version >= 4 and field.name.endswith('__feature_memberships_v1') else native if field.name in native.column_names else audit
        if source[field.name].type != field.type:
            raise ValueError('Governance original field type mismatch')
        arrays.append(source[field.name])
    restored = pa.Table.from_arrays(arrays, schema=schema)
    expected, context = display_table(restored, header['original_metadata'], naming_version=version)
    if not expected.equals(table, check_metadata=False):
        raise ValueError('Governance public view differs from audited scientific values')
    expected_fields = {name: context['fields'][name] for name in expected.column_names}
    if expected_fields != metadata['fields']:
        raise ValueError('Governance public field definitions differ from audit')
    return restored, header['original_metadata']


def rename_table(table, metadata):
    """Alias v2 app-only columns, preserving its immutable audit binding."""
    original, context = restore_support(table, metadata)
    public, view = display_table(original, context, naming_version=3)
    updated = copy.deepcopy(metadata)
    updated['fields'] = {name: view['fields'][name] for name in public.column_names}
    updated['application_contract'].update(version=3, columns=public.column_names,
                                            column_aliases=contract()['column_aliases'])
    restored, _ = restore_support(public, updated)
    if not restored.equals(original, check_metadata=False):
        raise ValueError('Renamed governance scientific values changed')
    return public, updated


def upgrade_table(table, metadata, audit_directory=None):
    """Upgrade a typed app-only table to names while retaining native structs."""
    original, context = restore_support(table, metadata)
    return compact_table(original, context, audit_directory)
