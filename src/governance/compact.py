"""Offline, reversible projection of an existing validated delivery."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import UTC, datetime
import warnings

import pyarrow.parquet as pq

from .app_contract import contract
from .app_only import compact_table, upgrade_table
from .products import METADATA_KEY, _json, validate_metric_table, validate_products
from .shared.artifacts import sha256_file


def compact_products(directory, *, audit_directory=None):
    """Keep selected columns with support embedded in the final Parquet files.

    Legacy external audits are read and preserved; new sidecars are never made.
    """
    root = Path(directory).resolve()
    if audit_directory is not None:
        warnings.warn('audit_directory is deprecated; support is embedded in final Parquets', DeprecationWarning, stacklevel=2)
    lock = root.parent / f'.{root.name}.update.lock'
    with lock.open('x'):
        pass
    try:
        validate_products(root)
        catalog = json.loads((root / 'catalog.json').read_text())
        schemas = [pq.read_schema(root / binding['path']).metadata for variants in catalog['tables'].values() for binding in variants.values()]
        already = ['embedded_support' in json.loads(meta[METADATA_KEY]) for meta in schemas]
        if all(already):
            return validate_products(root)
        before = {'catalog.json': sha256_file(root / 'catalog.json')}
        with tempfile.TemporaryDirectory(prefix=f'.{root.name}.compact-', dir=root.parent) as temporary:
            stage = Path(temporary)
            names = []
            for resolution, variants in catalog['tables'].items():
                for kind, binding in variants.items():
                    name = binding['path']
                    table = pq.read_table(root / name)
                    metadata = json.loads(table.schema.metadata[METADATA_KEY])
                    if 'app_only_audit' in metadata or 'embedded_support' in metadata:
                        public, context = upgrade_table(table, metadata)
                    else:
                        public, context = compact_table(table, metadata)
                    validate_metric_table(public, context)
                    pq.write_table(public.replace_schema_metadata({**(public.schema.metadata or {}), METADATA_KEY: _json(context)}), stage / name, compression='zstd')
                    if not public.equals(pq.read_table(stage / name), check_metadata=False):
                        raise ValueError('Compact Parquet readback mismatch')
                    before[name] = binding['sha256']
                    binding['sha256'] = sha256_file(stage / name)
                    catalog.setdefault('support_data', {}).setdefault(resolution, {})[kind] = context['embedded_support']
                    names.append(name)
            catalog['application_contract'] = contract()
            catalog.pop('audit_data', None)
            catalog['compacted_at_utc'] = datetime.now(UTC).isoformat()
            (stage / 'catalog.json').write_bytes(_json(catalog) + b'\n')
            names.append('catalog.json')
            backup = stage / 'previous'
            backup.mkdir()
            for name in names:
                if sha256_file(root / name) != before[name]:
                    raise ValueError('Governance changed during compaction')
                shutil.copy2(root / name, backup / name)
            try:
                for name in names:
                    os.replace(stage / name, root / name)
                result = validate_products(root)
            except BaseException:
                for name in names:
                    os.replace(backup / name, root / name)
                raise
        return result
    finally:
        lock.unlink(missing_ok=True)
