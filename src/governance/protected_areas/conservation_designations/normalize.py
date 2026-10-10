"""ECCC-reported marine classification views; no cross-country protection taxonomy."""
from governance.shared.normalization import base_record, clean, records_frame

# Exact combinations qualified in the bounded CPCAD source roster, not invented legal classes.
CLASSIFICATIONS = {
    (1, 1): ('reported_pa_designated', 'Protected area (PA)', 'Designated'),
    (2, 1): ('reported_oecm_designated', 'Other effective area-based conservation measure (OECM)', 'Designated'),
    (3, 3): ('reported_interim_pa', 'Interim - protected area (PA)', 'Interim'),
    (5, 1): ('reported_not_applicable_designated', 'Not applicable', 'Designated'),
}


def integer(value, field):
    try:
        result = int(value)
        if float(value) != result:
            raise ValueError()
        return result
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'Valid CPCAD {field} integer required') from None


def evidence_key(parent, zone):
    return f'cpcad:parent:{integer(parent, "PARENT_ID")}:zone:{integer(zone, "ZONE_ID")}'


def normalize(frame, source):
    if source.source_id != 'eccc_marine_classification':
        raise ValueError(f'Unsupported classification source: {source.source_id}')
    rows, seen = [], set()
    for _, row in frame.iterrows():
        if clean(row.get('BIOME')) != 'M':
            raise ValueError('CPCAD classification scope is explicitly marine only')
        pair = (integer(row.get('PA_OECM_DF'), 'PA_OECM_DF'), integer(row.get('STATUS'), 'STATUS'))
        if pair not in CLASSIFICATIONS:
            raise ValueError(f'Unqualified CPCAD classification/status combination: {pair}')
        role, class_label, status_label = CLASSIFICATIONS[pair]
        oid = integer(row.get('OBJECTID'), 'OBJECTID')
        if oid in seen:
            raise ValueError('Duplicate CPCAD source OBJECTID')
        seen.add(oid)
        key = evidence_key(row.get('PARENT_ID'), row.get('ZONE_ID'))
        record = base_record(source, source_feature_id=f'{source.source_id}:{oid}',
            governance_feature_id=key, feature_name=clean(row.get('NAME_E')),
            feature_type='provider_reported_marine_classification_zone', authority=source.provider,
            jurisdiction='Canadian provider inventory; no legal applicability inference',
            legal_authority=None, legal_source_url=None, source_coverage_status='partial_source_selected_marine_inventory')
        record.update(LEGAL_AUTHORITY=None, LEGAL_SOURCE_URL=None, CLASSIFICATION_ROLE=role,
                      PROVIDER_CLASS_LABEL=class_label, PROVIDER_STATUS_LABEL=status_label,
                      PROVIDER_EVIDENCE_KEY=key,
                      EVIDENCE_OVERLAP_POLICY='Classification view, not incremental protected coverage; join parent/zone IDs to existing MPA/refuge evidence and never sum family totals.',
                      geometry=row.geometry)
        for name, value in row.items():
            if name != frame.geometry.name:
                record['ECCC_' + name] = clean(value)
        rows.append(record)
    return records_frame(rows, frame.crs)


def metric_groups(collection='conservation_designations'):
    return {f'{collection}__{spec[0]}': {'collection': collection, 'role': spec[0],
            'role_field': 'CLASSIFICATION_ROLE', 'source_id': 'eccc_marine_classification',
            'description': f'ECCC reported marine classification: {spec[1]} / {spec[2]}',
            'geometry_family': 'polygon', 'identity': 'Distinct provider parent/zone keys, not parent-site counts or newly protected areas. Provider Not applicable is a classification, not a metric missingness state.',
            'overlap_policy': 'Non-additive classification view. Union within this reported class/status only; parent/zone IDs and the release evidence crosswalk identify existing refuge evidence. Never sum with MPA/refuge metrics or claim incremental protected coverage.'}
            for spec in CLASSIFICATIONS.values()}
