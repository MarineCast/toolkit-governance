# toolkit-governance agent guidance

## Scope and required reading

This repository owns the standalone `governance` package for species-neutral native-geometry
marine protected areas, jurisdictional reference boundaries and fisheries management products.
Six collection pipelines are implemented; the 24-entry catalog also includes 18 planned families.
Read [architecture](docs/ARCHITECTURE.md) for ownership/import changes, [contracts](docs/CONTRACTS.md)
for scientific changes, and [workflows](docs/WORKFLOWS.md) before producer execution. Read the
[README](README.md) and [migration report](docs/MIGRATION.md) for setup and extraction evidence.
Preserve unrelated changes and read deeper instructions before editing a subdirectory.

## Shared MarineCast context

For repository boundaries, dependencies, shared schemas/provenance or application integration,
read the MarineCast [infrastructure guide](https://github.com/MarineCast/.github/blob/HEAD/INFRASTRUCTURE.md).
Resolve paths from this checkout: `../../.github/INFRASTRUCTURE.md` in the grouped workspace or
`../.github/INFRASTRUCTURE.md` in a flat clone layout. Prefer a local copy; otherwise read the
linked guide and report if unavailable. Sibling agent instructions are not automatically inherited.

Ecosystem architecture and the proposed H3 manifest v0.1 remain in the organization documentation
repository. Governance's native-geometry manifests are separate and are not H3-contract adoption.
Do not add a common core package, application dependency or sibling-filesystem import implicitly.

## Scientific contracts

- Preserve EPSG:4326 native geometry, source identity, feature IDs and unique geometry-part IDs.
  No H3 columns or hard-coded model grid belong in canonical products.
- Keep reference/cartographic geometry, derived country-water support and controlling legal
  authority distinct. Preserve jurisdiction, citations, source status, effective dates, learned
  time, retrieval time, source vintage, licenses and redistribution limitations.
- Keep unknown, unavailable, partial and not-applicable support distinct from observed absence.
  Never turn a missing source or empty intersection into zero/false without authoritative coverage.
- All fields remain model-ineligible by default. Ecological inference, policy-response leakage,
  optional H3 overlays and model eligibility belong to downstream explicit validation.
- Preserve source-specific normalization, antimeridian clipping, geometric support and units.
  Map simplification is presentation-only. Document changed calculations explicitly.

## Workspace and execution

Install in an isolated Python 3.11+ environment using `python -m pip install -e '.[test]'`.
Workspace precedence is CLI `--workspace`, then `GOVERNANCE_WORKSPACE`, then cwd; package resources
are read-only defaults. `governance init` copies missing config/catalog files and never downloads.
Relative paths inside any config resolve against the workspace, including when the config path
is absolute. Keep `config/` and `src/governance/resources/config/` byte-identical.

Acquisition, build and inspection are explicit operations. Read workflow effects first; preserve
raw snapshot pins and validated products. Partial builds need `--allow-partial`; replacement needs
`--overwrite`. Per-file atomic writes do not imply a multi-product transaction. Reconciliation
requires provisioned external spatial-support inputs; do not silently search an application tree.
Historical migrated local artifacts retain original provenance and need separate rebuild validation.
Keep downloads, local migration evidence, build outputs and credentials out of tracked source.

## Validation and completion

Run `git status --short` before edits and inspect the diff afterward. Behavior changes require
focused tests, then `python -m pytest -q`; package/resource changes also require a regular wheel
installation outside the checkout with a new external workspace. Block application imports in
that smoke test. Documentation-only work needs references and `git diff --check`.
State acquisition, regional rebuild, map visual QA, platform and integration boundaries accurately.
No network or regional science run was established by the extraction's offline tests.

For the optional explicit H3 overlay, read `docs/h3-matrix.md`, install `.[test,h3]`,
and run `python -m pytest -q tests/test_h3_matrix.py` followed by the full suite.
It derives a separate model-ineligible consumer-grid product; canonical native
schemas and manifests retain their no-H3 contract. A regional overlay requires
verified native products, an explicit grid and an explicit metre-based length CRS.

## Codebase navigation

Use `graphify-out/graph.json` for structural questions, then read authoritative source/tests.
Skip graph work for obvious targeted edits. Use `rg` for literals/configuration/prose and ast-grep
for syntax patterns. Graphify is optional isolated developer tooling (`graphifyy==0.9.62`), not a
runtime dependency. On the extraction machine it is installed in `~/.local/share/graphify-venv`.

From this checkout only:

```sh
graphify extract . --code-only
graphify cluster-only .
graphify export html
graphify explain "build_collection"
graphify affected "build_collection" --relation calls --depth 1
```

Use `extract . --code-only --no-cluster` for a quick structural graph. Refresh after structural
edits; do not rebuild for each question. `.gitignore` and `.graphifyignore` exclude generated data,
builds and local migration archives. Code-only extraction skips prose semantics and does not prove
dynamic imports; inspect source when coverage is incomplete. The graph/report/HTML are disposable
local-only caches: never commit or publish them or enable hooks implicitly. Do not run Graphify at
MarineCast root, grouping directories or `.github`. Source/tests outrank schemas, architecture and
this navigation cache. See the migration report for the observed graph run and its limitations.
