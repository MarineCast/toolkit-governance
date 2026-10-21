# Marine Conservation Areas

Recorded marine conservation sites, their designated count/coverage and a broader assignment view that also labels proposed and interim references.

## Sources and processing

This interface reuses original NOAA inventory/sanctuary, Canadian conservation/designation and qualified refuge sources; it adds no download source. Explicit marine classifications or reviewed marine-site crosswalks determine eligibility. Reviewed site identities reconcile supported duplicates; unresolved identities stay separate. Coverage unions eligible polygons within the full H3 cell and divides by full cell area in EPSG:6933. Mixed marine/terrestrial site extents remain whole recorded boundaries.

Authoritative acquisition, rights and provider qualifications:

- [marine conservation areas source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/marine_conservation_areas/DATA_SOURCES.md)
- [marine protected areas source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/marine_protected_areas/DATA_SOURCES.md)
- [conservation designations source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/conservation_designations/DATA_SOURCES.md)
- [wildlife refuges source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/wildlife_refuges/DATA_SOURCES.md)
- [national marine sanctuaries source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/national_marine_sanctuaries/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| Marine Conservation Area Count | `marine_conservation_areas__recorded_feature_count` | int64 / count |
| Marine Conservation Area Coverage | `marine_conservation_areas__recorded_polygon_union_area_fraction` | double / fraction |
| Marine Conservation Area Assignment | `marine_conservation_assignment__feature_memberships_v1` | governance_memberships_v1 / recorded membership |

### Marine Conservation Area Count

Recorded existing/designated marine conservation sites, with PA, OECM and other designations kept distinct; not a count of legally equivalent MPAs or proof of current law. Proposed AOIs and interim zones are excluded. Marine scope requires explicit provider marine classification or a reviewed marine-site crosswalk. Mixed marine/terrestrial NOAA site and matched FWS boundaries retain their full recorded extents. Unresolved cross-inventory identities remain separate; unmatched FWS marine scope is unqualified. Positive results are partial inventory summaries; no-hit cells remain unknown, never zero.

### Marine Conservation Area Coverage

Union of all eligible source polygons intersected with full H3 polygon / full H3 polygon area in EPSG:6933. Overlapping sites and duplicate inventory boundaries are never summed. Recorded existing/designated marine conservation sites, with PA, OECM and other designations kept distinct; not a count of legally equivalent MPAs or proof of current law. Proposed AOIs and interim zones are excluded. Marine scope requires explicit provider marine classification or a reviewed marine-site crosswalk. Mixed marine/terrestrial NOAA site and matched FWS boundaries retain their full recorded extents. Unresolved cross-inventory identities remain separate; unmatched FWS marine scope is unqualified. Positive results are partial inventory summaries; no-hit cells remain unknown, never zero.

### Marine Conservation Area Assignment

All designated marine conservation site memberships plus explicitly labeled Proposed and Interim references. Reference display IDs qualify the original site ID by status; original source records, site IDs and geometry part IDs remain retained. The same site may have designated and interim zones. Assignment entries are not the Marine Conservation Area Count. Proposed/interim references remain excluded from that designated Count and Coverage. Race Rocks AOI is a point; no boundary or area is inferred. Stripes show overlapping memberships, not area shares. Missing component support remains unknown.

The combined `marine_conservation_assignment__feature_memberships_v1` is a derived display field. Physical designated and proposed/interim membership columns remain separate in the [handoff schema](../reference/columns.md).

## Identity and missingness

PA, OECM, sanctuary and other designation classes remain distinct. Assignment includes explicitly labeled Proposed and Interim entries, but designated Count and Coverage exclude them. Reference display IDs qualify site identity by status; a site can have designated and interim zones. Race Rocks AOI remains a point with no invented area. Membership stripes indicate overlap, not shares of cell area.

Memberships retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
