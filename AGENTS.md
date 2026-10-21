# Governance Toolkit agent guidance

This checkout owns marine governance acquisition, source normalization and H3 metric products.
It has no application or sibling-toolkit runtime dependency. Start with README.md and the
[Parquet output contract](docs/parquet-products.md); source and tests are authoritative.

## Public outputs

- Write one static and at most one dynamic metric Parquet per supplied H3 resolution in
  `Data/Governance`, a small `catalog.json` with update times per collection/domain area,
  and one source GeoParquet per dataset under `OriginalData/<source-id>/geometry.parquet`.
- Public rows are H3 cell × metric columns; dynamic rows add a typed source-backed `date`.
  Preserve supplied grid membership and resolution. Never manufacture a dated history
  from source retrieval/build times, establishment years or unknown effective dates.
- No public releases, generation directories, current pointers, manifests, crosswalks or
  duplicated native/study bundles. Native products/manifests and reconciliation outputs
  are temporary implementation intermediates. Production entry points are build/export/validate, explicit acquisition, initialization and
  read-only catalog/preflight. Query/get, inspection, study and release runtimes are not public APIs.
- OriginalData preserves original retrieved feature extents and attributes before toolkit
  clipping, source IDs, receipt scopes and date evidence. Store shared sources once.
  Acquired feature selections do not imply an exhaustive global polygon inventory.

## Scientific and operational boundaries

Preserve units, source systems, feature/part identity, union/denominator semantics, citations,
rights, source vintage and missingness. Unknown/unavailable/partial are distinct from zero.
Native normalization is EPSG:4326 with no implicit H3 grid; public overlays use an explicit
consumer grid. `MODEL_ELIGIBLE` remains false. Geometry, legal authority, effective time,
source observation time and system receipt time remain distinct quantities.

Workspace precedence is CLI `--workspace`, then `GOVERNANCE_WORKSPACE`, then cwd. Package
resources are read-only defaults; `init` preserves edits and downloads nothing. Acquisition
is explicit and bounded. Builds are offline; partial coverage and replacement require their
explicit options. Inspect acquisition, processing, cleanup and replacement effects first.
No source-data redistribution or automatic hosting is authorized by an ordinary build.

Read [contracts](docs/CONTRACTS.md), [the application handoff schema](src/governance/resources/app_contract.json),
[architecture](docs/ARCHITECTURE.md), affected family
`DATA_SOURCES.md` and source/tests for scientific changes. Configuration and packaged defaults
must remain byte-identical. The registry has sixteen implemented acquisition collections. Seven presentation families
group the application features; acquisition collections and displayed features are distinct.
Do not use stale organization/navigation summaries as contract authority.

## Verification

Run focused scientific/product tests, then the full suite for behavior changes. Validate a
regular wheel outside the checkout with OrcaCast/application imports blocked and `pip check`.
For prose, verify links, build strict MkDocs, and run `git diff --check`. Report native/regional,
live-provider, scientific and consumer paths separately; offline fixtures are not observations.
Use scoped `rg` for known paths; Graphify caches are optional, disposable and local-only.
Never publish graphs or build a workspace-wide graph merely for navigation.
