from governance.vessel_management.routing import normalize as normalize_routing

def normalize(frame, source):
    return normalize_routing(frame, source, collection='traffic_separation_schemes')
