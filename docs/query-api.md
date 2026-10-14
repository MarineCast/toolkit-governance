# Query one layer

This API returns in-memory research objects. For public data files use the
[flat Parquet build](parquet-products.md); getters do not write delivery companions.

```python
from governance import get_marine_protected_areas

result = get_marine_protected_areas(
    (-125.0, 44.0, -123.0, 46.0),
    workspace="/path/to/new-research-workspace",
    allow_partial=True,
    make_h3=False,
)
print(result.features)
print(result.coverage)
```

H3 is included in the base installation from version 0.3. Pass `make_h3=True` to
request in-memory cell metrics at one resolution (default 7); `False` returns native
features without calculating cell metrics. Each logical catalog collection has
`get_<collection>`; `get_fishery_management_areas` aliases `get_management_areas`, and
`get_marine_protected_area` aliases its plural. Planned collections raise
`LayerNotImplementedError`; they never return a successful empty inventory.

## Shared options and return value

`get_layer(collection_id, bounding_box, *, make_h3=False, h3_res=7, sources=None,
systems=None, workspace=None, cache=None, config=None, config_path=..., allow_partial=False,
include_proposed=False, mode="cache-first", as_of=None, budget=None,
max_cells=100000, max_memberships=1000000)` is the common engine. Named wrappers accept
one bounding box and the same keyword options. `sources` and `systems` currently select
exact configured source IDs (and canonical WDFW/DFO/ADF&G system IDs); these mutually exclusive options never infer equivalence
between recreational, commercial, reporting, Indigenous or routing systems. Explicit
`GovernanceConfig` objects and workspace-relative configuration avoid process-global
workspace mutation. The CLI retains its environment precedence.

The stable `GovernanceResult` contains:

| Field | Contract |
| --- | --- |
| `features` | Native EPSG:4326 GeoDataFrame, including a valid empty schema |
| `h3` | One-row-per-cell DataFrame at one resolution; `None` without H3 |
| `memberships` | Exact cell/source/feature/record/part relationships; `None` without H3 |
| `coverage` | Requested scope, each provider's receipt status, geographic limitations and legal-currentness qualification |
| `provenance` | Source hashes, rights, query receipts, versions, separate retrieval/query time and bounded stage timings |

A successful zero-match query has `coverage.status="empty"`. Unavailable input has
`status="unavailable"`, including when `allow_partial=True` returns available providers.
A verified source-query receipt establishes acquisition completeness only. Geographic
completeness and current legal applicability remain separately qualified. Neither state
establishes universal legal absence. Partial/unknown support needs `allow_partial=True`.

`as_of` is rejected for these static inventories, including a nominal current date:
there is no legal-history engine. Known exact dates remain source attributes. Establishment
years stay years, and malformed/ambiguous dates fail validation. Epoch milliseconds require
an explicit ArcGIS field/provider declaration. Missing retrieval evidence stays null;
query/build time does not overwrite first-known evidence.

## Cache and network modes

- **cache-first** validates compatible cached receipts, then acquires missing support.
- **refresh** retrieves a replacement into staging and validates it before replacement.
- **offline** never makes network calls; incompatible scope or selectors fail explicitly.

Only the getters and explicit download commands acquire data. Install, initialize, build,
inspect and release commands do not gain implicit network access. Getter initialization
copies missing defaults into its explicit workspace. `cache` selects a separate raw-cache
root; relative configured inputs still use the workspace. Request caches include layer,
provider, source vintage, selector, mask and spatial support in their identity. An existing
verified superset can serve a smaller query. Mask-selected or smaller caches cannot silently
serve a larger request. Legacy snapshots lacking reconciled complete receipts remain readable
for migration inspection, but request-aware builds/getters reject them with a migration message.
Derived/local vectors require their own provider/version/selector/support receipt even when their bytes are pinned. A `full_source_dataset: true` receipt explicitly qualifies an unfiltered vector; a bounded receipt needs reconciled completeness and containing bounds. Use a new workspace to reacquire them; old caches/releases and source pins remain intact.

Default acquisition caps are 64 MB decoded response bytes per query, 50,000 source features
per source and 2,000 requests per source. One ArcGIS response is capped at 16 MB, with bounded
connect/read timeouts, three transient attempts and exponential backoff. An ID roster is
reconciled before/after bounded geometry batches. Pagination fallback requires declared
pagination and ordering capability plus exact before/after counts. Empty and short pages
advance by the requested service window. Data are spooled rather than collecting unbounded
national pages. Direct archives are capped and exact expected pins are checked again before
normalization. Pins are never silently updated. Unqualified bulk/source-frame workflows
report their provisioning blocker.

## H3 and spatial semantics

