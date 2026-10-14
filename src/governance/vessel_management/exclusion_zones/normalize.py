from governance.vessel_management.fixed_rules import normalize as normalize_rules

def normalize(frame, source):
    return normalize_rules(frame, source, collection='exclusion_zones')
