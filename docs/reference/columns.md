# Final product columns and scientific support

Product contract v5 has exactly twenty selected features plus H3 identity at each full native R6/R8 delivery, matching the v4 physical columns. The packaged `app_contract.json` is the machine-readable handoff. Scientific support is embedded in final Parquet metadata. Names, units, source-qualified records, all overlaps and nulls retain the [product contract](../parquet-products.md).

| Physical column | Selected feature | Type / units |
| --- | --- | --- |
| `h3_index` | Native H3 row identity | string |
| `county_district_count` | County / District Count | count |
| `critical_habitat_count` | Critical Habitat Count | count |
| `exclusion_zone_count` | Exclusion Zone Count | count |
| `fisheries_management_area_count` | Management Area Count | count |
| `has_mapped_tribal_area` | Tribal / First Nations Area | boolean |
| `has_international_boundary` | International Boundary | boolean |
| `conservation_area_count` | Marine Conservation Area Count | count |
| `conservation_area_coverage_fraction` | Marine Conservation Area Coverage | fraction |
| `has_routing_reference` | Routing / regulation recorded | boolean |
| `county_district_membership` | County / District Assignment | list<string> readable names |
| `critical_habitat_membership` | Critical Habitat Assignment | list<string> readable names |
| `exclusion_zone_membership` | Exclusion Zone Assignment | list<string> readable names |
| `fisheries_management_area_membership` | Management Area | list<string> readable names |
| `speed_restriction_zone_membership` | Speed Restriction Zones | list<string> readable names |
| `mapped_tribal_area_membership` | Tribal / First Nations Assignment | list<string> readable names |
| `state_province_membership` | State / Province Assignment | list<string> readable names |
| `country_membership` | Country Assignment | list<string> readable names |
| `coast_guard_membership` | Coast Guard Assignment | list<string> readable names |
| `vessel_routing_membership` | Shipping Lanes & Traffic Separation Zones | list<string> readable names |
| `conservation_area_membership` | Marine Conservation Area Assignment | list<string> readable names |

Status arrays, unselected support counts and hidden shipping compatibility arrays live in metadata rather than physical columns. Booleans remain nullable Arrow booleans; null is not false. Counts remain nullable integers, fractions remain 0–1, and membership columns contain sorted distinct readable names. Complete paired IDs, labels, source records and native part lineage remain in the embedded support partition. Legacy v2–v4 retain their external audit requirements.

The combined conservation assignment includes status-qualified proposed/interim references; designated conservation count and coverage exclude them. The materialized assignment preserves the established feature ID. Embedded support retains original designated/reference components, removed arrays, the full scientific dictionary and the original schema for exact reconstruction. Reader-only status/support arrays remain available for inspection. See [support storage and migration](../parquet-products.md#compact-delivery-and-external-audit).

## Naming and compatibility

Counts use `_count`, readable assignment name lists use `_membership`, and nullable flags use `has_`. Conservation coverage retains `_fraction` to declare its 0–1 units. `country_membership` and `state_province_membership` describe geographic water assignments rather than legal jurisdiction.

Version 5 preserves the v4 native-to-public `column_aliases`, readable-name policy and physical types. The producer validator and independent Data Explorer reader verify aliases and reconstruct the original scientific schema. Feature IDs and inspection/source records remain stable. An explicit storage conversion preserves arrays, null masks, H3 grain, definitions and model eligibility; it does not rerun overlays. Existing v2–v4 external audits remain readable and unchanged. New v5 writers embed all original typed membership arrays in the final file.

## Readable membership values

All eleven `_membership` columns contain sorted distinct names, for example
`["Canada"]`, `["Canada", "United States"]` or `["British Columbia"]`. The table
remains one row per H3 cell; lists are never exploded into duplicate metric rows.
Country and province/state labels use explicit source codes/titles. Fisheries
prefer the source area title. Other labels use source feature names, then titles
or area codes when a name is unavailable. Unicode and source spelling are retained.
Conservation reference names carry `[Proposed]` / `[Interim]`; designated totals
still exclude those references. A null list means unresolved source support;
`[]` remains an observed empty membership. If a future recorded feature has no
usable label, a null item preserves that unnamed membership rather than inventing
an ID as its name. Source record identities are not deduplicated by name in audit.

Counts retain their original recorded-feature identity semantics. Several source
features may share one name, and one feature may supply multiple names, so counts
need not equal the public list length. This representation does not establish
unique sites, exhaustive geographic coverage, active restrictions or model eligibility.
