"""Versioned, paired categorical records for positive-dimensional H3 memberships."""
from __future__ import annotations

import json

import pandas as pd
import pyarrow as pa

RECORD_FIELDS = (
    'source_dataset_id', 'source_feature_id', 'feature_name', 'feature_type',
    'authority', 'jurisdiction', 'region', 'area_system_id', 'area_code',
    'area_title', 'area_hierarchy_level', 'parent_area_code',
)
RECORD_TYPE = pa.struct([
    pa.field(name, pa.string(), nullable=name not in ('source_dataset_id', 'source_feature_id'))
    for name in RECORD_FIELDS
] + [pa.field('geometry_part_ids', pa.list_(pa.field('item', pa.string(), nullable=False)), nullable=False)])
MEMBERSHIP_TYPE = pa.list_(pa.field('item', pa.struct([
    pa.field('feature_id', pa.string(), nullable=False),
    pa.field('records', pa.list_(pa.field('item', RECORD_TYPE, nullable=False)), nullable=False),
]), nullable=False))
SUFFIX = 'feature_memberships_v1'


def qualify_unknown_no_hit(table, columns):
    """Null no-hit support in a partial inventory is unknown, not an observation.

    Preserve observed values/empty memberships and stronger unavailable/error
    reasons. This qualifies support only; it never fills a null measurement.
    """
    import pyarrow.compute as pc
    for name in columns:
        status = name + '_status'
        if name in table.column_names and status in table.column_names:
            unknown = pc.and_(pc.is_null(table[name]), pc.equal(table[status], 'partial'))
            values = pc.if_else(unknown, 'unknown', table[status])
            table = table.set_column(table.column_names.index(status), table.schema.field(status), values)
    return table


def _text(value):
    return None if value is None or pd.isna(value) else str(value)


def prepare_records(native):
    """Normalize each native row once, outside the cell intersection loop."""
    return [(row["GOVERNANCE_FEATURE_ID"], tuple(_text(row.get(name.upper())) for name in RECORD_FIELDS), row["GEOMETRY_PART_ID"])
            for row in native.to_dict("records")]


def memberships(records, indexes):
    """Deduplicate parts by feature and exact paired source/categorical record."""
    features = {}
    for index in sorted(indexes):
        feature_id, values, part_id = records[index]
        feature = features.setdefault(feature_id, {})
        feature.setdefault(values, set()).add(part_id)
    return [
        {'feature_id': feature_id, 'records': [
            dict(zip(RECORD_FIELDS, values), geometry_part_ids=sorted(parts))
            for values, parts in sorted(records.items(), key=lambda pair: json.dumps(pair[0], ensure_ascii=True))
        ]}
        for feature_id, records in sorted(features.items())
    ]


def definition(group):
    return {
        'units': None, 'nullable': True, 'membership_schema_version': 1,
        'definition': 'One entry per distinct GOVERNANCE_FEATURE_ID with positive-dimensional cell intersection; paired source records retain labels and sorted intersecting native part IDs',
        'coverage_reference': group,
        'missing_reason_field': f'{group}__{SUFFIX}_status',
        'count_field': f'{group}__recorded_feature_count',
        'count_semantics': 'List length equals existing distinct feature count; geometry_part_ids are lineage, never a feature count. Repeated source records of one feature remain paired inside records.',
        'missingness': 'Null for no recorded intersection under incomplete support; empty list only for complete support and zero feature count. Null labels are not inferred.',
        'category_semantics': 'feature_type is canonical native category; region only copies native REGION; authority and jurisdiction are distinct. No dominant-area assignment or invented region.',
    }


def validate_memberships(table, fields):
    """Validate exact Arrow types, pairing, deterministic ordering and count support."""
    for name, field in fields.items():
        if 'membership_schema_version' not in field:
            continue
        group, separator, suffix = name.rpartition('__')
        implicit = field.get('implicit_support') == 'positive_partial_null_unknown_v1'
        uniform = field.get('implicit_support') == 'uniform_count_membership_support_v1'
        support_state = field.get('implicit_status')
        if uniform and (group != 'management_areas' or support_state not in ('observed', 'partial', 'unknown', 'unavailable', 'not_applicable')
                        or 'missing_reason_field' in field):
            raise ValueError(f'Invalid compact Management Areas support: {name}')
        null_status = field.get('implicit_null_status')
        if implicit and (group != 'county_regional_boundaries' or null_status not in ('unknown', 'unavailable')
                         or 'missing_reason_field' in field):
            raise ValueError(f'Invalid compact regional support: {name}')
        if not separator or suffix != SUFFIX or any(field.get(key) != expected for key, expected in (
            ('count_field', f'{group}__recorded_feature_count'),
            ('missing_reason_field', None if implicit or uniform else name + '_status'), ('coverage_reference', group),
        )):
            raise ValueError(f'Invalid membership field bindings: {name}')
        if field['membership_schema_version'] != 1 or table[name].type != MEMBERSHIP_TYPE:
            raise ValueError(f'Invalid membership schema: {name}')
        counts = table[field['count_field']].to_pylist()
        if uniform:
            count_field = fields[field['count_field']]
            if (count_field.get('implicit_support') != field['implicit_support']
                    or count_field.get('implicit_status') != support_state
                    or count_field.get('units') != 'count'
                    or not pa.types.is_integer(table[field['count_field']].type)):
                raise ValueError(f'Invalid compact Management Areas count support: {name}')
            statuses = count_statuses = [support_state] * len(counts)
        elif implicit:
            count_field = fields[field['count_field']]
            if (count_field.get('implicit_support') != field['implicit_support']
                    or count_field.get('implicit_null_status') != null_status
                    or not pa.types.is_integer(table[field['count_field']].type)):
                raise ValueError(f'Invalid compact count support: {name}')
            statuses = count_statuses = ['partial' if count is not None else null_status for count in counts]
        else:
            statuses = table[field['missing_reason_field']].to_pylist()
            count_statuses = table[field['count_field'] + '_status'].to_pylist()
        for entries, count, status, count_status in zip(table[name].to_pylist(), counts, statuses, count_statuses):
            if uniform and ((status == 'observed' and count is None) or
                            (status in ('unknown', 'unavailable', 'not_applicable') and count is not None)):
                raise ValueError(f'Invalid compact Management Areas value/support: {name}')
            if status != count_status or (entries is None) != (count is None):
                raise ValueError(f'Membership/count support mismatch: {name}')
            if entries is None:
                continue
            if len(entries) != count or (not entries and status != 'observed') or (implicit and count <= 0):
                raise ValueError(f'Membership/count mismatch: {name}')
            ids = [entry['feature_id'] for entry in entries if entry is not None]
            if len(ids) != len(entries) or any(not isinstance(i, str) or not i for i in ids) or ids != sorted(set(ids)):
                raise ValueError(f'Invalid membership feature identity/order: {name}')
            for entry in entries:
                records = entry['records']
                if not records or any(record is None for record in records):
                    raise ValueError(f'Empty membership source records: {name}')
                keys = []
                for record in records:
                    if any(not record[k] for k in ('source_dataset_id', 'source_feature_id')):
                        raise ValueError(f'Missing membership source identity: {name}')
                    parts = record['geometry_part_ids']
                    if not parts or any(not isinstance(p, str) or not p for p in parts) or parts != sorted(set(parts)):
                        raise ValueError(f'Invalid membership part lineage: {name}')
                    keys.append(json.dumps(tuple(record[k] for k in RECORD_FIELDS), ensure_ascii=True))
                if keys != sorted(set(keys)):
                    raise ValueError(f'Duplicate/unordered membership source records: {name}')
