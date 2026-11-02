from governance.vessel_management.fixed_rules import normalize as normalize_rules

def normalize(frame, source):
    from .qualified import SOURCES, normalize as normalize_qualified
    if source.source_id in SOURCES:
        return normalize_qualified(frame, source)
    from .washington import SOURCE_ID, normalize as normalize_washington
    if source.source_id == SOURCE_ID:
        return normalize_washington(frame, source)
    return normalize_rules(frame, source, collection='exclusion_zones')
