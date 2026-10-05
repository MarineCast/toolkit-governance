# Governance production readiness

Fifteen native reference collection pipelines are implemented, with nine catalog families still
planned and unavailable. The latest bounded batch adds source-specific BIA land-area and NRCan Indian Reserve
administrative references. Every current collection is research-only.
No collection establishes legal applicability, current
regulatory compliance, historical effective dates or model eligibility. Retained acquisition dates
are not a freshness guarantee. The configured native extent is [-180, 32, -109, 72] EPSG:4326.

The existing application grid contains 1,263 R6 cells and 43,393 R8 cells across approximately
[-125.887, 46.793, -122.097, 50.056]. These are separate delivery variants, preserving supplied
membership; neither is an exhaustive grid over the native Northeast Pacific extent. The grid
falls within UTM zone 10N, so EPSG:32610 is retained for line lengths; EPSG:6933 measures areas.
Antimeridian H3 cells remain explicitly unsupported. Native companions preserve feature/part
relations and all source attributes. Static snapshots have no fabricated daily or effective date.

## Operational workflow

1. Initialize an isolated workspace and explicitly provision source snapshots and support inputs.
2. Run `governance --workspace WORKSPACE preflight`. It inventories all catalog entries and every
   configured source, including unused alternatives. Missing products are unavailable, not passed.
3. Build all configured collections into this isolated workspace with `--allow-partial`. Never rebuild
   into a published generation. Legacy per-family commands remain per-file atomic only.
4. Export the explicit H3 overlay; supply the grid and suitable metre-based length CRS.
5. Use `export-delivery --matrix MATRIX --output-directory NEW_DIR --release-id ID
   --software-revision FULL_SHA`. This writes a separate wide Parquet and companion manifest for
   each supplied resolution. All metric statuses have the observed/unknown/unavailable/
   not_applicable/partial semantics. Input receipt is a count fraction, not geographic coverage;
   exhaustive geographic denominators remain unknown. Missing geometry types remain null.
6. Assemble native products, all secondary artifacts, snapshots, effective configs, grid,
   metric dictionary, source rights/lineage and validation evidence in one prepared directory.
7. Run `publish-generation --source PREPARED --release-root LOCAL_ROOT --release-id ID
   --scientific-method-version native-inventory-overlay-1.3.0 --software-revision FULL_SHA`.
   It copies and hashes every member, checks exact membership, synchronizes writes and atomically
   switches `current.json` under an exclusive publisher lock. IDs cannot be overwritten. Readers
   call `resolve_current` once and retain that path for the operation; this prevents mixed reads.
8. `verify-generation PATH` rechecks every byte. `activate-generation --release-root LOCAL_ROOT
   --release-id EARLIER_ID` explicitly rolls back to a verified prior generation. It does not
   mutate data. Failed copying leaves the prior pointer intact; failure after directory rename
   can leave an unreferenced verified generation. A crash lock requires operator inspection;
   never delete an active lock automatically. OS/filesystem durability guarantees still apply.

The local generation envelope is distinct from the shared application manifest schema. Delivery
shape alone is not shared-schema conformance. Governance does not fit v0.1's quantity_kind enum;
any shared-profile adopter needs the reviewed reference-geometry extension and validation.

## Original planning inventory (historical; current status below)

Each row needs a pinned dataset/version, verified rights, native normalizer and fixtures,
coverage qualification, real overlay comparison and release acceptance before implementation is
complete. No paid or speculative bulk acquisition is justified by a catalog placeholder.

