# Workflows and operational boundaries

The normal workflow is the [flat Parquet build](parquet-products.md): initialize
an explicit source workspace, review configuration and source rights, acquire
inputs explicitly, build supplied H3 grids, and validate `Data/Governance`.

Acquisition writes qualified raw caches in the source workspace. Builds never
download implicitly. Public outputs contain only resolution-specific static/optional
dynamic metric Parquets, `catalog.json`, and `OriginalData/<dataset>/geometry.parquet`.
Native family products, manifests and reconciliation diagnostics are temporary
implementation intermediates. No release, publication, activation or rollback
command is required for governance data.

An existing flat output requires `--overwrite`; it is checked before replacement.
A verified OriginalData directory can supply future offline builds, and the static
metric files themselves can supply the grid. Provider/version/selector/support
receipts must still agree with configuration. Last-update timestamps do not refresh
source vintage or establish present legal applicability.

## External local inputs

International-boundary reconciliation still requires configured NOAA maritime,
DFO bioregion and seascape water support. They are data inputs, not sibling Python
imports. Their original source attribution and unknown retrieval times are retained.
No sibling checkout is searched implicitly.

## Development checks

```sh
python -m pip install -e '.[test,docs]'
python -m pytest -q
python -m pip wheel --no-deps --wheel-dir dist .
mkdocs build --strict
git diff --check
```

Validate a regular wheel from outside the checkout with application imports blocked.
Keep checkout and packaged configuration byte-identical. Synthetic/offline tests do
not establish live source availability, legal currency or scientific accuracy.
Old study/generation helpers and their regression tests concern historical artifacts;
their CLI and public output workflow are retired. See [migration](MIGRATION.md).
