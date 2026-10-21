# Vessel Routing & Regulations

Two identity layers and one nullable recorded-reference flag describe navigation/routing and fixed speed references.

## Sources and processing

CHS chart-object references and the pinned NOAA vessel-routing inventory retain eight shipping roles and seven traffic-scheme roles. The Shipping Lanes & Traffic Separation Zones display combines their typed memberships while preserving native role and original records. Speed Restriction Zones remains separate and includes the qualified TC Swiftsure fixed ring. The combined boolean derives from retained memberships; it does not pool line lengths and polygon areas.

Authoritative acquisition, rights and provider qualifications:

- [shipping lanes source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/vessel_management/shipping_lanes/DATA_SOURCES.md)
- [traffic separation schemes source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/vessel_management/traffic_separation_schemes/DATA_SOURCES.md)
- [speed restriction zones source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/vessel_management/speed_restriction_zones/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| Routing / regulation recorded | `vessel_routing_regulations__recorded_reference` | bool / boolean |
| Speed Restriction Zones | `speed_restriction_zones__feature_memberships_v1` | governance_memberships_v1 / recorded membership |
| Shipping Lanes & Traffic Separation Zones | `vessel_routing_regulations__traffic_separation_zones__feature_memberships_v1` | governance_memberships_v1 / recorded membership |

### Routing / regulation recorded

True means at least one retained routing/regulation reference feature is recorded in the native cell. This includes navigation lines, recommended routes, traffic-scheme components and seasonal speed references; it does not mean an unconditional mandatory restriction, current activation, vessel-specific applicability or legal compliance. False requires observed empty memberships for every expected component and independently evidenced complete geographic inventory coverage of the full supplied cells. Otherwise no-hit support is null (unknown/unavailable), never inferred false. Identity layers retain all source-qualified IDs, overlaps, source roles, advisory/conditional meanings and original details. Shipping Lanes & Traffic Separation Zones groups all eight shipping roles and seven traffic-scheme roles for display; navigation/recommended routes, boundaries, crossings, lane parts, separation lines, traffic lanes and separation zones retain their native types. Line and polygon memberships are combined as evidence of reference presence, never as pooled area/length coverage. No source acquisition, geometry overlay or artificial daily history is performed.

### Speed Restriction Zones

One entry per distinct GOVERNANCE_FEATURE_ID with positive-dimensional cell intersection; paired source records retain labels and sorted intersecting native part IDs

### Shipping Lanes & Traffic Separation Zones

One entry per distinct GOVERNANCE_FEATURE_ID with positive-dimensional cell intersection; paired source records retain labels and sorted intersecting native part IDs

## Identity and missingness

CHS identity uses object type plus LNAM when available, otherwise snapshot OBJECTID; repeated chart records and ENC_NAME remain paired. NOAA original source FIDs remain retained. These are source object identities, not guaranteed unique physical routes. Recommended routes are not mandatory restrictions. TC speed, season, clause and exceptions remain source attributes; Nitinat coastline-dependent geometry is excluded pending qualified support.

Memberships retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