Bounding boxes use `(west, south, east, north)` in degrees. `west > east` wraps across the
antimeridian. Native queries select intersecting **full feature boundaries**, split at the
dateline where needed; they do not truncate boundaries at the query edge. H3 queries expand
source selection to the complete intersecting cells and retain their full native support.
This avoids computing full-cell metrics from bbox-truncated geometry. It can return features
just outside the user rectangle that intersect those cells.

Candidate cells use overlap containment and exact final intersection, including polygons
with no cell centre. Cell/member budgets reject oversized requests. Polygon/line boundary-only
touches are excluded; points on boundaries count in each touching cell. Memberships preserve
native parts and source record identity. Metrics group by source; proposals have a separate
`__proposed` group and are excluded by default. Feature, designation, source-record and part
counts describe different entities. Polygon coverage unions overlap within its group and uses
antimeridian-safe equal-area square metres divided by full cell area. Line measures use WGS84
geodesic metres. Points count distinct coordinates; no water-only denominator is inferred.
Empty intersections under qualified partial coverage retain null counts/measures.

Generic getters support wrapped native/H3 geometry. This engineering support does **not**
qualify all Aleutian/Arctic source inventories. The legacy explicit study overlay retains its
regional CRS and existing metric definitions and still rejects dateline grids.

## CLI

```sh
governance --workspace /path/to/workspace get marine-protected-areas \
  --bbox -125.0 44.0 -123.0 46.0 --h3-res 7 --allow-partial

governance --workspace /path/to/workspace get fishery-management-areas \
  --bbox -124 47 -122 49 --source wdfw_recreational_marine_areas \
  --mode offline --allow-partial --output /path/to/new-output-directory
```

The CLI prints qualified coverage and row counts; `--output` writes native/H3/membership
Parquet plus coverage/provenance JSON into a new directory. Existing build/download/inspect,
study, delivery and release commands retain their entry points; see the [advanced workflows](WORKFLOWS.md).

## Compatibility and failure boundaries

Version 0.2 / `native-reference-2.0` changes date precision, marine-area fallback and retained
measure calculations. Existing native products and their hashes remain readable; rebuilds
record the new method rather than silently relabeling older releases. Semantic hashes cover
ordered native values and geometry independently of build metadata/Parquet byte encoding.
Native artifact/manifest staging rolls back handled failures under a per-product writer lock;
readers still verify exact hashes. Two renames are not a crash-atomic or workspace transaction.
Use the existing immutable-release envelope when coherent multi-product publication is authorized.


## Coverage inventory

`governance availability` prints the [packaged availability matrix](coverage.md), covering
all 24 catalog layers and eight separate regional qualifications. Seventeen reference
families have adapters; seven are planned. New source dispatch includes ODFW's pinned 2016
reference, ADF&G groundfish reporting polygons, and closed-ring subsets of the TC 2026
instrument. BC provincial classifications, DFO whole-area/legal applicability, Oregon fisheries, complete
Alaska fishery systems, universal Indigenous territory/rights and legal history remain gaps.

Version 0.2.1 uses `native-reference-query-2.1` and rebuild method `native-reference-2.1`.
Intersections recursively retain only components of the original geometry dimension; polygon
area and line length survive collections with boundary remnants. All fragments from one
native part yield one membership. Boundary-only polygon/line contacts remain excluded.
Repair denominators and retained numerators use the same original dimension. Source support
is split at the dateline before measuring geodesic segments; bounded roundoff is snapped only
after finite/range checks. Historical products and legacy H3 metric definitions are unchanged.

Query provenance adds `producer.package`, `producer.version`, `producer.code_revision`
and `producer.code_revision_source`. Revision comes only from matching installed VCS
metadata; ordinary wheels/editable source runs return null/unavailable without embedded
revision evidence. Git is not a runtime dependency and cwd is never used to guess a revision.
Source retrieval timestamps remain separate from query time.

A missing direct-cache receipt fails by default. The legacy ZIP exception additionally requires
`immutable_full_source_archive: true`, direct-archive acquisition, a configured verified SHA-256,
an unfiltered `1=1` selector, no mask and no server filtering. This explicitly qualifies the
configured full archive/member inventory, not geographic/legal completeness. The configured
Census, IBC, NRCan, NOAA inventory/ONMS and ODFW pinned ZIPs declare that contract; existing pins
are unchanged. Derived/local vectors and other archives still need compatible receipts.
Only reviewed source qualification can declare this contract; pinning a user-created subset
does not establish full-source meaning. Malformed/mismatched existing receipts always fail. A new acquisition receipt cannot be used
to claim that an unapplied selector/mask was honored.

Geometry repairs report their status, source-dimension remnants and diagnostic measure change. Pre-repair measures of invalid shapes are QC evidence, never certified area/length.
