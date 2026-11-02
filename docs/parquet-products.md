# Public product contract

## Files and row identity

The delivery directory contains `catalog.json`, `governance-r<resolution>-static.parquet`, at most one `governance-r<resolution>-dynamic.parquet` per resolution and `OriginalData/<source-id>/geometry.parquet`. No release/generation directories, current pointers, manifest sidecars or duplicated native/study bundles are public outputs.

Static row identity is the unique string `h3_index` at the declared resolution. Dynamic identity adds a non-null Arrow date/timestamp `date` supported by source temporal evidence. Current reference inventories are static. Retrieval/build time, establishment year and unknown effective dates must never be converted into an artificial daily history. Supplied H3 membership and resolution are preserved.

`catalog.json` binds tables and originals by relative path, SHA-256 and row count, and records collection update information. Each table embeds JSON under Arrow metadata key `governance`; each source GeoParquet embeds `governance_original` and standard GeoParquet metadata. Embedded definitions bind fields, spatial/temporal support, methods, original source lineage and model eligibility. Version 5 binds in-file support through `embedded_support`; `catalog.support_data` repeats that binding. Legacy tables use `app_only_audit` and `catalog.audit_data`. `model_eligible` remains false.

## Application contract

The machine-readable feature contract is packaged in `governance/resources/app_contract.json` and embedded as catalog `application_contract`. It fixes supported resolutions (R6 and R8), feature identities/families, the twenty selected columns, scientific support and legacy reconstruction fields. The [physical-column reference](reference/columns.md) is the exact handoff schema. Full deliveries have exactly 21 physical columns: `h3_index` and those twenty selected features. Bounded subset builds retain only the selected features their sources support. Support statuses, unselected counts, original conservation components and saved compatibility fields are retained in metadata rather than physical columns.

`conservation_area_membership` is materialized from designated and status-qualified proposed/interim memberships as one of the twenty selected features. Designated conservation count and coverage retain their narrower meaning. Its support companions and county/management statuses are reconstructed for inspection rather than stored as public columns. The former shipping-lanes compatibility quartet remains in scientific support rather than physical columns. Internal normalization can retain additional scientific reconstruction fields without exporting them as public columns.

Catalog `sources` supplies a concise description, URL, qualification and separate `source_updated_at`, `observation_date`, `publication_date`, `retrieved_at_utc` and `source_vintage_note`. Unknown dates are null. ArcGIS `dataLastEditDate` is accepted only as explicit provider data-edit evidence from the retained receipt; general service/schema edits are not substituted. `built_at_utc` is product build time and `last_updated_utc` is its compatibility alias, never source update or legal effective time.

## Compact delivery and external audit

Contract v5 stores the same selected features and H3 identity, using concise lower_snake_case names. `application_contract.column_aliases` maps original native columns to these names. The final Parquet embeds a lossless scientific support partition under binary Arrow metadata key `governance_support`. It contains H3/date join keys, removed arrays, original schema/order and metadata under `governance_app_audit`. Counts, null masks, statuses, typed records and part lineage reconstruct exactly. Public membership name lists are checked against typed records, including designated and status-qualified proposed/interim conservation components. The public `fields` dictionary declares only physical columns; its support references resolve through the embedded scientific dictionary.

The support binding uses schema `governance.embedded_support.v1`, encoding `zlib_parquet_v1`, SHA-256 of the compressed bytes, row count and column names. Its payload is a zlib-compressed Parquet member; compression includes the complete scientific dictionary. It has no filesystem path. The final table checksum covers these bytes as well. New deliveries are portable as a complete Data/Governance directory; no workspace audit directory, coverage file, native matrix, manifest or intermediate evidence file is required afterward.

Successful ordinary builds validate final products/originals, then remove verified disposable workspace source caches and coverage files. Temporary native, overlay and publication staging are removed. No new external audit or compaction receipt is written. Explicit caller-owned inputs, configuration, unrecognized/shared files and required legacy audits are protected; failed builds preserve source caches. `--keep-workspace-data` is an explicit diagnostic opt-out for source-cache cleanup.

