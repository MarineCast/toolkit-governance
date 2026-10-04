"""Explicit adopter mapping against a caller-supplied, pinned shared schema."""
from __future__ import annotations
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from .delivery import validate_delivery
from .shared.artifacts import sha256_file


def export_shared_manifest(artifact: str | Path, local_manifest: str | Path,
                           schema_path: str | Path, *, schema_reference: str) -> Path:
    """Validate an approved reference_geometry schema; preserve native lineage.

    Requires the optional contract extra. A schema is supplied explicitly, never fetched
    silently. No shared core fields are invented and no other quantity is substituted.
    """
    from jsonschema import Draft202012Validator, FormatChecker
    artifact, local_manifest, schema_path = map(Path, (artifact, local_manifest, schema_path))
    validate_delivery(artifact, local_manifest)
    local = json.loads(local_manifest.read_text())
    schema = json.loads(schema_path.read_text())
    if 'reference_geometry' not in schema['properties']['product']['properties']['quantity_kind']['enum']:
        raise ValueError('Shared schema does not admit reference_geometry')
    version = schema['properties']['contract_version']['const']
    if not schema_reference.strip():
        raise ValueError('Pinned schema reference required')
    fields = {}
    arrow = pq.read_schema(artifact)
    for name, info in local['fields'].items():
        dtype = arrow.field(name).type
        field = {'type': 'integer' if pa.types.is_integer(dtype) else 'number' if pa.types.is_floating(dtype) else 'string',
                 'description': info['definition'], 'units': info['units'],
                 'nullable': info['nullable'], 'statistic': 'identity' if name == 'h3_index' or name.endswith('_status') else info['definition']}
        if 'missing_reason_field' in info:
            field['missing_reason_field'] = info['missing_reason_field']
            field['description'] += f". Coverage definition/evidence: {local_manifest.name}#/coverage/{info['coverage_reference']}; native snapshot inventory only."
            field['minimum'] = 0
            if 'area_fraction' in name:
                field['maximum'] = 1
        if 'enum' in info: field['enum'] = info['enum']
        fields[name] = field
    sources = []
    for name, record in local['native_manifests'].items():
        native = record['manifest']
        upstream = native['sources']
        sources.append({'id': native['product'], 'source_version': record['manifest_sha256'],
                        'retrieved_at': local['created_at_utc'],
                        'spatial_coverage': json.dumps(native['resolved_bounds_wgs84']) + '; inventory completeness '+native['source_completeness'],
                        'temporal_coverage': 'Locally read rebuilt native snapshot. Upstream retrieval/effective times remain as recorded, including unknowns; no new provider acquisition implied.',
                        'license': '; '.join(sorted({s['license'] for s in upstream})),
                        'attribution': '; '.join(sorted({s['attribution'] for s in upstream})),
                        'redistribution': 'Local use only in this release; upstream restrictions retained: '+'; '.join(sorted({s['redistribution'] for s in upstream}))})
    manifest = {
        'contract_version': version,
        'product': {'id': local['product_id'], 'version': local['semantic_product_version'],
                    'description': 'Static recorded governance inventory geometry. No legal applicability or completeness claim.', 'quantity_kind': 'reference_geometry'},
        'producer': {'repository': 'toolkit-governance', 'package': 'toolkit-governance',
                     'package_version': local['software']['version'], 'git_sha': local['software']['git_sha'], 'working_tree_dirty': False},
        'identity': {'row_description': local['identity']['grain'], 'primary_key': ['h3_index']},
        'spatial': {'type': 'h3', 'resolution': local['spatial']['h3_resolution'], 'index_fields': ['h3_index'],
                    'support': 'cell', 'crs': 'EPSG:4326', 'domain': 'Exact cell membership in artifact; supplied grid checksum '+local['spatial']['grid']['sha256'],
                    'method': 'Full H3 cell intersection; unioned polygon areas EPSG:6933 and line lengths '+local['spatial']['length_crs']},
        'temporal': local['temporal'], 'fields': fields,
        'provenance': {'created_at': local['created_at_utc'],
                       'configuration': {'description': 'Effective native configuration identity; recover configuration and source lineage via '+local_manifest.name, 'sha256': local['configuration_hash']},
                       'sources': sources,
                       'processing': f"Scientific method {local['scientific_method_version']}; immutable data release {local['data_release_id']}; native manifest and per-metric coverage companion {local_manifest.name} SHA256 {sha256_file(local_manifest)}. Schema {schema_reference} SHA256 {sha256_file(schema_path)}. Native companions preserve feature/part attributes and source authority. All model-ineligible."},
        'artifact': local['artifact'], 'limitations': local['limitations'] + ['Partial inventory estimates have unknown geographic completeness; configured-source receipt is not geographic recall.'],
    }
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    destination = artifact.with_suffix('.shared-manifest.json')
    with destination.open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    return destination