| Planned family | Candidate authoritative source / exact missing evidence | OSM suitability | Work estimate after source qualification |
|---|---|---|---|
| critical_habitat | NOAA/USFWS and Canadian SARA designated geometry; cross-jurisdiction roster and source pins absent | No legal designation substitute | 2–5 days |
| wildlife_refuges | USFWS boundaries and Canadian protected-area inventories; approved roster, pins and scopes absent | Physical labels only, not designation | 1–3 days |
| conservation_designations | Federal/state/provincial designation inventories; inclusion taxonomy and jurisdiction roster unspecified | No designation substitute | 3–7 days |
| county_regional_boundaries | Census TIGER/Statistics Canada administrative polygons; cross-border granularity and vintage unresolved | Reference cartography only with ODbL attribution | 1–3 days |
| tribal_first_nations_areas | Nation/Tribe and official agency sources; consent, sovereignty/territory versus reserve interpretation and rights unresolved | No territorial/sovereignty substitute | Cannot estimate until scope/rights resolved |
| seasonal_closures | DFO/state/NOAA closure notices and instruments; effective and knowledge-time machine-readable history absent | No | 3–10 days per jurisdiction |
| gear_restrictions | Agency rules and spatial instruments; gear taxonomy, activity applicability and temporal rules absent | No | 3–10 days per jurisdiction |
| harvest_regulations | Agency regulation feeds/legal instruments; species/gear/activity keys and time semantics undefined | No | 5–15 days per jurisdiction |
| salmon_management_zones | DFO/state management geography; approved zone taxonomy, pins and revisions absent | No management designation substitute | 2–5 days |
| shipping_lanes | NOAA/CHS navigation references; approved geographic roster and redistribution terms unresolved | Suitable labeled navigational reference only; never safe navigation/legal claim | 1–3 days |
| traffic_separation_schemes | IMO-adopted/NOAA/CHS schemes; authoritative versions, geometry rights and applicability unresolved | Reference geometry fallback only, not official scheme authority | 2–5 days |
| exclusion_zones | Agency notices/instruments; activity-specific authority and effective-time history absent | No | 3–10 days per jurisdiction |
| speed_restriction_zones | NOAA/Transport Canada instruments; season, vessel class and mandatory/advisory scope absent | No | 3–7 days per jurisdiction |
| whale_approach_regulation_zones | NOAA/DFO/state law; species/activity/distance and exceptions cannot be inferred from polygon intersection | No | 5–10 days plus interpretation review |
| ports | Official port authorities/transport inventories; physical port definition, footprint versus point and roster absent | Yes, clearly non-authoritative physical/reference features with ODbL attribution | 1–3 days |
| coast_guard_sectors | USCG/Canadian Coast Guard regions; compatible organizational geography and pins absent | Labels only, not responsibility/authority | 1–3 days |
| management_regions | Managing agencies; what management system is intended is unspecified | No authority substitute | Cannot estimate until system named |
| reporting_areas | Agency reporting systems; activity/system and grain undefined (WDFW marine reporting areas already represented in implemented management_areas) | No reporting assignment substitute | 1–3 days after system defined |

These are engineering estimates, not deadlines or approval of legal interpretation. Physical
reference alternatives do not complete regulatory families. New families require defined product
scope before bounded acquisition. Existing NOAA MPA inventory does not independently implement
all designation-specific planned products.

## Current source limitations

Canadian Pacific fishery-management areas are configured reference-only, with no pinned approved
machine-readable geometry or normalizer. An official DFO public ArcGIS open-data directory was
successfully inspected on 2026-10-04; it exposed Atlantic fisheries and NAFO areas but no matching
Pacific-area service under those names. The configured Pacific maps web host failed DNS during
this run. This is a bounded access/discovery limitation, not proof no source exists. Do not
substitute OSM or Atlantic geometry. Preserve this source as unavailable pending qualification.

NOAA/BOEM GIS references carry legal-use disclaimers. IBC's map line is not controlling boundary
evidence. Archived NRCan cartography and seascape-derived country-water support cannot establish
legal jurisdiction. DFO MPA areas of interest are points distinct from designated polygons.
The six named NOAA sanctuary roster's completeness does not establish exhaustive grid coverage.

## Configured source and rights inventory

Source terms below are retained configuration statements, not a new legal determination.
Only local data retention is in scope; no data publication is authorized.

