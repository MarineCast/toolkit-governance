# Physical columns and display support

This reference follows the packaged `app_contract.json`; use that machine-readable resource for validation. The same schema applies at each declared application resolution. Values and source identities retain the [product contract](../parquet-products.md).

| Physical column | Role |
| --- | --- |
| `h3_index` | Row identity |
| `coast_guard_sectors__feature_memberships_v1` | Typed paired membership |
| `coast_guard_sectors__feature_memberships_v1_status` | Support state |
| `coast_guard_sectors__recorded_feature_count` | Declared value or paired support count |
| `coast_guard_sectors__recorded_feature_count_status` | Support state |
| `county_regional_boundaries__feature_memberships_v1` | Typed paired membership |
| `county_regional_boundaries__recorded_feature_count` | Declared value or paired support count |
| `critical_habitat__feature_memberships_v1` | Typed paired membership |
| `critical_habitat__feature_memberships_v1_status` | Support state |
| `critical_habitat__recorded_feature_count` | Declared value or paired support count |
| `critical_habitat__recorded_feature_count_status` | Support state |
| `exclusion_zones__feature_memberships_v1` | Typed paired membership |
| `exclusion_zones__feature_memberships_v1_status` | Support state |
| `exclusion_zones__recorded_feature_count` | Declared value or paired support count |
| `exclusion_zones__recorded_feature_count_status` | Support state |
| `federal_waters__assignment__feature_memberships_v1` | Typed paired membership |
| `federal_waters__assignment__feature_memberships_v1_status` | Support state |
| `federal_waters__assignment__recorded_feature_count` | Declared value or paired support count |
| `federal_waters__assignment__recorded_feature_count_status` | Support state |
| `federal_waters__international_boundary` | Declared value or paired support count |
| `federal_waters__international_boundary__feature_memberships_v1` | Typed paired membership |
| `federal_waters__international_boundary__feature_memberships_v1_status` | Support state |
| `federal_waters__international_boundary__recorded_feature_count` | Declared value or paired support count |
| `federal_waters__international_boundary__recorded_feature_count_status` | Support state |
| `federal_waters__international_boundary_status` | Support state |
| `management_areas__feature_memberships_v1` | Typed paired membership |
| `management_areas__recorded_feature_count` | Declared value or paired support count |
| `marine_conservation_areas__feature_memberships_v1` | Typed paired membership |
| `marine_conservation_areas__feature_memberships_v1_status` | Support state |
| `marine_conservation_areas__recorded_feature_count` | Declared value or paired support count |
| `marine_conservation_areas__recorded_feature_count_status` | Support state |
| `marine_conservation_areas__recorded_polygon_union_area_fraction` | Declared value or paired support count |
| `marine_conservation_areas__recorded_polygon_union_area_fraction_status` | Support state |
| `proposed_interim_conservation_references__feature_memberships_v1` | Typed paired membership |
| `proposed_interim_conservation_references__feature_memberships_v1_status` | Support state |
| `proposed_interim_conservation_references__recorded_feature_count` | Declared value or paired support count |
| `proposed_interim_conservation_references__recorded_feature_count_status` | Support state |
| `speed_restriction_zones__feature_memberships_v1` | Typed paired membership |
| `speed_restriction_zones__feature_memberships_v1_status` | Support state |
| `speed_restriction_zones__recorded_feature_count` | Declared value or paired support count |
| `speed_restriction_zones__recorded_feature_count_status` | Support state |
| `state_provincial_waters__assignment__feature_memberships_v1` | Typed paired membership |
| `state_provincial_waters__assignment__feature_memberships_v1_status` | Support state |
| `state_provincial_waters__assignment__recorded_feature_count` | Declared value or paired support count |
| `state_provincial_waters__assignment__recorded_feature_count_status` | Support state |
| `tribal_first_nations_areas__feature_memberships_v1` | Typed paired membership |
| `tribal_first_nations_areas__feature_memberships_v1_status` | Support state |
| `tribal_first_nations_areas__mapped_area` | Declared value or paired support count |
| `tribal_first_nations_areas__mapped_area_status` | Support state |
| `tribal_first_nations_areas__recorded_feature_count` | Declared value or paired support count |
| `tribal_first_nations_areas__recorded_feature_count_status` | Support state |
| `vessel_routing_regulations__recorded_reference` | Declared value or paired support count |
| `vessel_routing_regulations__recorded_reference_status` | Support state |
| `vessel_routing_regulations__shipping_lanes__feature_memberships_v1` | Hidden compatibility support |
| `vessel_routing_regulations__shipping_lanes__feature_memberships_v1_status` | Hidden compatibility support |
| `vessel_routing_regulations__shipping_lanes__recorded_feature_count` | Hidden compatibility support |
| `vessel_routing_regulations__shipping_lanes__recorded_feature_count_status` | Hidden compatibility support |
| `vessel_routing_regulations__traffic_separation_zones__feature_memberships_v1` | Typed paired membership |
| `vessel_routing_regulations__traffic_separation_zones__feature_memberships_v1_status` | Support state |
| `vessel_routing_regulations__traffic_separation_zones__recorded_feature_count` | Declared value or paired support count |
| `vessel_routing_regulations__traffic_separation_zones__recorded_feature_count_status` | Support state |

## Derived display fields

These are constructed by the declared application presentation contract rather than stored as additional physical columns:

- `marine_conservation_assignment__feature_memberships_v1`
- `county_regional_boundaries__feature_memberships_v1_status`
- `county_regional_boundaries__recorded_feature_count_status`
- `management_areas__feature_memberships_v1_status`
- `management_areas__recorded_feature_count_status`
- `marine_conservation_assignment__feature_memberships_v1_status`
- `marine_conservation_assignment__recorded_feature_count`
