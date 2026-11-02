"""Validate source-supported presence and qualified absence independently of storage."""


def validate_presence_flags(table, metadata):
    from ..jurisdiction.tribal_first_nations_areas.interface import AREA, ASSIGNMENT, COMPONENTS, _complete as tribal_complete
    from ..jurisdiction.international_boundary import COLUMN, MEMBERS, GROUP, _complete as boundary_complete
    from ..vessel_management.presentation import PRESENCE, SEPARATION, GROUPS, _complete as routing_complete

    fields, coverage = metadata['fields'], metadata.get('coverage', {})
    specifications = {
        AREA: ([ASSIGNMENT], lambda: all(tribal_complete(coverage, group) for group in COMPONENTS)),
        PRESENCE: ([SEPARATION + '__feature_memberships_v1', 'speed_restriction_zones__feature_memberships_v1'],
                   lambda: all(routing_complete(coverage, group) for group in GROUPS)),
        COLUMN: ([MEMBERS], lambda: boundary_complete(coverage.get(GROUP, {}), table['h3_index'].to_pylist(),
                    fields[COLUMN].get('original_source_bindings', {}))),
    }
    for flag, (members, complete) in specifications.items():
        if flag not in table.column_names:
            continue
        rows, states = [], []
        for name in members:
            rows.append(table[name].to_pylist() if name in table.column_names else [None] * table.num_rows)
            status = fields.get(name, {}).get('missing_reason_field')
            states.append(table[status].to_pylist() if status else [None] * table.num_rows)
        qualified = None
        status_column = fields[flag].get('missing_reason_field')
        flag_states = table[status_column].to_pylist() if status_column else [None] * table.num_rows
        for i, value in enumerate(table[flag].to_pylist()):
            positive = any(bool(row[i]) for row in rows)
            if positive:
                if value is not True:
                    raise ValueError(f'Boolean overlap contradicts positive membership: {flag}')
            elif value is True:
                raise ValueError(f'Boolean overlap lacks positive membership: {flag}')
            elif value is False:
                if qualified is None:
                    qualified = complete()
                if (not qualified or flag_states[i] != 'observed'
                        or not all(row[i] == [] for row in rows)
                        or not all(state[i] == 'observed' for state in states)):
                    raise ValueError(f'Boolean absence requires complete observed empty support: {flag}')
