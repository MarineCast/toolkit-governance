# Fisheries management-area sources

Phase 1 acquires WDFW Recreational Marine Area Code polygons as one explicit
Washington management system.

- Service: <https://geodataservices.wdfw.wa.gov/arcgis/rest/services/ApplicationServices/Major_Fishing_Area/MapServer/6>
- Legal source: <https://app.leg.wa.gov/WAC/default.aspx?cite=220-56-185>

The polygons are not merged with Canadian or other U.S. area systems. DFO's
official Pacific Fishery Management Area maps and the 2007 regulations are
recorded as references, but an approved machine-readable geometry source has not
yet been pinned. California, Oregon, Alaska, U.S. federal/council, and Canadian
coverage remain explicitly unavailable in the Phase 1 matrix.

## Relational reference support

Native products preserve original OBJECTID and AreaName, all WDFW attributes and an
explicit recreational system/sector/hierarchy identity. Unknown parent, geometry version
and validity are null in the optional study H3 crosswalk. Each provider record has separate
positive-area cell relations; full-native and full-cell fractions are non-additive geometric
support, not catch/effort allocation weights. Native geometry-part IDs travel with each
relation. A shared provider code does not identify the same area across different systems.

Future quantity joins include recreational and commercial scope and the Oregon study
portion. No catch/effort quantities or allocation are acquired or computed in this release.
Agency administrative regions remain separate from fishing/reporting systems.

Official source candidates remain qualified separately:

- WDFW catch record card areas: <https://geodataservices.wdfw.wa.gov/arcgis/rest/services/FP_Projects/CatchRecordCardArea/MapServer/1>. Hydrological feed relations are not implicitly management parents.
- WDFW Salish commercial salmon reference: <https://geodataservices.wdfw.wa.gov/arcgis/rest/services/FP_Projects/WDFWFishProgramWACs/MapServer/8>. Provider notes describe approximations, missing markers and historical coordinate discrepancies; not controlling current legal geometry.
- WA Ecology commercial fish/shellfish reference: <https://gis.ecology.wa.gov/serverext/rest/services/GIS/CoastalAtlas/MapServer/1091>. The historical reference vintage is distinct from current instruments.
- DFO Pacific area/subarea maps: <https://www.pac.dfo-mpo.gc.ca/fm-gp/maps-cartes/areas-secteurs/index-eng.html>. Approved vector access/redistribution remains unresolved; regulations and geometry are separate evidence.
- ODFW nearshore commercial logbook grids: <https://www.dfw.state.or.us/fish/commercial/docs/marine_reserves/logbook_grid_charts.asp>. PDF/chart blocks require qualified source geometry and identifiers before a vector crosswalk; port sampling/landings do not establish catch coordinates.

These candidates are not completed native adapters or a complete source-system roster.
No common geometry/code equivalence, current law, quantities or redistribution clearance
is inferred from discovery.


## Bounded Alaska groundfish adapter (0.2)

The [ADF&G Groundfish layer 3](https://gis.adfg.alaska.gov/mapping/rest/services/CF_public/Groundfish/MapServer/3)
exposes queryable polygon geometry, original OBJECTID, six-digit STAT_AREA and geometry
start/end dates. The current `PVG_Statewide_2001_Present_GCS_WGS1984` service is a separate
commercial statistical/reporting system; geometry dates are not legal effective dates.
The getter reconciles a bounded bbox ID roster and preserves all source attributes.
Southeast, Gulf and Aleutian/dateline query completeness are qualified separately;
the declared layer extent ends about 68.5 N and establishes no Arctic completeness.
The layer's metadata forbids reproduction/distribution without ADF&G consent; retain
attribution and processing changes, and keep retrieved data local. A query receipt does
not establish all fisheries, shellfish applicability, current regulations or legal jurisdiction.
The legacy normalization-profile label is retained for CLI/config compatibility; dispatch
now explicitly distinguishes WDFW and ADF&G source IDs.


## DFO Pacific subarea adapter (0.2)

A fresh 2026-10-13 official Pacific service-directory check discovered
[DFO_BC_PFMA_SUBAREAS_50K_V3_1, layer 0](https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/Pacific/DFO_BC_PFMA_SUBAREAS_50K_V3_1/MapServer/0).
The earlier reference-only source entry now names this bounded ArcGIS adapter. There was no
existing checksum pin to replace. Original OBJECTID/GLOBALID and MGNT_AREA/SUBAREA_ hierarchy
are retained; codes stay in `dfo.pacific.pfma.subareas`, separate from WDFW/ADF&G.
The layer name supplies V3.1/50K reference identity, not an exact geometry vintage or legal
accuracy guarantee. Source licence/copyright metadata is blank: no automatic OGL claim or
redistribution clearance. Local research/inspection only; source-specific reuse confirmation
is required before sharing datasets. Subarea shapes do not manufacture whole-area polygons,
fishery/species/gear applicability, current law or historical rules.
