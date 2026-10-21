# Governance Toolkit

`toolkit-governance` builds qualified marine governance reference products on an explicit H3 grid. The independent `governance` Python package and CLI preserve original source geometry, attributes, identity and retrieval evidence alongside cell-level outputs.

The public output contains `governance-r<resolution>-static.parquet`, an optional source-dated dynamic table per resolution, `catalog.json`, and `OriginalData/<source-id>/geometry.parquet`. Current inventories are static, partial and model-ineligible. Recorded geometry does not establish current law or complete jurisdiction.

Start with the [offline quickstart](docs/how-to-use.md), [configuration](docs/configuration.md) and [product contract](docs/parquet-products.md). The [family guide](docs/layers.md) documents each displayed feature, its source meaning, processing and limitations. [Coverage and refresh](docs/coverage.md) separates source receipt completeness from geographic and legal qualification.

```sh
python -m pip install .
governance --workspace /path/to/workspace init
governance --workspace /path/to/workspace build \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --original-data /path/to/retained/Governance \
  --output-directory /path/to/new/Governance \
  --allow-partial --keep-workspace-data
governance validate-data /path/to/new/Governance
```

The retained directory must include its catalog and verified originals. Builds never download sources. Without `--keep-workspace-data`, successful builds attempt cleanup of verified disposable workspace caches; failed builds retain them. Installation and initialization acquire no datasets.

See [CLI and Python API](docs/reference/cli.md) and [developer checks](docs/WORKFLOWS.md). Software uses [Apache-2.0](LICENSE); source data rights are provider-specific and are not granted by the software license.
