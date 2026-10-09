# toolkit-governance agent guidance

## Scope and required reading

This repository owns the standalone `governance` package for species-neutral native-geometry
marine protected areas, jurisdictional reference boundaries and fisheries management products.
Fifteen collection build pipelines are implemented; the 24-entry catalog includes 9 planned
families. Critical-habitat acquisition remains explicitly budgeted/provisioned; read
[production readiness](docs/production-readiness.md) before operational execution.
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

## Task routing and validation

Run `git status --short` before edits, preserve unrelated work and read deeper instructions.
Load only the matching guidance; combine applicable gates and run the full suite once after
focused checks.

| Task | Guidance / checks |
| --- | --- |
| Setup / extraction history | [README](README.md) / [migration report](docs/MIGRATION.md), respectively |
| Ownership or imports | [Architecture](docs/ARCHITECTURE.md); focused tests, then full suite |
| Scientific / schema change | [Contracts](docs/CONTRACTS.md); focused tests, then full suite |
| Behavior change | `python -m pytest -q tests/<relevant_test>.py`, then `python -m pytest -q` |
| Documentation-only | Verify references/names, inspect diff and `git diff --check`; no package suite |
| Package / resources | Focused/full tests plus [installed-wheel acceptance](docs/agent-checks.md#installed-wheel-acceptance) outside the checkout in a new external workspace; block application imports |
| Explicit H3 overlay | [H3 matrix](docs/h3-matrix.md), `.[test,h3]`, `python -m pytest -q tests/test_h3_matrix.py`, then full suite |
| Acquisition / rebuild / inspection | [Workflows](docs/WORKFLOWS.md) and [production readiness](docs/production-readiness.md); review source pins, rights, paths and effects before execution |
| Preflight / delivery / immutable publication or rollback behavior | [Operational/release gates](docs/agent-checks.md#regional-and-release-boundaries), production readiness; focused config/workspace/release tests, then full suite |

The H3 overlay is a separate model-ineligible consumer-grid product; canonical native schemas and
manifests retain their no-H3 contract. Regional overlays require verified native products, an
explicit grid and an explicit metre-based length CRS. `catalog --verify-artifacts` skips missing
artifacts and is not whole-release acceptance; inspection HTML does not promote a release.
Historical products and offline tests are not new rebuild evidence. State acquisition, regional,
map visual QA, platform and integration boundaries accurately; inspect the diff and run
`git diff --check` before handoff.

## Navigation

Use scoped source search for known paths/literals. Existing graphs are optional for relationships;
check relevant source/manifest freshness and coverage first, then verify source/tests. Fall back
for stale/missing/incomplete indexes; no-match does not prove no use. Source/tests outrank
schemas/contracts, architecture and caches. [Navigation details](docs/agent-checks.md#codebase-navigation)
retain commands, exclusions and the local-only sharing policy. Do not install, rebuild, export,
overwrite instructions or enable hooks merely for a question; maintenance requires explicit scope.
