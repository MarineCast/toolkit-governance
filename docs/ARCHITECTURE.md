# Architecture and navigation

`governance` owns acquisition, source normalization, native-geometry publication and inspection.
Applications own ecological interpretation, grid selection and temporal eligibility. The optional
`h3_matrix` module performs a species-neutral geometric overlay only on an explicit consumer grid;
it produces a separate model-ineligible context product, retaining canonical native products.
There is no
application runtime dependency, sibling-path import, shared core package or implicit source download.

| Surface | Ownership |
| --- | --- |
| `governance.__init__` | Public configuration and workspace initializer |
| `governance.cli` / `python -m governance` | CLI routing and explicit workspace selection |
| `governance.h3_matrix` | Optional explicit H3 overlay export; see [contract](h3-matrix.md) |
| `protected_areas/*`, `jurisdiction/*`, `fisheries_management/*` | Six family-owned source, build and inspection workflows |
| `shared/` | Native schema, acquisition, clipping, coverage, manifests, catalog and map descriptors |
| `_config/` | Private composed YAML, redaction, path and presentation support |
| `maintenance/catalog.py` | Explicit 24-collection registry and deterministic catalog generator |
| `resources/config/` | Installed defaults copied by `init`; never runtime output storage |
| `config/` | Editable checkout defaults; keep synchronized with packaged resources |

Preserve the per-family public entry points (`download`, `build`, `inspect`) and shared contracts.
The CLI dispatches through configured collections to those modules. Catalog validation uses the
explicit registry, not empty source directories that disappear during wheel packaging. The map
inspector forwards its selected configuration to catalog validation.

Configuration composition retains mapping deep-merges, list replacement, references, environment
values, include-cycle checks and redacted configuration hashes. Paths resolve under the selected
workspace. Defaults require initialization; there is no silent fallback to an application checkout.
The inherited dataclass loader does not enforce a complete strict unknown-key schema; do not
claim that it does. The named `full_area` restriction remains an explicit current limitation.

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

`preflight` inventories every source and catalog family; `delivery` projects single-resolution
wide snapshot tables; `releases` provides immutable local multi-artifact generations and verified
activation/rollback. See [production readiness](production-readiness.md) for operational boundaries.