| Source | Cache | Vintage | Rights / authority limitation |
|---|---|---|---|
| international_boundary_commission_v1_3 | available | 2018-04-19 | International Boundary Commission terms and source disclaimer apply; IBC states that the digital line is for mapping purposes only and must not be used to define the boundary; source section scale is retained and no segment is snapped. |
| noaa_us_maritime_limits | available | 2013-09-13 | U.S. Government work; source terms and NOAA disclaimers apply; Not for legal use; official depiction is on controlling NOAA charts and legal instruments. |
| noaa_us_territorial_sea_dynamic | available | dynamic_at_retrieval | U.S. Government work; source terms and NOAA disclaimers apply; NOAA publishes source-native limit lines, not legal zone polygons, and marks the GIS service as not for legal use; controlling charts and legal instruments prevail. |
| noaa_us_contiguous_zone_dynamic | available | dynamic_at_retrieval | U.S. Government work; source terms and NOAA disclaimers apply; NOAA publishes source-native limit lines, not legal zone polygons, and marks the GIS service as not for legal use; controlling charts and legal instruments prevail. |
| noaa_us_eez_dynamic | available | dynamic_at_retrieval | U.S. Government work; source terms and NOAA disclaimers apply; NOAA publishes source-native limit lines, not legal zone polygons, and marks the GIS service as not for legal use; controlling charts and legal instruments prevail. |
| nrcan_canadian_geopolitical_boundaries_lines | available | 2013-12-17 | Open Government Licence - Canada; archived GeoBase product terms apply; Archived cartographic product, not a controlling legal boundary; source positional accuracy and agency are retained and conflicts remain visible. |
| nrcan_canadian_geopolitical_country_area | available | 2013-12-17 | Open Government Licence - Canada; archived GeoBase product terms apply; Archived cartographic country area, not a controlling legal water-jurisdiction polygon; it is comparison support only. |
| dfo_federal_marine_bioregions_support | available | unknown | Open Government Licence - Canada; DFO describes marine bioregion boundaries as ecosystem-planning boundaries that may be fuzzy; use only for reconciliation context and support, never legal authority. |
| seascape_territorial_water_support | available | unknown | Derived artifact; upstream source licenses and attribution are recorded in the water-geometry manifest; Assembled territorial-water support is a modeling/spatial-support product; its exterior and country partition must not be interpreted as controlling legal boundaries. |
| noaa_mpa_inventory_states | unavailable | 2023 | U.S. Government public-domain data; not for navigation; NOAA describes the inventory as a dynamic reference compilation, not a legal document; site-specific governing rules are not supplied and require management-agency verification. |
| noaa_mpa_inventory_nerrs | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory polygon and classifications are reference metadata; the reserve designation and approved management plan control. |
| noaa_mpa_inventory_boem | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory geometry and classifications are reference metadata and do not substitute for a site-specific BOEM instrument. |
| noaa_mpa_inventory_marine_national_monuments | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory geometry and classification do not replace the monument proclamation, amendments, or regulations. |
| noaa_mpa_inventory_national_marine_sanctuaries | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory geometry and classification do not replace current ONMS boundary data or site regulations. |
| noaa_onms_channel_islands_boundary | available | 2008-06-18 | U.S. Government work; NOAA source terms and disclaimers apply; GIS boundary representation only; the current 15 CFR part 922 subpart G boundary description and coordinates control. |
| noaa_onms_chumash_heritage_boundary | available | 2024-12-02 | U.S. Government work; NOAA source terms and disclaimers apply; GIS boundary representation only; the current 15 CFR part 922 subpart V boundary description and coordinates control. |
| noaa_onms_cordell_bank_boundary | available | 2015-06-10 | U.S. Government work; NOAA source terms and disclaimers apply; GIS boundary representation only; the current 15 CFR part 922 subpart K boundary description and coordinates control. |
| noaa_onms_greater_farallones_boundary | available | 2015-06-10 | U.S. Government work; NOAA source terms and disclaimers apply; GIS boundary representation only; the current 15 CFR part 922 subpart H boundary description and coordinates control. |
| noaa_onms_monterey_bay_boundary | available | 2014-09-12 | U.S. Government work; NOAA source terms and disclaimers apply; GIS boundary representation only; the current 15 CFR part 922 subpart M boundary description and coordinates control. |
| noaa_onms_olympic_coast_boundary | available | 2004-12-01 | U.S. Government work; NOAA source terms and disclaimers apply; GIS boundary representation only; the current 15 CFR part 922 subpart O boundary description and coordinates control. |
| noaa_mpa_inventory_national_park_service | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory geometry and classification are reference metadata; NPS authoritative boundaries and site rules control. |
| noaa_mpa_inventory_national_wildlife_refuge_system | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory geometry and classification are reference metadata; FWS authoritative boundaries and refuge rules control. |
| noaa_mpa_inventory_national_forest_service | unavailable | 2023 | U.S. Government public-domain data; not for navigation; Inventory geometry and classification are reference metadata; Forest Service authoritative boundaries, orders, and plans control. |
| noaa_mpa_inventory_2023 | available | 2023 | U.S. Government public-domain data; not for navigation; NOAA describes the inventory as a dynamic reference compilation, not a legal document; site-specific governing rules are not supplied and require management-agency verification. The exact 2023 archive is pinned and clipped locally to full_area after raw preservation. |
| dfo_oceans_act_marine_protected_areas | available | dynamic_at_retrieval | Open Government Licence - Canada; DFO states that the GIS boundaries are visual reference only and not legally authoritative; official regulation coordinates control. |
| dfo_oceans_act_areas_of_interest | available | dynamic_at_retrieval | Open Government Licence - Canada; The source publishes point locations, not proposed legal boundaries; Areas of Interest remain separate from active designations. |
| boem_submerged_lands_boundary | available | unknown | U.S. Government work; BOEM source terms apply; GIS line is approximate and is not the controlling official boundary record. |
| wdfw_recreational_marine_areas | available | unknown | Washington State public data terms apply; One Washington recreational area system; not complete fisheries-management coverage. |
| dfo_pacific_fishery_management_areas | unavailable | unknown | Open Government Licence - Canada where applicable; Official maps and legal descriptions are known, but no approved machine-readable geometry snapshot is configured. |

