"""The retained Explorer contract, shared by production and offline migration.

Projection only removes columns. It never recalculates values, changes a native
identity, or converts an unknown support state into a negative observation.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path


def contract():
    return json.loads(files('governance').joinpath('resources/app_contract.json').read_text())


def project_app_contract(table, metadata):
    """Select approved values and their declared support without altering arrays."""
    specification = contract()
    if metadata['spatial']['h3_resolution'] not in specification['resolutions']:
        raise ValueError('Application products support H3 resolutions 6 and 8')
    available = set(table.column_names)
    if set(metadata.get('collections', {})) == set(specification['source_collections']):
        missing = set(specification['columns']) - available
        if missing:
            raise ValueError(f'Missing production application columns: {sorted(missing)}')
    retained = [name for name in specification['columns'] if name in available]
    fields = metadata['fields']
    # Subset configurations are useful for bounded source builds. Every retained
    # membership must still carry its complete count/status dependency closure.
    for name in retained:
        descriptor = fields[name]
        required = [descriptor.get(key) for key in ('count_field', 'missing_reason_field',
                                                    'support_membership_column')]
        if descriptor.get('membership_schema_version') and descriptor.get('missing_reason_field'):
            required.append(descriptor['count_field'] + '_status')
        missing = [key for key in required if key and key not in retained]
        if missing:
            raise ValueError(f'Incomplete application support for {name}: {missing}')
    metadata['fields'] = {name: fields[name] for name in retained}
    if 'sources' in metadata:
        # Full acquisition receipts/rosters are already checksum-bound in each
        # OriginalData file. Avoid duplicating them in every resolution's footer.
        source_keys = {
            'source_id', 'provider', 'url', 'source_as_of', 'retrieved_at_utc',
            'snapshot_sha256', 'runtime_status', 'configured_status', 'attribution',
            'license', 'legal_citation', 'redistribution', 'authority_scope',
            'limitation', 'coverage', 'temporal_note',
        }
        metadata['sources'] = {
            source: {key: value for key, value in record.items() if key in source_keys}
            for source, record in metadata['sources'].items()
        }
    metadata['application_contract'] = {
        'version': specification['version'],
        'columns': retained,
        'supported_resolutions': specification['resolutions'],
        'compatibility_columns': [name for name in specification['compatibility_columns'] if name in retained],
        'identity_policy': 'Source-qualified records, overlapping memberships and native part IDs retained unchanged',
    }
    return table.select(retained)


def annotate_catalog(catalog, source_records, original_root=None):
    """Add concise source descriptions and explicitly typed date evidence.

    A build timestamp is never a source update. Unstructured source vintage notes
    remain verbatim instead of being guessed into an observation/publication date.
    """
    specification = contract()
    catalog['built_at_utc'] = catalog['last_updated_utc']
    catalog['date_semantics'] = {
        'last_updated_utc': 'Compatibility alias for product build time; not source last-modified',
        'source_updated_at': 'Explicit provider source update evidence only; null when unavailable',
        'observation_date': 'Explicit observation date only; not inferred from retrieval or publication',
        'publication_date': 'Explicit publication date only; not a legal effective date',
        'retrieved_at_utc': 'Source receipt time; not source update or observation time',
    }
    catalog['application_contract'] = specification
    catalog['sources'] = {
        source_id: {
            'description': record.get('authority_scope') or record.get('title') or record.get('source_as_of'),
            'url': record.get('url'),
            'source_updated_at': record.get('source_updated_at') or record.get('source_last_modified'),
            'observation_date': record.get('observation_date'),
            'publication_date': record.get('publication_date'),
            'retrieved_at_utc': record.get('retrieved_at_utc'),
            'source_vintage_note': record.get('source_as_of'),
            'qualification': record.get('limitation'),
        }
        for source_id, record in sorted(source_records.items())
        if source_id in catalog['original_data']
    }
    if original_root is not None:
        import pyarrow.parquet as pq
        for source_id, entry in catalog['sources'].items():
            binding = catalog['original_data'][source_id]
            schema = pq.read_schema(Path(original_root) / binding['path'])
            original = json.loads(schema.metadata[b'governance_original'])
            editing = original.get('receipt', {}).get('metadata_response', {}).get('editingInfo', {})
            # ArcGIS explicitly identifies a data edit, separately from schema
            # and general service edits. Do not infer one from the latter.
            millis = editing.get('dataLastEditDate')
            if isinstance(millis, (int, float)) and not isinstance(millis, bool):
                entry['source_updated_at'] = datetime.fromtimestamp(millis / 1000, UTC).isoformat()
                entry['source_update_evidence'] = {
                    'path': binding['path'],
                    'field': 'governance_original.receipt.metadata_response.editingInfo.dataLastEditDate',
                    'meaning': 'Provider-reported data edit at retrieval; not legal effective time',
                }
