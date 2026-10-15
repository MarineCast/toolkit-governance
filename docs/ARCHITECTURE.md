# Architecture and navigation

`governance` owns acquisition, source normalization and geometric metrics on explicit H3 grids.
The public `products` API writes [flat Parquets](parquet-products.md), an update catalog and
original dataset extents. Applications own ecological interpretation, grid selection and
temporal eligibility. Native GeoParquet and manifests exist only as temporary implementation
intermediates during a normal build. There is no application runtime dependency, sibling-path
import, shared core package or implicit source download.

| Surface | Ownership |
| --- | --- |
| `governance.__init__` | Public configuration and workspace initializer |
| `governance.cli` / `python -m governance` | CLI routing and explicit workspace selection |
| `governance.h3_matrix` | Internal explicit H3 overlay; see [contract](h3-matrix.md) |
| `protected_areas/*`, `jurisdiction/*`, `fisheries_management/*`, `administrative_context/*`, `vessel_management/*` | Seventeen family-owned source, build and inspection workflows |
| `preflight` | Read-only source and catalog readiness inventory |
| `delivery` | Verified overlay projection into one wide table per supplied resolution |
| `products` | Public offline build, flat output replacement and catalog/Parquet validation |
| `releases`, `study`, `shared_contract` | Historical artifact compatibility/regression utilities; retired CLI |
| `shared/` | Native schema, acquisition, clipping, coverage, manifests, catalog and map descriptors |
| `_config/` | Private composed YAML, redaction, path and presentation support |
| `maintenance/catalog.py` | Explicit 24-collection registry and deterministic catalog generator |
| `resources/config/` | Installed defaults copied by `init`; never runtime output storage |
| `config/` | Editable checkout defaults; keep synchronized with packaged resources |

Preserve the per-family public entry points (`download`, `build`, `inspect`) and shared contracts.
The flat builder runs configured native modules in temporary storage. Catalog validation uses the
explicit registry, not empty source directories that disappear during wheel packaging. The map
inspector forwards its selected configuration to catalog validation.

Configuration composition retains mapping deep-merges, list replacement, references, environment
values, include-cycle checks and redacted configuration hashes. Paths resolve under the selected
workspace. Defaults require initialization; there is no silent fallback to an application checkout.
The shared loader rejects unknown root/source/collection/clipping/path/inspection keys, malformed booleans and reference cycles. The named `full_area` restriction remains an explicit current limitation.

## Graphify

Graphify is optional developer tooling, not a package dependency. Use isolated `graphifyy==0.9.62`
with Python 3.10+. From this repository:

```sh
graphify extract . --code-only
graphify explain "build_collection"
graphify affected "build_collection" --relation calls --depth 1
```

Use the existing local graph for ownership and relationship queries, then inspect source/tests.
For a quick navigation graph without clustering use `--no-cluster`. Rebuild after structural
changes, not every question. `.gitignore` and `.graphifyignore` exclude data, build outputs,
migration archives and caches. Code-only extraction does not semantically index prose or prove
runtime dynamic-import relationships. Source/tests are authoritative.

`graphify-out/` is a disposable local-only cache. Never commit or publish it, install agent hooks
implicitly or build a MarineCast-wide graph. This repository owns its graph independently of
other toolkits. See [migration validation](MIGRATION.md) for the observed run.

`preflight` inventories source and catalog readiness. `products.build_products` stages
normalization, a metrics-only overlay and original extents, then replaces a validated flat
directory. `products.export_products` projects a verified internal matrix without releases.
The single-layer [query engine](query-api.md) remains an in-memory scientific API.