## Explicit shared-schema mapping

Install `.[contract]` and use `export-shared-manifest --artifact TABLE --local-manifest COMPANION
--schema PINNED_SCHEMA --schema-reference IMMUTABLE_REFERENCE` for an approved schema that admits
`reference_geometry`. The adapter validates the entire manifest with JSON Schema and date-time
format checking, writes a separate `.shared-manifest.json`, and refuses v0.1. Native-local
companions remain required for metric coverage and transitive rights/authority lineage. Immediate
provenance sources are the rebuilt native artifacts read locally; read time is explicitly
not external provider retrieval. Unknown original acquisition dates remain unknown. The schema
reference/hash, native manifest hashes, scientific method and immutable release identity remain
recoverable in the shared manifest processing description. No model or legal qualification follows
from schema validity.

## Newly implemented static reference families

**Ports:** the official NGA public World Port Index JSON was acquired instead of the OSM fallback.
The original response contains 2,951 port records; 322 points fall in the native Northeast Pacific
extent. Numeric positions use literal DMS arithmetic. Provider strings with exactly 60 minutes
and zero seconds carry one degree; original coordinate strings remain in NGA-prefixed attributes.
This is a physical point inventory, not port polygons, jurisdiction, current navigation advice
or an exhaustive harbor roster. NGA original attributes are retained without interpreting
regulatory codes. Redistribution rights require separate review; this release remains local.
The source is https://msi.nga.mil/Publications/WPI and its public JSON endpoint.

