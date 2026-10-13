# Governance 0.2 hardening handoff

Implemented on `codex/governance-hardening`, starting from fetched default branch
`074e3ea` and comparing the review baseline `17f4b3b5f91f1126686fbb6fa301137627529ddd`.
The default-branch delta was documentation-only. The first focused commit,
`6168e14`, contains correctness/API changes; the following commit adds qualified
providers, final regression refinements, coverage/resources and this handoff.
No merge, push, deployment, production overwrite, release activation or public source-data
redistribution was performed. Only toolkit-governance is changed.

## Finding dispositions

| Task finding | Implemented behavior / evidence |
| --- | --- |
| ArcGIS short/empty-page truncation | Capability-aware stable ID roster, recursive bounded batches, before/after reconciliation; fallback requires ordered pagination/count receipts and advances service record windows. Duplicate/missing/repeated/unstable IDs and budgets fail before cache replacement. |
| Cache scope and pins | Layer/provider/version/selector/mask/support/completeness validation; request keys and compatible supersets. Pins enforced again on ordinary builds, cache reads and overrides. Derived/local vectors require declared scope receipts. Shapefile sidecars participate in dataset hashes; receipts do not circularly hash themselves. |
| Valid zero-match results | Schema-preserving native empties and explicit empty/unavailable/not-applicable coverage; builders and MPA secondary publishers accept legitimate empties. Single-country/cross-border regressions do not require matches in both countries. |
| Dates and provenance | Shared declared-epoch-ms/ISO parser, malformed/schema-drift failures; 1590969600000 is 2020-06-01. Establishment year/precision separated from exact effective dates; cached source receipt times survive rebuild. Semantic hash excludes build metadata. Historical getter as_of is rejected. |
| Spatial retained measures | Unwrapped equal-area polygon square metres, WGS84 geodesic line metres, point-count fractions; dateline half-line and one-of-two-point fractions pass. Holes/multipart/repair/touch/empty cases are tested. Repair status, lower-dimension remnants and dimension-specific diagnostic measure deltas are reported. |
| MPA area/designation meaning | Marine zero remains zero; total-site area is separate. Proposals excluded by default and separately grouped when requested. Feature, designation, source-record, zone and part counts/relations retain their distinct grains. Inventory status is not legal-currentness. |
| Semantic/config validation | Required non-null IDs, CRS/families/types, finite measurements, fraction bounds, date/interval precision, status/role consistency, provider fields/types, strict booleans/resolution/bounds/selectors, unknown-key rejection and reference-cycle detection. |
| Publication failures | Native artifact/manifest pairs stage and roll back handled failures under a product lock; direct cache pairs roll back handled failures. Readers reject hash disagreement. Two renames remain a crash boundary, not workspace transactionality. Existing immutable-release workflows remain intact. |
| Simple API/CLI | Typed GovernanceResult; thin named getters, explicit config/workspace objects, bounded cache-first/refresh/offline acquisition, source/system selection; get CLI and read-only availability command. Unqualified planned layers raise a specific exception. |
| Optional H3 | Native-only import/use with H3 physically absent; overlap candidates/exact intersections, bounded cells/memberships, one resolution, full-cell support, per-provider groups, union coverage, declared units, relational memberships and dateline cells. Legacy study metrics keep their original definitions. |
| Regional expansion | ODFW 2016 published reference, DFO Pacific V3.1 subareas, ADF&G groundfish reporting, TC 2026 closed vessel/speed rings. Eight regional fixture scopes and 408 matrix rows separate implementation, receipt completeness, geography and legal currentness. |
| Cleanup/performance | Consolidated date/grid helpers and collection registry; removed duplicate receipt helper and proven unused touched imports/locals. Reused transforms/spatial indexes, single-collection dispatch, spooled/capped acquisition and bounded overlays. Measured stages below. |

The [query API](query-api.md), [coverage notes](coverage.md) and source-specific
DATA_SOURCES.md files carry contracts, source/rights limitations and migration details.
Version 0.2 / native-reference-2.0 records changed scientific calculations explicitly;
old native products and historical releases are not relabeled or rebuilt.

## Source evidence and decisions

- ODFW's official download was 20,803 bytes, with 14 placemarks and preserved multipart
  boundaries/holes. A new independent 2016 archive pin is recorded; current OARs remain separate.
- The official DFO Pacific directory exposed `DFO_BC_PFMA_SUBAREAS_50K_V3_1/MapServer/0`.
  The prior reference-only entry now has a bounded adapter, original OBJECTID/GLOBALID and
  MGNT_AREA/SUBAREA_ hierarchy. No previous checksum pin existed. Layer licence/copyright fields
  are blank; local reference inspection is qualified, dataset redistribution is not.
- ADF&G's official layer declares original six-digit reporting codes, polygon/query capability,
  geometry validity dates and a dateline-spanning extent ending about 68.5 N. Its reproduction/
  distribution restriction is retained; geometry dates are not legal effective dates.
- TC's pinned 2026-05-22 instrument yields two vessel rings and one Swiftsure speed ring.
  Original quantity/unit, applicability/exception references, authority, clauses and inclusive
  day-precision interval travel with records. Nitinat's coastline segment is excluded.
- Existing expected SHA-256 pins were compared against the fetched starting branch and are
  unchanged. NRCan/ECCC selectors are now explicit and must match their qualified source scope.
  All editable/packaged configuration resources were checked byte-identical.
