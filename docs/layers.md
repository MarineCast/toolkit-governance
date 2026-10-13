# Layers, inputs, and outputs

Fifteen implemented collections have normalization, build, and inspection modules.
Acquisition is explicit; some families require provisioned bounded snapshots. The table below summarizes the configured inputs and primary
outputs; the sections that follow describe secondary products and coverage.

| Collection ID | Source inputs | Native geometry | Primary output |
| --- | --- | --- | --- |
| `marine_protected_areas` | NOAA 2023 MPA Inventory; DFO Oceans Act MPAs and Areas of Interest | Polygons and separate interest points | `marine_protected_areas.parquet` |
| `national_marine_sanctuaries` | Six pinned NOAA ONMS boundary archives | Polygons, retaining parts and overlaps | `national_marine_sanctuaries.parquet` |
| `international_boundaries` | IBC, NOAA, NRCan CGB, DFO bioregions, and supplied seascape water support | Reference lines and derived support polygons | `international_boundaries.parquet` |
| `federal_waters` | NOAA territorial-sea, contiguous-zone, and EEZ services; archived NRCan CGB | Source-native limit lines | `federal_maritime_limits.parquet` |
| `state_provincial_waters` | BOEM Submerged Lands Act boundary service | State seaward boundary lines | `state_seaward_boundaries.parquet` |
| `management_areas` | WDFW Recreational Marine Area Code service | Polygons | `management_areas.parquet` |
| `critical_habitat` | Provisioned NOAA NMFS polygon/line snapshots | Polygons and lines | `critical_habitat.parquet` |
| `wildlife_refuges` | Selected FWS and ECCC inventories | Polygons | `wildlife_refuges.parquet` |
| `conservation_designations` | Qualified ECCC marine CPCAD classifications | Polygons with separate reported roles | `conservation_designations.parquet` |
| `county_regional_boundaries` | Pinned Census TIGER/Line 2025 county archive | Polygons | `county_regional_boundaries.parquet` |
| `tribal_first_nations_areas` | BIA land-area and selected NRCan BC reserve inventories | Distinct provider reference polygons | `tribal_first_nations_areas.parquet` |
| `shipping_lanes` | Provisioned CHS and NOAA2026 routing references | Source-native role-specific geometry | `shipping_lanes.parquet` |
| `traffic_separation_schemes` | Provisioned CHS and NOAA2026 TSS references | Source-native role-specific geometry | `traffic_separation_schemes.parquet` |
| `ports` | Provisioned NGA World Port Index | Physical points | `ports.parquet` |
| `coast_guard_sectors` | Provisioned USCG sectors and CCG Western-region references | Distinct agency polygons | `coast_guard_sectors.parquet` |

**Paths below are workspace-relative defaults**, controlled by
`config/data/governance/governance.yaml`. Every collection directory also contains
`manifest.json`. Raw snapshots live under `data/raw/governance/`, except explicitly
configured local support paths. [Configuration](configuration.md) explains how to
select a workspace and change paths.

## Shared native product contract

One row represents a retained **geometry part** of a source-backed feature.
`GOVERNANCE_FEATURE_ID` links parts belonging to the same feature;
`GEOMETRY_PART_ID` is unique within an artifact. Count distinct features when you
need feature counts, and preserve parts when you need their exact geometry.

| Field group | Representative fields | Meaning |
| --- | --- | --- |
| Identity | `GOVERNANCE_FEATURE_ID`, `SOURCE_DATASET_ID`, `SOURCE_FEATURE_ID`, `GEOMETRY_PART_ID` | Source identity and retained part identity |
| Description | `FEATURE_NAME`, `FEATURE_TYPE`, `AUTHORITY`, `JURISDICTION` | Source-backed names and authority context |
| Legal context | `LEGAL_BINDING_STATUS`, `LEGAL_AUTHORITY`, `LEGAL_SOURCE_URL` | Source status and citations; no inferred rule applicability |
| Time | `EFFECTIVE_START`, `EFFECTIVE_END`, `SYSTEM_LEARNED_AT`, `SOURCE_VINTAGE` | Separate effective, learned, and source-vintage time |
| Qualification | `SOURCE_COVERAGE_STATUS`, `MEASUREMENT_STATUS`, `QC_STATUS`, `QC_REASON`, `MODEL_ELIGIBLE` | Coverage, measurement origin, QC, and default model ineligibility |
| Geometry support | `CLIPPED_TO_FULL_AREA`, source bounds, `RETAINED_GEOMETRY_TYPE`, `RETAINED_MEASURE_FRACTION`, `geometry` | Native EPSG:4326 geometry and clipping diagnostics |

