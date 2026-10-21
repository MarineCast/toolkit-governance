# Critical Habitat

Source-backed habitat reference features and their complete overlapping assignments. A feature count is neither a species count nor a count of legally equivalent habitat designations.

## Sources and processing

NOAA NMFS polygon/line inventory, DFO aquatic critical-habitat records and reviewed ECCC marine Marbled Murrelet reference polygons are normalized with provider attributes, species/population labels and statuses intact. Positive-dimensional intersections retain native parts; one distinct source-qualified feature counts once regardless of the number of parts.

Authoritative acquisition, rights and provider qualifications:

- [critical habitat source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/critical_habitat/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| Critical Habitat Count | `critical_habitat__recorded_feature_count` | int64 / count |
| Critical Habitat Assignment | `critical_habitat__feature_memberships_v1` | governance_memberships_v1 / recorded membership |

### Critical Habitat Count

Distinct source-backed feature IDs with positive-dimensional intersections

### Critical Habitat Assignment

One entry per distinct GOVERNANCE_FEATURE_ID with positive-dimensional cell intersection; paired source records retain labels and sorted intersecting native part IDs

## Identity and missingness

NOAA proposed/final meanings remain source-specific. DFO Final/Proposed stays unresolved. ECCC marine reference polygons identify habitat only where required biophysical attributes occur; they do not confirm habitat throughout the polygon. The posted Final recovery document does not establish blanket current legal protection. Terrestrial murrelet nesting components are excluded.

Memberships retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