**Critical habitat:** NOAA's published merged polygon/line service was discovered from its
[critical-habitat page](https://www.fisheries.noaa.gov/national/endangered-species-conservation/critical-habitat).
The 1,791 polygon-source features cover the configured Northeast Pacific query. A bounded full-AOI
line request hit its 150 MB combined-acquisition cap and did not publish a partial line snapshot.
A separately recorded application-footprint line request returned 9,679 features in approximately
16 MB. Thus line support is only [-125.89,46.79,-122.09,50.06]; it is not native-AOI-wide line
coverage. Source query metadata and original attributes preserve this distinction. The generic
`download critical_habitat` command refuses unbudgeted network acquisition; provision the
explicitly bounded ArcGIS snapshots documented in the release evidence.

NOAA describes the GIS as reference geometry; proposed/final rules and 50 CFR 226 control.
Proposed versus final status, listed entity, species, source publication/effective dates, units,
notes and links are retained individually. No source end dates are invented. Canadian and USFWS
critical habitat remain outside this source scope. Merged layer names/vintage are retained; this
is not a certification that every latest individual species layer has been merged.

The original 18-family planning table above is the assessment baseline; ports and critical_habitat
now have the bounded implementations described here. That first release left 16 pending; the next batch below implements two more as partial reference inventories. OSM port
requests returned HTTP 406 and 429; no OSM data was accepted. NGA eliminated the need for a port
fallback. OSM's [ODbL attribution terms](https://www.openstreetmap.org/copyright) would apply to
any later OSM-derived reference product, separately from authoritative sources.


## County and selected-refuge batch

The second batch raises the implemented count to ten, leaving fourteen planned families. All
remain model-ineligible reference inventories. It adds no legal applicability or effective-date
reconstruction. See the family [county source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/county_regional_boundaries/DATA_SOURCES.md)
and [refuge source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/wildlife_refuges/DATA_SOURCES.md).

The 2025 Census county archive is 83,989,800 bytes, pinned to SHA-256
`9c6e9d9076abce2670d1de255de3710c35ecca00a7005d88e012dec52d95f763`.
The source is nationwide U.S. data, transformed from NAD83 to WGS84 and clipped through the
existing antimeridian-safe native pipeline. It provides no Canadian regional districts. The
2025-01-01 reference date describes the Census vintage, not a legal effective date.

Filtered official refuge acquisition returned 132 FWS National Wildlife Refuge records and 68
ECCC National Wildlife Area / Marine National Wildlife Area / Migratory Bird Sanctuary records
returned by the server query for [-180,32,-109,72]. Exact native clipping retained 132 FWS
and 40 ECCC features; 28 ECCC query candidates were outside the precise AOI. Complete object-ID
rosters and every response page are archived;
IDs are snapshot-scoped, not assumed stable across future source updates. FWS source geometry
is resource-grade, dissolved and partly generalized (source documentation reports 1–30 m for
selected features). ECCC source status, establishment year, parent/zone IDs and management fields
are retained individually. Neither an establishment year nor an inventory receipt becomes an
exact legal effective date. Other protected-area categories are explicitly excluded.

The two refuge requests used 92,367,404 response bytes under a 120 MB cap. Including Census and
the preceding approximately 175 MB acquisition, the running estimate remains below the approved
400 MB public-source budget. Staging is capped at 2 GB. No paid services, source-data commits or
external data publication are involved. Every subsequent release uses a new immutable identity;
previous releases and caches remain intact.


The native outputs contain 372 county geometry parts (325 county-equivalent features) and
29,193 refuge parts (172 source features). All output geometries validate. The shared native
pipeline repaired 64 invalid FWS source geometries using its existing documented `make_valid`
method; source snapshots remain unchanged. Clipping diagnostics retain repaired/excluded counts.


## Typed routing-reference batch

The third batch implements `shipping_lanes` and `traffic_separation_schemes` as explicit component
inventories, bringing the catalog to twelve implemented reference collections and twelve planned.
The method is `native-inventory-overlay-1.1.0`; delivery semantic version is 1.1.0. Existing ten
family calculations are unchanged. Routing has fifteen separately declared source/role groups,
with no pooled routing count, area or line total. Polygon roles expose component-object count and
unioned area fraction; line roles expose component-object count and unioned length. An absent
source is unavailable; empty roles/intersections under incomplete regional coverage remain null.

CHS AOI queries for layers 2–5 returned 26/14/55/234 candidates. Ferry layer 1 is excluded. Every
source field, chart identifier and object LNAM is retained. Where LNAM is present, logical object
counts deduplicate that identifier within its source object type; native source-record/part IDs
remain unique. Geometry union prevents additive overlap inside each source/role. Overlap with
other roles or NOAA is not summed or interpreted as a unique route or whole scheme. Conflicting
chart geometries are retained and unioned, not silently resolved to a preferred chart scale.

The NOAA March 16, 2026 archive is distinct from its older live EPSG:3857 service and contains
327 NAD83 source records. Original GPKG FID is preserved in the provisioned GeoParquet and the ZIP
is retained unchanged, SHA-256 `9dff1d661030e6e306b5c49cf84e07e5f566a3b027da282c3d713e74314eff37`.
Traffic Lane/Separation Zone roles belong to TSS; Fairway/Two-Way Route/Recommended Route roles
belong to shipping references. Area To Be Avoided, Precautionary Area and Particularly Sensitive
Sea Area are excluded from these families, not repurposed into unqualified regulatory products.

The official Marine Cadastre disclaimer was retrieved through its linked page. It permits use
of government-hosted public-domain information unless specifically annotated otherwise, with
attribution/no-false-ownership, no-endorsement and no-presentation-of-modified-content-as-official
constraints. Dataset metadata limits use to coastal/ocean planning, not navigation, reports no
maintenance planned and untested completeness. CHS uses OGL-Canada v2 with attribution/license
link and no endorsement. Dates/status codes remain original attributes; publication, catalog
modification, retrieval and legal applicability are distinct.

Acquisition used 27,936,991 response bytes (40 MB cap), including a size-preflighted 27,668,464-byte
NOAA ZIP. The cumulative estimate is 379,294,195 bytes under the existing 400 MB acquisition
budget. No paid access or external source-data publication. Exact source metadata, dictionary,
rights, request rosters, pages, checksums and receipts accompany the immutable local release.


The bounded real native build produced 256 shipping-reference parts/source records representing
199 logical object IDs after CHS LNAM deduplication, and 195 TSS parts representing 187 source
object IDs. All new output geometries validate without repair. Four declared roles have no
source geometry in the native AOI and remain null in delivery, not observed absence. The archive
and raw chart responses retain source records outside the native AOI and excluded object types.

## Coast Guard and ECCC classification batch

The fourth batch implements two narrow families, bringing the current count to 14 research-only
collections and 10 planned/unavailable families. Method `native-inventory-overlay-1.2.0` adds six
source/role groups; existing metric definitions and values remain unchanged. The R6/R8 grids,
area/length projections, native extent and schema 0.2 mapping remain the established configuration.

- Coast Guard: two USCG sectors (Columbia River and Puget Sound) selected by the exact application
  grid, plus the CCG Western administrative region. These are distinct organizational units,
  never pooled as unique jurisdiction or equivalent sectors. CCG is a 2021 cartographic snapshot
  intended for 1:250000 or smaller scales; operating areas may extend beyond mapped boundaries.
- ECCC: 72 CPCAD December 2025 marine source records, retaining 70 parent and 72 zone IDs:
  51 reported PA/designated, 17 OECM/designated, one interim PA/interim and three provider
  Not applicable/designated. These are provider-qualified classification views, not a new
  cross-country designation taxonomy or incremental protected coverage. Not applicable here
  is a provider label, distinct from a metric missingness state. All classes remain partial.
  Original codes, dates, mechanism strings and IPCA fields remain source attributes without
  legal-current, effective-date or Indigenous territorial inference.
- Four CPCAD records reuse exact cached refuge source evidence with their original per-page
  retrieval receipts. Parent/zone evidence keys and a release crosswalk disclose this overlap.
  No aggregate conservation metric is produced; do not sum MPA, refuge and classification metrics.
- PAD-US contributes only an evidence crosswalk: all 60 grid-selected Marine/MPA Source_PAID
  values match the existing NOAA inventory identifiers. Its NOAA 2021 source vintage is retained
  separately from NOAA 2023; no new geometry, coverage or replacement inventory is inferred.

New source geometry acquisition used 4,587,359 bytes (CCG 1,486,345; CPCAD 3,101,014), below the
8 MB per-source caps. Total authorized public acquisition consumed 387,275,523 of 400,000,000
bytes including earlier attempts/preflight. Estimated final release is 0.80–0.82 GB and transient
staging/assembly/publication requires approximately 2.6 GB. No paid API or cloud resource is used.

USCG original metadata is retained unchanged, including its malformed redistribution clause.
The derivative has a distinct title and accompanying FGDC-format processing/lineage/citation
metadata. Schema conformance and redistribution clearance are not asserted; the release remains
local-only pending rights review. CCG and CPCAD retain Open Government Licence - Canada
attribution, links and modified-data labels. Other inherited source rights restrictions persist.

The remaining 10 planned families are tribal_first_nations_areas, seasonal_closures,
gear_restrictions, harvest_regulations, salmon_management_zones, exclusion_zones,
speed_restriction_zones, whale_approach_regulation_zones, management_regions and reporting_areas.
Tribal administrative/reserve versus traditional-territory scope and management/reporting systems
require explicit selection. Dynamic legal products require authoritative activity/gear/species
keys, instruments and effective/knowledge-time history; static inventory geometry cannot fill
those gaps. The estimates in the original table apply only after those decisions and source
qualification. OSM cannot resolve these legal or territorial gaps.

## BIA and NRCan administrative-reference batch

The fifth batch raises the implemented count to 15 research-only collections and leaves nine
planned families. The `tribal_first_nations_areas` catalog family implements only the approved
administrative/reserve reference scope. It contains no traditional territories, treaty fishing
areas, sovereign-jurisdiction inference or legal-title determination. Its two source/role groups
remain separate in H3 metrics and map inspection. Provider area identifiers count source units,
not Tribes, Nations, people or rights holders. Separate source records and geometry parts remain
recoverable; geometry overlaps are unioned within a source group rather than summed.

Direct BIA AIAN National LAR acquisition returned 14 full source polygons selected by the existing
exact application-grid mask. All observed CLASSIFICATION codes are `1`; the service supplied no
code domain, so no decoded land-type claim is introduced. BIA explicitly limits the geometry to
illustrative/reference/statistical use, disclaims legal/jurisdiction/ownership inference, and
warns that all co-interested tribes may not be represented. Its current service describes ongoing
improvements; an older BIA consultation described 2019 LAR spatial definitions. Neither statement
is silently converted to this snapshot's geometry vintage or legal effective date.

Direct NRCan CLSS acquisition returned 111 source records selected by the same mask and explicitly
filtered to provider `Indian Reserve` records in British Columbia. Provider administrative IDs,
original distribution/jurisdiction/representation-purpose fields and every received attribute are
retained. A provider purpose value of `Legal` is not promoted to canonical legal authority.
Sechelt Land and other administrative classes remain outside this first qualified subset.
Open Government Licence - Canada terms, attribution and modification labels remain attached.

This is partial application-grid-selected WA/BC reference coverage, not a full provincial/state,
Northeast Pacific or Indigenous-interest inventory. The original native AOI and supplied R6/R8
memberships remain unchanged; selected whole source features are clipped only by the established
native pipeline. Empty intersections stay null under partial support, and all fields remain
model-ineligible. Original source OBJECTIDs and stable provider area IDs serve different roles.
No source establishment or effective date is inferred from retrieval, edit or catalog dates.

Acquisition used 2,682,213 additional response bytes: BIA geometry 461,775 bytes, NRCan geometry
2,194,612 bytes, and 25,826 bytes of fresh metadata/ID rosters. Including the earlier 410,508-byte
scope preflight, this is 3,092,721 bytes against the approved 11 MB additional batch cap.
Cumulative counted public acquisition is 390,368,244 / 400,000,000 bytes. Peak task-owned staging,
assembly and local publication remains estimated at 2.7 GB, with 29 GiB free before work began.
The additive scientific method/product version is `native-inventory-overlay-1.3.0`; existing
metric meanings and values are unchanged. Native and shared schema 0.2 companions remain required.

The remaining nine families are seasonal_closures, gear_restrictions, harvest_regulations,
salmon_management_zones, exclusion_zones, speed_restriction_zones,
whale_approach_regulation_zones, management_regions and reporting_areas. WA/BC WDFW/DFO systems
and dated whale/fisheries snapshot scopes are approved; source qualification remains necessary.
DataBC PFMA metadata says Access Only while a third-party copy claims OGL-BC, and a discovered
Washington commercial salmon reporting layer explicitly says non-authoritative. Neither was
accepted as authoritative geometry. DFO's legacy geoportal endpoint returned 404. Existing WDFW
recreational geometry is reusable evidence, not automatically a new commercial reporting system.

Primary WA/BC regulatory texts must retain jurisdiction, issuer/system, species, vessel/activity/
gear and rights-holder applicability, exceptions, and independent effective/expiry, publication,
knowledge and receipt times. Moving-whale approach rules do not yield fixed exclusion polygons.
Coastline/border-defined segments require qualified geometry support. Contradictory dates in a
Tribe-issued fishery instrument require human review, not silent correction. No regulatory
snapshot, UTC time expansion or legal-history product is added in this batch.
