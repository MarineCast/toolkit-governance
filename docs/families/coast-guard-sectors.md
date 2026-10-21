# Coast Guard Sectors

Administrative assignment to recorded USCG sectors and CCG regions, including the explicitly qualified Western BC model-water supplement.

## Sources and processing

USCG sector polygons and CCG region polygons are normalized separately. The final assignment unions their typed membership lists and retains all overlaps. Western is additionally assigned over explicit BC model-water support, with water-source lineage. This supplement is derived; it is not an intersection with the original CCG region boundary. Original CCG geometry remains retained.

Authoritative acquisition, rights and provider qualifications:

- [coast guard sectors source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/administrative_context/coast_guard_sectors/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| Coast Guard Assignment | `coast_guard_sectors__feature_memberships_v1` | governance_memberships_v1 / recorded membership |

### Coast Guard Assignment

Coast Guard administrative assignment: retained CCG region and USCG sector polygon memberships, supplemented by Western over explicit British Columbia model-water support. Added water assignments are derived, not intersections with the original CCG polygon or a legal/operational boundary. Every existing unit and overlap is retained; unmatched cells remain unknown. Counts describe distinct assigned units, not equivalent jurisdictions.

## Identity and missingness

USCG FID and CCG OBJECTID_1 remain paired with source names and native part IDs. A unit count in support metadata is not a count of equivalent operational jurisdictions. USCG redistribution clearance is unresolved; CCG source terms and its cartographic vintage remain in source notes.

Memberships retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