Canonical products have **no H3 fields**. Manifests record sources and raw snapshot
checksums, retrieval information where supplied, configuration/extent identity,
clipping diagnostics, artifact SHA-256, columns, rows, geometry types, and known
limitations. Family publishers add authority policies and related-artifact checksums.
See [product contracts](CONTRACTS.md) for validation semantics.

## Marine protected areas

### Inputs and processing

- **NOAA MPA Inventory:** the pinned 2023 geodatabase archive supplies U.S.
  discovery geometry and reference classifications, management agencies, and
  source IDs. The detailed national archive is clipped locally.
- **DFO Oceans Act MPAs:** designated MPA/zone polygons supply Canadian reference
  geometry and regulation citations.
- **DFO Areas of Interest:** native points represent interest sites. They are
  retained separately; the toolkit does not invent proposed boundaries.

Normalization preserves designation identity, management authority, source-native
activity classifications, governing-rule gaps, and IUCN reporting values where
provided. It does not synthesize a protection score or infer legal activities.

### Outputs

Directory: `data/processed/domain/governance/protected_areas/marine_protected_areas/`

| File | Contents |
| --- | --- |
| `marine_protected_areas.parquet` | Combined canonical native geometry, including designated/reference polygons and interest points |
| `mpa_designation_polygons.parquet` | Polygon subset excluding Areas of Interest |
| `area_of_interest_geometry.parquet` | Separate non-designated interest geometry, retaining native points |
| `source_authority_evaluation.json` | U.S. management-authority coverage and missing site-specific governing-rule audit |
| `manifest.json` | Source checksums, designation/part counts, related files, and no-score policy |

### Coverage and interpretation

The inventory is complete for the acquired archive, not every current legal MPA.
DFO points are not designated areas. NOAA inventory values are reference metadata;
DFO regulation coordinates control over visual GIS geometry. This collection is
configured as `implemented_partial`.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/marine_protected_areas/DATA_SOURCES.md)

## NOAA national marine sanctuaries

### Inputs and processing

Six checksum-pinned ONMS shapefile archives supply the configured West Coast
roster: Channel Islands, Chumash Heritage, Cordell Bank, Greater Farallones,
Monterey Bay, and Olympic Coast. Their GIS vintages differ. The publisher checks
the exact roster and approximate-area QC policy, preserving polygon parts and
overlapping sanctuaries.

### Outputs

Directory: `data/processed/domain/governance/protected_areas/national_marine_sanctuaries/`

| File | Contents |
| --- | --- |
| `national_marine_sanctuaries.parquet` | Clipped canonical sanctuary polygons with designation, authority, and area-QC attributes |
| `sanctuary_authority_records.json` | One non-spatial designation/authority record per configured sanctuary |
| `manifest.json` | Roster completeness, source vintages, geometry-part counts, and authority-record checksum |

### Coverage and interpretation

The completeness label `complete_current_noaa_west_coast_sanctuary_roster` is the
publisher's configured roster policy. It is not a live check of current law or a
claim of complete authoritative coverage of arbitrary map cells. GIS membership
does not determine activity rules. Official boundary descriptions and coordinates
control; source vintages remain visible.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/national_marine_sanctuaries/DATA_SOURCES.md)

## International boundaries

### Inputs and processing

- Pinned **IBC digital boundary v1.3**, retaining section names and source scale.
- **NOAA U.S. Maritime Limits and Boundaries**, from configured local vector data
  or an acquired service snapshot.
- Pinned **NRCan GeoBase CGB Level 1**, retaining lines and country-area reference
  polygons with cartographic/legislative source status and accuracy where supplied.
- Provisioned **DFO Federal Marine Bioregions** and a **seascape territorial-water
  support GeoParquet**. These are spatial support, not legal boundary authority.

Reconciliation compares source lines independently in EPSG:3347. It samples
directional IBC-to-source distances and records source-scale precision proxies,
distance statistics, match fractions, and unresolved comparisons. It does not
snap or average source boundaries.

