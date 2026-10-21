# Administrative Boundaries

Recorded county/district, reserve/land-area and geographic water assignments. The international-boundary flag describes a line touching a cell. These references answer different questions and must remain separate.

## Sources and processing

Census TIGER/Line counties, BC ABMS regional districts, BIA AIAN land-area records, qualified NRCan BC Indian Reserve records, retained model-water polygons and international boundary lines supply distinct support. County/district processing uses full original polygons and includes edge/corner contact. Tribal/reserve and water assignments require positive area. WA/OR assignments intersect administrative polygons with U.S. model water; BC uses explicit British Columbia model water. No nearest-land assignment, offshore extension or high-seas complement is constructed.

Authoritative acquisition, rights and provider qualifications:

- [county regional boundaries source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/county_regional_boundaries/DATA_SOURCES.md)
- [tribal first nations areas source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/tribal_first_nations_areas/DATA_SOURCES.md)
- [state provincial waters source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/state_provincial_waters/DATA_SOURCES.md)
- [federal waters source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/federal_waters/DATA_SOURCES.md)
- [international boundaries source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/international_boundaries/DATA_SOURCES.md)

## Public columns

These are the display features at each supplied resolution. Additional embedded support is described in the [product contract](../parquet-products.md); a support field is not another displayed measurement.

| Display name | Exact column | Type / unit |
| --- | --- | --- |
| County / District Count | `county_regional_boundaries__recorded_feature_count` | int64 / count |
| Tribal / First Nations Area | `tribal_first_nations_areas__mapped_area` | bool / boolean |
| International Boundary | `federal_waters__international_boundary` | bool / boolean |
| County / District Assignment | `county_regional_boundaries__feature_memberships_v1` | governance_memberships_v1 / recorded membership |
| Tribal / First Nations Assignment | `tribal_first_nations_areas__feature_memberships_v1` | governance_memberships_v1 / recorded membership |
| State / Province Assignment | `state_provincial_waters__assignment__feature_memberships_v1` | governance_memberships_v1 / recorded membership |
| Country Assignment | `federal_waters__assignment__feature_memberships_v1` | governance_memberships_v1 / recorded membership |

### County / District Count

Count of distinct source-qualified counties / BC regional districts touched by the full closed native H3 cell. All matches count once, including edge/corner contacts.

### Tribal / First Nations Area

Positive-area intersection with a received BIA land-area reference or qualified BC NRCan Indian Reserve. True requires at least one qualifying overlap. False requires verified complete mapped-inventory coverage of every supplied full cell for both component sources and observed empty memberships; otherwise no-hit support is null (unknown/unavailable). All overlapping names and source-qualified area/record IDs are retained; no dominant area is chosen. These are different provider administrative/reserve categories, not Tribes or Nations as entities, sovereign/traditional territories, ownership, treaty rights or broader legal jurisdiction. Query receipts and national extents do not establish completeness.

### International Boundary

True means the full cell intersects a retained mapped international border line, including edge or corner contact. False requires verified complete geographic line support. Current sources are partial: no-hit cells remain unknown. This is boundary presence, separate from the International water-assignment category; mapping reference only, not legal authority. All independently published matching line records remain paired, without averaging or selecting a dominant source.

### County / District Assignment

All county / BC regional district names and paired source IDs touched by the full closed native H3 cell, including edge/corner contacts.

### Tribal / First Nations Assignment

Positive-area intersection with a received BIA land-area reference or qualified BC NRCan Indian Reserve. True requires at least one qualifying overlap. False requires verified complete mapped-inventory coverage of every supplied full cell for both component sources and observed empty memberships; otherwise no-hit support is null (unknown/unavailable). All overlapping names and source-qualified area/record IDs are retained; no dominant area is chosen. These are different provider administrative/reserve categories, not Tribes or Nations as entities, sovereign/traditional territories, ownership, treaty rights or broader legal jurisdiction. Query receipts and national extents do not establish completeness.

### State / Province Assignment

Geographic model-water assignment: WA/OR administrative polygons clipped to U.S. water support; BC from the explicit British Columbia water region. Not legal marine ownership. Unmatched support remains unknown; no offshore extension. Membership means any positive-area overlap of the full native H3 cell with supported water geometry. All geographic assignments and paired source IDs/names/parts are retained; no dominant assignment, nearest-land classification or high-seas complement. Unknown and verified no-assignment are distinct; this partial source inventory does not certify absence.

### Country Assignment

Geographic country assignment from retained model-water polygons; not federal administrative waters, EEZ or legal jurisdiction. International is not established by these sources; unmatched support remains unknown. Membership means any positive-area overlap of the full native H3 cell with supported water geometry. All geographic assignments and paired source IDs/names/parts are retained; no dominant assignment, nearest-land classification or high-seas complement. Unknown and verified no-assignment are distinct; this partial source inventory does not certify absence.

## Identity and missingness

County GEOIDs and BC LGL_ADMIN_AREA_ID stay source-qualified. BIA LARID differs from its source OBJECTID; NRCan adminAreaId differs from its source record ID. Names never substitute for these identities. Stikine is retained as original evidence but excluded from regional-district membership. Northern Rockies is not substituted from another layer.

Memberships retain all source-qualified IDs, paired labels and sorted geometry-part lineage; no dominant match is selected. A null value means unknown/unavailable support, not zero or absence. Current partial inventories do not justify empty lists, false flags or zero counts in unmatched cells. Numeric fractions are dimensionless (0–1), not percentages; counts count the documented identity, not native parts.

## Update and use

Rebuild offline from the retained, validated OriginalData using [the refresh workflow](../coverage.md). A rebuild changes processing time, not source vintage, legal effective time or geographic completeness. Acquire newer source evidence only through an explicit bounded provider workflow and recheck the linked source qualifications before replacing originals.

Use these features for qualified reference inspection and research. They remain model-ineligible and do not establish current law, navigational safety, regulatory compliance or exhaustive jurisdiction. Preserve the source-specific qualifications when exporting a view or interpreting a cell.
