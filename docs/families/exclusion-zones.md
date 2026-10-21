# Exclusion Zones

Partial static references to named activity restrictions, with count and all overlapping assignments. Geometry does not certify that a restriction is active for a particular vessel or date.

## Sources and processing

Sources include Transport Canada coordinate-ring instruments, USCG/USACE rule references, NOAA chart references, DFO fishing closures, Washington harvest references, DND/CCG active-area references and named FWS access restrictions. Processing retains the evidence class for each geometry: parsed instrument coordinates, checked agency diagrams or provider reference geometry. Positive-dimensional intersections count a distinct source-qualified feature once.

Authoritative acquisition, rights and provider qualifications:

- [exclusion zones source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/vessel_management/exclusion_zones/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| Exclusion Zone Count | `exclusion_zones__recorded_feature_count` | int64 / count |
| Exclusion Zone Assignment | `exclusion_zones__feature_memberships_v1` | governance_memberships_v1 / recorded membership |

### Exclusion Zone Count

Distinct source-backed feature IDs with positive-dimensional intersections

### Exclusion Zone Assignment

One entry per distinct GOVERNANCE_FEATURE_ID with positive-dimensional cell intersection; paired source records retain labels and sorted intersecting native part IDs

## Identity and missingness

Vessel entry, seabed disturbance/anchoring, fishing and landing access are separate activities; ordinary transit can remain permitted. Keep activation, seasonal intervals, vessel applicability, exceptions, legal citations and evidence gaps attached. Temporary/moving zones and shoreline-dependent boundaries are incomplete. Full-cell intersection can include geometry outside the reporting water mask; it is not water-only coverage.

Memberships retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