!!! note "Local support is required"
    `download international_boundaries` cannot provision the configured local-only
    DFO and seascape support inputs. Supply those paths explicitly, with shapefile
    sidecars and upstream provenance. `--allow-partial` does not bypass all
    reconciliation prerequisites. See [workflows](WORKFLOWS.md#external-local-inputs).

### Outputs

Directory: `data/processed/domain/governance/jurisdiction/international_boundaries/`

| File | Contents |
| --- | --- |
| `international_boundaries.parquet` | Canonical mixed reference lines and derived country-water support polygons with QC |
| `authoritative_boundary_segments.parquet` | Source-authority-published line segments; the filename describes provenance, not legal effect |
| `country_water_polygons.parquet` | Derived support polygons with country-allocation QC and explicit non-authority status |
| `boundary_reconciliation.parquet` | Per-section, per-comparison-source sampled distances and reconciliation status |
| `manifest.json` | Authority policy, source/related-file checksums, diagnostics, and unresolved sections |

### Coverage and interpretation

IBC digital geometry is a mapping reference. DFO bioregions and assembled
country-water support do not define legal waters. Missing support remains
unresolved and must be read from the rebuilt manifest; historical comparison
results do not establish a new regional acceptance result.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/international_boundaries/DATA_SOURCES.md)

## Federal waters and maritime-zone limits

### Inputs and processing

NOAA dynamic service layers supply separately identified U.S. territorial-sea,
contiguous-zone, and EEZ limit lines. Archived NRCan CGB supplies available
Canadian EEZ reference lines. The normalizer retains `ZONE_TYPE`,
`GEOMETRY_ROLE`, source agency, feature publication/update vintage, and legal status.

The producer keeps native lines. It does not buffer nominal distances into zone
polygons, dissolve nested zones, or generate `IS_FEDERAL_WATER`.

### Outputs

Directory: `data/processed/domain/governance/jurisdiction/federal_waters/`

| File | Contents |
| --- | --- |
| `federal_maritime_limits.parquet` | Combined canonical U.S./Canadian native limit lines |
| `us_maritime_zone_limits.parquet` | Separately identified U.S. zone-limit lines |
| `canadian_maritime_zone_limits.parquet` | Available archived Canadian EEZ reference lines |
| `zone_availability.json` | Country-by-zone availability and explicit source gaps |
| `manifest.json` | Source checksums/vintages, geometry policy, counts, and related-file checksums |

### Coverage and interpretation

Canadian internal-water, territorial-sea, and contiguous-zone geometry remains
unavailable in the configured source policy. NOAA's selected services do not
provide internal-water polygons. This collection is `implemented_partial`;
missing zones cannot be inferred from an EEZ line or shoreline.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/federal_waters/DATA_SOURCES.md)

## State and provincial waters

### Inputs and processing

The configured BOEM/BSEE Submerged Lands Act boundary service supplies U.S. state
seaward boundary lines. The producer normalizes and clips those native lines.

### Outputs

Directory: `data/processed/domain/governance/jurisdiction/state_provincial_waters/`

| File | Contents |
| --- | --- |
| `state_seaward_boundaries.parquet` | Canonical source-native state seaward boundary lines |
| `manifest.json` | Sources, checksums, clipping, coverage, and limitations |

### Coverage and interpretation

No state-water polygons are invented from the line. Provincial-water geometry
remains unavailable; British Columbia administrative applicability is not assumed
equivalent to U.S. state waters. This collection is `implemented_partial`.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/state_provincial_waters/DATA_SOURCES.md)

## Fisheries management areas

### Inputs and processing

WDFW Recreational Marine Area Code polygons provide one explicit Washington
management system. DFO Pacific Fishery Management Area references are recorded
as `reference_only`; no approved machine-readable source is pinned in the
configuration. Area systems are not merged into a universal zoning scheme.

### Outputs

Directory: `data/processed/domain/governance/fisheries_management/management_areas/`

| File | Contents |
| --- | --- |
| `management_areas.parquet` | Canonical WDFW recreational marine-area polygons |
| `manifest.json` | Source checksums, clipping, coverage, and limitations |

### Coverage and interpretation

California, Oregon, Alaska, federal/council, and Canadian support remain
unavailable in the configured Phase 1 coverage matrix. Polygon membership alone
does not establish current season, gear, harvest, or species rules.
This collection is `implemented_partial`.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/fisheries_management/management_areas/DATA_SOURCES.md)

## Critical-habitat reference inventory

### Inputs and processing

Provisioned NOAA NMFS polygon and line snapshots retain provider identity,
designation/proposal status, citations, and original attributes. Acquisition
requires an explicit bounded plan and complete query/ID/page receipts; the
download wrapper refuses an implicit national line-layer request.

### Outputs

Directory: `data/processed/domain/governance/protected_areas/critical_habitat/`

