# Public product contract

## Files and row identity

The delivery directory contains `catalog.json`, `governance-r<resolution>-static.parquet`, at most one `governance-r<resolution>-dynamic.parquet` per resolution and `OriginalData/<source-id>/geometry.parquet`. No release/generation directories, current pointers, manifest sidecars or duplicated native/study bundles are public outputs.

Static row identity is the unique string `h3_index` at the declared resolution. Dynamic identity adds a non-null Arrow date/timestamp `date` supported by source temporal evidence. Current reference inventories are static. Retrieval/build time, establishment year and unknown effective dates must never be converted into an artificial daily history. Supplied H3 membership and resolution are preserved.

`catalog.json` binds tables and originals by relative path, SHA-256 and row count, and records collection update information. Each table embeds JSON under Arrow metadata key `governance`; each source GeoParquet embeds `governance_original` and standard GeoParquet metadata. Embedded definitions bind fields, spatial/temporal support, methods, original source lineage and model eligibility. `model_eligible` remains false.

## Application contract

The machine-readable application contract is packaged in `governance/resources/app_contract.json` and embedded as catalog `application_contract`. It fixes the supported application resolutions (R6 and R8), display feature identities/families, required physical columns, derived display/support columns and hidden compatibility fields. The [physical-column reference](reference/columns.md) is the exact handoff schema. Display feature count and physical column count are different: the latter includes identity, support statuses/counts and explicitly hidden compatibility fields.

`marine_conservation_assignment__feature_memberships_v1` is derived for display from designated and proposed/interim physical memberships. Its status/count companions and compact county/management statuses are also declared derived fields. The hidden shipping-lanes quartet remains for consumer compatibility; it is not a separate displayed measurement. Internal normalization can retain additional scientific reconstruction fields without exporting them as public columns.

Catalog `sources` supplies a concise description, URL, qualification and separate `source_updated_at`, `observation_date`, `publication_date`, `retrieved_at_utc` and `source_vintage_note`. Unknown dates are null. ArcGIS `dataLastEditDate` is accepted only as explicit provider data-edit evidence from the retained receipt; general service/schema edits are not substituted. `built_at_utc` is product build time and `last_updated_utc` is its compatibility alias, never source update or legal effective time.

## Fields and units

The [family pages](layers.md) enumerate exact displayed columns. Acquisition collections, retained diagnostic support and display features are distinct. A count is an integer count of the documented source-qualified feature/site identity. A coverage fraction is dimensionless (0–1), not percent. The public routing flag and mapped administrative flags are nullable Arrow booleans.

Marine Conservation Area Coverage is the union of eligible recorded polygons within the **full H3 cell**, divided by full cell area in EPSG:6933. Overlap is not summed and no water-only denominator is substituted. Native line support uses length semantics rather than area. Boundary contact rules are family-specific: counties/districts and international lines include closed-cell edge/corner contact; ordinary polygon/line memberships require positive-dimensional intersection. The flat overlay is regional and rejects antimeridian grids; generic geometry utilities do not establish global product support.

## Paired membership identity

`feature_memberships_v1` is a nullable Arrow list of structs. Each item has non-null `feature_id` and `records`. Every record preserves non-null `source_dataset_id`, `source_feature_id`, and a sorted list `geometry_part_ids`, plus nullable `feature_name`, `feature_type`, `authority`, `jurisdiction`, `region`, `area_system_id`, `area_code`, `area_title`, `area_hierarchy_level` and `parent_area_code`.

Multiple records/parts can support one feature. Parts never inflate feature counts; labels stay paired with IDs and are not deduplicated by name. All overlaps survive; there is no dominant-area choice. Proposed/interim conservation assignments retain status-qualified display identity while designated count/coverage exclude those references. Routing combines typed identities for display without asserting physical-route or legal equivalence.

## Missingness and coverage

Unknown, unavailable, partial, observed and not-applicable support are distinct. Preserve each field's declared support metadata and, where present, its status companion. Compact fields declaring `implicit_support: positive_partial_null_unknown_v1` encode nonempty membership/positive count as partial inventory support and null as unknown (or unavailable without original inputs); they do not support zero or an empty list.

For nullable booleans, true means documented reference evidence exists. False requires verified complete geographic support for every required component and observed empty memberships. Current partial source inventories do not establish false from no match. A null membership list is not an empty list. Query receipt completeness, geographic completeness and current legal applicability are different claims.

## OriginalData and time

OriginalData retains retrieved feature extents and attributes before toolkit clipping, original source identities, receipt scope and time evidence. A bounded selection is not a global inventory. Shared source data are stored once. Normalization/repair can create derived native parts while preserving original geometry and transformation evidence.

Source vintage, legal effective time, observation time, retrieval time and build time remain separate. Rebuilding from unchanged originals does not make a source newer. Source rights, attribution and redistribution restrictions travel with the original binding; the software license grants no source-data license.

## Validation and operational use

`governance validate-data DIRECTORY` / `validate_products(DIRECTORY)` verifies catalog/file consistency, checksums, original identities, row grain, declared fields, membership structure, nullable state/value rules and model-ineligible metadata. Unexpected/missing files fail validation. Validation establishes structural consistency, not current legal truth or completeness.

Build into a review destination and validate before replacing a delivery. Acquisition is explicit; `build_products` is offline. Native normalization and H3 matrices are temporary intermediates. See [quickstart](how-to-use.md), [coverage/refresh](coverage.md) and [source rights](reference/sources.md).

<!-- Stable targets for authoritative source-note links. -->
<span id="geographic-water-assignment-interfaces-2026-10-19"></span>
<span id="international-boundary-under-federal-waters-2026-10-19"></span>
<span id="management-areas-interface-2026-10-19"></span>
<span id="regional-boundaries-interface-2026-10-19"></span>
<span id="tribal-first-nations-interface"></span>
<span id="unified-marine-conservation-areas-2026-10-19"></span>
<span id="western-bc-water-assignment-2026-10-19"></span>
<span id="wildlife-refuges-scientific-interface-2026-10-18"></span>

### Bound replay of exclusion qualifications

The packaged `exclusion_replay_qualification_20261019.json` receipt preserves the
reviewed TC source-pin qualification and Lockheed datum/reporting-mask facts. Replay
requires the same source snapshot and exact original geometry WKB; the historical
mask distance additionally requires the reviewed native H3 key set and resolution.
The receipt records the checked mask hash, projected distance CRS and retained
evidence hashes. It does not fetch sources or imply a new mask measurement. Changed
source, geometry or grid support cannot inherit those numerical mask claims.
Without matching evidence, the producer uses a generic full-cell support warning.

Exclusion interpretation text is emitted from canonical qualifications rather than
reproducing duplicated historical append-only prose. Original source-record popup
qualifications and support limits remain preserved on matching evidence. Derived
water and boundary fields receive Administrative Boundaries presentation metadata
after their construction, with no changes to scientific definitions or values.
