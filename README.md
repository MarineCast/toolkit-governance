# Governance Toolkit

<img src="docs/assets/governance-toolkit-banner.png" alt="Coastal chart with governance boundaries" width="100%">

`toolkit-governance` produces marine governance metrics on explicit H3 grids and
retains original source shapes. It installs independently as the `governance`
Python package and CLI, with seventeen implemented collections and seven planned families.

The public output is `Data/Governance`: one static Parquet per resolution, one
optional dynamic Parquet per resolution, a small `catalog.json` with update times,
and `OriginalData/<dataset>/geometry.parquet`. There are no data release directories
or companion manifests. Static rows are H3 cells × metric columns; dynamic rows
add a typed `date`. Current inventories are static and model-ineligible.

```sh
python -m pip install .
governance --workspace /path/to/source-workspace init
# Explicitly acquire/provision qualified local sources after reviewing their configuration.
governance --workspace /path/to/source-workspace build \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --output-directory /path/to/Data/Governance --allow-partial
governance validate-data /path/to/Data/Governance
```

Read the [Parquet output guide](docs/parquet-products.md) for updates from retained
originals, Python usage, exact filenames, embedded provenance, source rights and
validation. Builds use temporary intermediates and do not download implicitly.
Source workspace precedence is `--workspace`, `GOVERNANCE_WORKSPACE`, then cwd;
package resources are read-only defaults. Partial coverage, nulls and observed zeros
remain distinct. Original geometry and source dates do not certify current law.

- [Product contracts](docs/CONTRACTS.md) and [architecture](docs/ARCHITECTURE.md)
- [Sources and rights](docs/reference/sources.md), [layers](docs/layers.md), and [query API](docs/query-api.md)
- [CLI](docs/reference/cli.md), [workflows](docs/WORKFLOWS.md), and [documentation site](docs/documentation-site.md)

```sh
python -m pip install -e '.[test,docs]'
python -m pytest -q
mkdocs build --strict
git diff --check
```

Software uses the [Apache-2.0 license](LICENSE). Data rights remain source-specific.
The wheel contains no acquired datasets. Offline tests are software validation;
live source availability and scientific/legal qualification require separate evidence.