`governance --workspace WORKSPACE compact-data DIRECTORY` explicitly converts a selected validated legacy directory to v5 offline. It restores existing support, embeds it, verifies reconstruction/readback, preserves originals, `REVIEW_RESULTS.txt` and source/build dates, publishes catalog bindings last and rolls back handled failures. `compacted_at_utc` records conversion time. Repeating it on validated v5 products is a no-op. The retired `--audit-directory` argument is accepted for compatibility but creates no directory. Existing legacy audit inputs are preserved; conversion does not sweep historical evidence or other products.

Legacy v1 retains its original support columns; v2/v3 retain typed public memberships; v4 uses readable names and external support. These remain readable without rewriting their bytes. **Legacy v2–v4 still require their checksum-bound external audits at their recorded paths.** Cache cleanup protects any audits required by the retained product. The membership policy remains `unique_readable_membership_names_v1`. Validation reconstructs support and checks memberships, statuses, the materialized view and boolean consistency; it does not establish current law, completeness or model eligibility.

## Fields and units

The [family pages](layers.md) enumerate exact displayed columns. Acquisition collections, retained diagnostic support and display features are distinct. A count is an integer count of the documented source-qualified feature/site identity. A coverage fraction is dimensionless (0–1), not percent. The public routing flag and mapped administrative flags are nullable Arrow booleans.

Marine Conservation Area Coverage is the union of eligible recorded polygons within the **full H3 cell**, divided by full cell area in EPSG:6933. Overlap is not summed and no water-only denominator is substituted. Native line support uses length semantics rather than area. Boundary contact rules are family-specific: counties/districts and international lines include closed-cell edge/corner contact; ordinary polygon/line memberships require positive-dimensional intersection. The flat overlay is regional and rejects antimeridian grids; generic geometry utilities do not establish global product support.

## Audited paired membership identity

Public `_membership` columns are nullable Arrow lists of readable strings. Their complete original `feature_memberships_v1` support is preserved in embedded support (external audit for legacy v2–v4) as a nullable Arrow list of structs. Each item has non-null `feature_id` and `records`. Every record preserves non-null `source_dataset_id`, `source_feature_id`, and a sorted list `geometry_part_ids`, plus nullable `feature_name`, `feature_type`, `authority`, `jurisdiction`, `region`, `area_system_id`, `area_code`, `area_title`, `area_hierarchy_level` and `parent_area_code`.

Multiple records/parts can support one feature. Parts never inflate feature counts; labels stay paired with IDs and are not deduplicated by name. All overlaps survive; there is no dominant-area choice. Proposed/interim conservation assignments retain status-qualified public names and audited display identity while designated count/coverage exclude those references. Routing combines typed identities for display without asserting physical-route or legal equivalence.

## Missingness and coverage

Unknown, unavailable, partial, observed and not-applicable support are distinct. Preserve each field's declared support metadata and, where present, its status companion. Compact fields declaring `implicit_support: positive_partial_null_unknown_v1` encode nonempty membership/positive count as partial inventory support and null as unknown (or unavailable without original inputs); they do not support zero or an empty list.

For nullable booleans, true means documented reference evidence exists. False requires verified complete geographic support for every required component and observed empty memberships. Current partial source inventories do not establish false from no match. A null membership list is not an empty list. Query receipt completeness, geographic completeness and current legal applicability are different claims.

Validation rejects false/null presence flags with positive membership, true flags without positive membership, and false flags without observed empty memberships and the family's complete geographic qualification. International-boundary qualification additionally binds its source inventory and exact H3 grid. Ordinary line/polygon intersections retain the source geometry dimension when grid-envelope clipping collapses a line to a point or a polygon to an edge; such contact cannot create a point/line membership. Overlay method version `native-inventory-overlay-1.3.1` identifies this correction.

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