- Full native boundaries are selected by intersection. H3 expands acquisition to full cell
  support; no bounding-box-truncated geometry is presented as complete full-cell coverage.
  Library calls use explicit workspace objects; legacy CLI environment precedence remains.

No raw provider archive, source dataset or generated regional product is committed.

## Cleanup evidence

`rg` across source/tests/docs, configured collection dispatch, console entry points, catalog
registry and installed-wheel imports showed that family modules remain dynamically used.
No family module or supported dependency was deleted. Two magnitude-guessing `_source_date`
helpers were replaced by the common declared-schema parser. Sanctuary's private
`_system_learned_at` and its sole JSON import were removed after build/query receipt handling
was centralized; direct normalizers use explicitly supplied receipt evidence. Unused touched
pipeline imports and loop indices were removed. Study/fishing-crosswalk consumers now import
`shared.grid.read_grid`; the old private `_grid` alias remains for compatibility.
Pydantic remains because ConfigDocument.validate_as is a supported extension point, now covered
by a strict-model regression. No mass formatting or Graphify refresh/publication was performed.

## Validation

- Original baseline suite: 65 passed before edits. Final offline suite: **105 passed,
  2 skipped**; skips are the deliberately opt-in network tests.
- Both live smoke tests passed with positive records: a small Gulf of Alaska groundfish query
  and a small DFO Pacific subarea query. Each enforced 2 MB / 20 features / 20 requests.
  Oregon/TC official bounded files were separately parsed; raw source files stay temporary/local.
- Clean wheel environments outside the checkout: native getter/CLI/resource/family imports
  with H3 physically absent; H3 getter with positive exact memberships at resolution 7;
  OrcaCast/application imports blocked. Both pip check runs passed.
- The full suite also passed against the clean installed wheel/current dependency stack.
  Python 3.14.6 on macOS arm64; newer stack includes GeoPandas 1.2.0, pandas 3.0.6,
  Shapely 2.2.0 and H3 4.5.0. Legacy transform deprecations and upstream CartoDB tile-key
  warnings are non-failing; the new shared area transform uses the supported array API.
- Wheel build, strict MkDocs build, config/resource parity, catalog generation, installed
  catalog/preflight/availability and git diff --check passed.

Python 3.11/other operating systems were not locally run. Real full-region rebuilds, frozen
historical study recertification, independent regional overlay acceptance, legal-currentness
review and browser map visual QA were not run. Offline scientific fixtures and small live
queries do not substitute for those gates. Production products/releases remain untouched.

## Measured performance

[Machine-readable measurements](performance.json) include environment, sizes and RSS.
These are single bounded samples; query memory is a cumulative process peak, not isolated
per-stage memory, and no broad/regional speedup is claimed.

| Work | Size | Measured time |
| --- | --- | ---: |
| Baseline clipping | 500 synthetic ordinary polygons | 0.533 s |
| Hardened clipping | Same 500 polygons | 0.428 s |
| Cold native Alaska query | 2 provider features/parts, 24,904 decoded bytes | 2.642 s total; 2.533 s acquisition/cache stage |
| Warm offline native query | Same 2 records, zero network bytes | 0.099 s total; 0.003 s cache stage; 0.026 s normalize/select |
| Cold H3 Alaska query | 4 features/parts, 3 R7 cells, 8 memberships, 37,106 bytes | 2.784 s total; 0.006 s overlay |
| Warm offline H3 query | Same records/cells/memberships, zero network bytes | 0.120 s total; 0.038 s normalize/select; 0.006 s overlay |

Clipping peak RSS: approximately 165 MB baseline and 165 MB hardened. The query process
peaked near 172 MB. A cold baseline API/acquisition benchmark would not be comparable:
the old getter did not exist and the old acquisition could truncate results.

## Runnable usage

```python
from governance import get_marine_protected_areas, get_fishery_management_areas

mpas = get_marine_protected_areas(
    (-125.0, 44.0, -123.0, 46.0), workspace="/path/to/research-workspace",
    sources="odfw_marine_reserves_2016", allow_partial=True,
)
subareas = get_fishery_management_areas(
    (-123.4, 48.4, -123.38, 48.42), workspace="/path/to/research-workspace",
    systems="dfo.pacific.pfma.subareas", allow_partial=True,
)
# After acquisition, repeat with mode="offline". Add make_h3=True with the h3 extra.
```

```sh
governance --workspace /path/to/workspace get marine-protected-areas \
  --bbox -125 44 -123 46 --source odfw_marine_reserves_2016 --allow-partial
governance --workspace /path/to/workspace availability
```

## Remaining qualification gaps

The [machine-readable matrix and coverage notes](coverage.md) record exact blockers:
BC provincial marine inclusion taxonomy and authoritative field/terms qualification;
Oregon fishery vector/identity contracts; DFO whole-area/current applicability and redistribution;
other Alaska fisheries and Arctic support; Indigenous territories/treaties/rights beyond
administrative references; named safety/security/anchoring systems and historical instruments;
Nitinat authoritative coastline/border support; and moving-animal rule context. Seven catalog
families remain planned. Every implemented family remains a research reference, model-ineligible.
Legacy caches missing reconciled scope/completeness receipts need explicit migration/reacquisition
in a new workspace; pin changes are never automatic. None of these gaps is converted into zero.
