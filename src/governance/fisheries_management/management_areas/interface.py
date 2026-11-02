"""Two-column Management Areas contract; source records remain in memberships."""
from __future__ import annotations

from governance.memberships import validate_memberships

GROUP = 'management_areas'
COUNT = GROUP + '__recorded_feature_count'
ASSIGNMENT = GROUP + '__feature_memberships_v1'
SUPPORT = 'uniform_count_membership_support_v1'
STATES = ('observed', 'partial', 'unknown', 'unavailable', 'not_applicable')
SCIENTIFIC_FEATURES = {
    COUNT: {'display_name': 'Management Area Count'},
    ASSIGNMENT: {'display_name': 'Management Area'},
}


def compact_features(table, fields, coverage):
    """Remove other derived fields without changing values, identities or support."""
    if COUNT not in table.column_names:
        return table
    if ASSIGNMENT not in table.column_names:
        raise ValueError('Management Areas requires both count and memberships')
    states = set()
    for name in SCIENTIFIC_FEATURES:
        descriptor = fields[name]
        if descriptor.get('implicit_support') == SUPPORT:
            states.add(descriptor.get('implicit_status'))
        else:
            states.update(table[descriptor['missing_reason_field']].to_pylist())
    if len(states) != 1 or not states.issubset(STATES):
        raise ValueError('Management Areas support must be uniform and shared by count/memberships')
    state = states.pop()
    for name, presentation in SCIENTIFIC_FEATURES.items():
        fields[name].pop('missing_reason_field', None)
        fields[name].update(presentation, map_feature=True, implicit_support=SUPPORT, implicit_status=state)
    removed = [name for name in table.column_names
               if name.startswith(GROUP + '__') and name not in SCIENTIFIC_FEATURES]
    table = table.drop(removed)
    for name in removed:
        fields.pop(name, None)
    coverage[GROUP].update(support_encoding=SUPPORT, metric_support_state=state)
    validate_memberships(table, fields)
    return table