| File | Contents |
| --- | --- |
| `critical_habitat.parquet` | Canonical native habitat reference polygons and lines |
| `manifest.json` | Retained source bindings, clipping, coverage, and limitations |

### Coverage and interpretation

The implemented NOAA inventory is partial. It does not establish complete USFWS
or Canadian SARA coverage, ecological response, current legal designation, or
historical effective boundaries. Complete selected query IDs are different from
complete habitat geography.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/critical_habitat/DATA_SOURCES.md)

## Selected wildlife-refuge references

### Inputs and processing

Provisioned FWS National Realty Boundaries select `RSL_TYPE='NWR'`. ECCC CPCAD
selects National Wildlife Area, Marine National Wildlife Area, and Migratory Bird
Sanctuary records. The normalizer preserves original source attributes and filters
those types again rather than treating all conservation classifications as refuges.

### Outputs

Directory: `data/processed/domain/governance/protected_areas/wildlife_refuges/`

| File | Contents |
| --- | --- |
| `wildlife_refuges.parquet` | Selected canonical U.S./Canadian refuge reference polygons |
| `manifest.json` | Source selection, snapshots, clipping, qualification, and checksum |

### Coverage and interpretation

These selected source systems do not provide an exhaustive inventory of all
features called refuges. FWS mapping is resource-grade reference geometry; source
status and reporting years do not become legal effective dates. Provision bounded
snapshots with metadata and complete ID/page receipts before building.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/wildlife_refuges/DATA_SOURCES.md)

## Reported marine conservation classifications

### Inputs and processing

ECCC CPCAD records are restricted to `BIOME=M` and qualified provider
`PA_OECM_DF`/`STATUS` pairs. Four separate views retain reported designated PA,
designated OECM, interim PA, and designated provider Not applicable classes.
Original fields and parent/zone evidence keys remain available.

### Outputs

Directory: `data/processed/domain/governance/protected_areas/conservation_designations/`

| File | Contents |
| --- | --- |
| `conservation_designations.parquet` | Canonical provider-reported marine classification geometry |
| `manifest.json` | Source and qualification bindings, native geometry identity, and limitations |

### Coverage and interpretation

This is a classification view of retained evidence, not newly protected coverage.
It can overlap existing MPA/refuge evidence; do not add totals across those
families. Provider Not applicable is a classification label, separate from metric
missingness. Unknown class/status combinations are rejected rather than decoded
into invented legal categories.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/conservation_designations/DATA_SOURCES.md)

## County-equivalent references

### Inputs and processing

The pinned 2025 U.S. Census TIGER/Line county archive retains metadata, original
attributes, NAD83 source information, and leading-zero GEOIDs. Explicit archive
acquisition has a byte cap. The builder transforms to WGS84 and clips to the
native processing extent.

### Outputs

Directory: `data/processed/domain/governance/jurisdiction/county_regional_boundaries/`

| File | Contents |
| --- | --- |
| `county_regional_boundaries.parquet` | Canonical U.S. county-equivalent reference polygons |
| `manifest.json` | Pinned source identity, clipping, coverage, and checksum |

### Coverage and interpretation

These are Census statistical/cartographic representations, including Alaska
equivalents. Canadian regional districts remain unavailable. Neither a county
reference date nor polygon membership establishes current administrative power,
offshore jurisdiction, or legal effective dates.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/county_regional_boundaries/DATA_SOURCES.md)

## BIA and NRCan administrative references

### Inputs and processing

Bounded BIA AIAN National LAR snapshots retain provider `LARID`, original record
identity, and undecoded classification. NRCan CLSS snapshots select British
Columbia Indian Reserve records, retaining provider `adminAreaId`, original
OBJECTID, and all source fields. The two systems remain separate metric groups.

### Outputs

Directory: `data/processed/domain/governance/jurisdiction/tribal_first_nations_areas/`

| File | Contents |
| --- | --- |
| `tribal_first_nations_areas.parquet` | Canonical selected provider administrative reference polygons |
| `manifest.json` | Provider/source identity, retained qualification, clipping, and checksum |

### Coverage and interpretation

The collection ID is a catalog label. Its inputs do not establish traditional
territory, sovereign jurisdiction, all interested Tribes or Nations, land title,
or treaty fishing rights. NRCan source representation-purpose labels remain raw
attributes. BIA and NRCan groups must not be pooled as unique territory coverage.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/tribal_first_nations_areas/DATA_SOURCES.md)

