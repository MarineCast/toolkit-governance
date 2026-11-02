"""Replay reviewed popup qualifications only for their exact source/grid support.

The packaged receipt is historical evidence, not a new mask measurement or source
fetch. A changed source, geometry or native grid cannot inherit its distance claim.
"""
import hashlib
import json
from importlib.resources import files
from pathlib import Path

import pyarrow.parquet as pq

MASK_LIMITATION = ('Reporting-mask support must be checked for the supplied grid; '
                   'full H3 support does not imply water-only overlap.')


def grid_digest(ids):
    return hashlib.sha256(json.dumps(sorted(ids), separators=(',', ':')).encode()).hexdigest()


def replay_qualifications(table, metadata, original_root, context, *, receipt=None):
    if receipt is None:
        receipt = json.loads(files('governance').joinpath(
            'resources/exclusion_replay_qualification_20261019.json').read_text())
    if receipt.get('schema_version') != 1:
        raise ValueError('Unsupported exclusion qualification receipt')
    ids = table['h3_index'].to_pylist() if 'h3_index' in table.column_names else []
    grid = receipt['grids'].get(str(metadata.get('spatial', {}).get('h3_resolution')), {})
    grid_matches = (len(ids) == grid.get('rows') and len(ids) == len(set(ids))
                    and grid_digest(ids) == grid.get('sorted_h3_ids_sha256'))
    root = Path(original_root).resolve()
    applied = []
    for identity, evidence in receipt['records'].items():
        if identity not in context:
            continue
        # Drop a prior copy of this receipt's facts until its bindings pass again.
        # Never carry a historical distance or source-pin assertion onto changed support.
        for key, value in evidence['facts'].items():
            if context[identity].get(key) == value:
                context[identity].pop(key)
        sid = evidence['source_id']
        if metadata.get('sources', {}).get(sid, {}).get('snapshot_sha256') != evidence['source_snapshot_sha256']:
            continue
        spatial = 'study_water_mask_distance_m' in evidence['facts']
        if spatial and not grid_matches:
            continue
        binding = metadata.get('original_data', {}).get(sid)
        if not binding:
            continue
        path = (root / binding['path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Exclusion qualification original path escapes root')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != binding['sha256']:
                raise ValueError('Exclusion qualification original checksum mismatch')
        identity_column = evidence['identity_column']
        rows = pq.read_table(path, columns=[identity_column, 'geometry']).to_pylist()
        match = [row for row in rows if row[identity_column] == evidence['identity_value']]
        if (len(match) != 1 or match[0]['geometry'] is None or
                hashlib.sha256(match[0]['geometry']).hexdigest() != evidence['geometry_wkb_sha256']):
            continue
        context[identity].update(evidence['facts'])
        applied.append(identity)
        if spatial:
            for name in ('exclusion_zones__recorded_feature_count', 'exclusion_zones__feature_memberships_v1'):
                for key in ('support_limitation', 'interpretation'):
                    value = metadata['fields'].get(name, {}).get(key)
                    if value:
                        metadata['fields'][name][key] = value.replace(MASK_LIMITATION, receipt['qualified_mask_limitation'])
    if applied:
        metadata.setdefault('exclusion_zone_interface', {})['qualification_replay'] = {
            'reviewed_at_utc': receipt['reviewed_at_utc'],
            'evidence': receipt['evidence'], 'records': applied,
            'grid_binding': grid if grid_matches else None,
            'meaning': 'Retained reviewed evidence for matching source snapshots and geometry; mask distance additionally requires exact native H3 support. No new source currentness or mask measurement.'}
