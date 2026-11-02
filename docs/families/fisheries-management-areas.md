# Fisheries Management Areas

All recorded fisheries management/reporting areas intersecting a cell and the count of their distinct source-qualified feature IDs.

## Sources and processing

WDFW recreational marine areas, DFO Pacific V3.1 subareas and ADF&G groundfish statistical reporting areas retain separate systems. Native normalization keeps original boundaries and attributes; positive-area H3 memberships retain each source record and part. The public interface computes count and assignment, not pooled polygon coverage, line length or point metrics.

Authoritative acquisition, rights and provider qualifications:

- [management areas source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/fisheries_management/management_areas/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| Management Area Count | `fisheries_management_area_count` | int64 / count |
| Management Area | `fisheries_management_area_membership` | list<string> / readable names |

### Management Area Count

Distinct source-backed feature IDs with positive-dimensional intersections

### Management Area

Sorted distinct readable names of recorded features intersecting the cell; full paired source records and native part IDs remain in scientific support embedded in v5 final Parquets (external audits for legacy products).

## Identity and missingness

Codes are qualified by system: WDFW recreational codes, dfo.pacific.pfma.subareas and ADF&G reporting codes are not interchangeable. Qualified DFO subarea zero is a real code, not missingness; original NAME and LABEL discrepancies remain. Subareas do not manufacture whole-area geometry, fishery/gear applicability or legal history. DFO reuse rights are unresolved and ADF&G distribution requires consent.

Public membership columns contain sorted distinct readable names. External audits retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