## Shipping and traffic-separation references

### Inputs and processing

Two collections, `shipping_lanes` and `traffic_separation_schemes`, use explicitly
provisioned CHS routing layers and the pinned NOAA2026 routing archive/reference
frame. Original source geometry, object types, chart identifiers, and attributes
are retained. Fifteen source/component-role groups distinguish navigation lines,
tracks, route parts, fairways, lanes, and traffic-separation components.

### Outputs

| Directory under `data/processed/domain/governance/vessel_management/` | Files |
| --- | --- |
| `shipping_lanes/` | `shipping_lanes.parquet`, `manifest.json` |
| `traffic_separation_schemes/` | `traffic_separation_schemes.parquet`, `manifest.json` |

### Coverage and interpretation

The family name does not make every record a mandatory shipping lane. Provider
object identity and repeated chart records remain distinct from a unique physical
route or whole scheme. Role metrics union overlap within a source/role; they are
not pooled as unique route coverage across groups. Unknown object types fail
closed. Ferry routes are excluded. Dates/status strings do not establish current
legal rules, enforcement, or navigational suitability.

[Shipping source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/vessel_management/shipping_lanes/DATA_SOURCES.md)
and [TSS source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/vessel_management/traffic_separation_schemes/DATA_SOURCES.md)

## Port location references

### Inputs and processing

A provisioned NGA World Port Index input supplies physical port points. Original
port numbers, attributes, coordinate strings, and conversion metadata are
retained. The normalizer does not construct port jurisdiction polygons.

### Outputs

Directory: `data/processed/domain/governance/administrative_context/ports/`

| File | Contents |
| --- | --- |
| `ports.parquet` | Canonical source-backed physical port location points |
| `manifest.json` | Source/provenance binding, clipping, coverage, and checksum |

### Coverage and interpretation

Port locations are non-binding physical references. Point membership does not
establish port jurisdiction, legal authority, complete facility coverage, or
vessel activity.

[Normalizer and source fields](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/administrative_context/ports/normalize.py)

## Coast Guard administrative references

### Inputs and processing

Provisioned USCG sector and CCG Western-region snapshots retain agency-specific
record IDs and all original attributes. The builder preserves separate
`uscg_sector` and `ccg_administrative_region` roles and separate overlay groups.

### Outputs

Directory: `data/processed/domain/governance/administrative_context/coast_guard_sectors/`

| File | Contents |
| --- | --- |
| `coast_guard_sectors.parquet` | Canonical distinct U.S./Canadian administrative reference polygons |
| `manifest.json` | Source qualification, clipping, native part identity, and checksum |

### Coverage and interpretation

USCG sectors and CCG administrative regions are different organizational units.
Their union does not establish operational jurisdiction, sovereign waters, or
navigational safety. Selected snapshots remain partial reference support;
redistribution qualifications travel with source metadata and receipts.

[Source notes](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/administrative_context/coast_guard_sectors/DATA_SOURCES.md)


## Shared inspection and optional overlay outputs

| Output | Default location or selection | Purpose |
| --- | --- | --- |
| Source coverage matrix | `data/processed/domain/governance/source_coverage_matrix.json` | Configured regional coverage and runtime source availability; written during acquisition/build |
| Consolidated map | `outputs/domains/governance/governance_layers.html` | Simplified display geometry, selected date, available layers, and planned/unavailable status |
| Map manifest | `outputs/domains/governance/governance_layers_map_manifest.json` | Inspection configuration, layer status, and rendered-output identity |
| Optional H3 matrix | Explicit `export-h3-matrix --output` path | Separate context overlay on a supplied grid; all configured native collections and manifests are required |

Routing, Coast Guard, reported conservation classification, and BIA/NRCan
administrative families retain separate source/role metric groups. Group metrics
are not pooled collection totals.

The H3 overlay retains input cell identity and native attribute sets, with nulls
for unsupported empty intersections. It is model-ineligible and does not change
canonical native geometry. See the [full overlay contract](h3-matrix.md).

## Planned families

These nine catalog entries have no implemented collection pipeline. Their presence
supports planning and inspection status; it does not make them downloadable.

| Category | Planned collection IDs |
| --- | --- |
| Fisheries management | `seasonal_closures`, `gear_restrictions`, `harvest_regulations`, `salmon_management_zones` |
| Vessel management | `exclusion_zones`, `speed_restriction_zones`, `whale_approach_regulation_zones` |
| Administrative context | `management_regions`, `reporting_areas` |
