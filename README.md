# Governance Toolkit

`toolkit-governance` builds qualified marine governance reference products on an explicit H3 grid. The independent `governance` Python package and CLI preserve original source geometry, attributes, identity and retrieval evidence alongside cell-level outputs.

The final output contains `governance-r<resolution>-static.parquet`, an optional source-dated dynamic table per resolution, `catalog.json`, and `OriginalData/<source-id>/geometry.parquet`. Each full R6/R8 static table contains the twenty selected features plus `h3_index` (21 columns). Membership columns contain readable name lists. New v5 products preserve original typed memberships, support arrays and scientific metadata inside the final Parquets, without external audit files. Successful ordinary builds remove their disposable source caches, native intermediates and coverage files after final validation. Current inventories are static, partial and model-ineligible. Recorded geometry does not establish current law or complete jurisdiction.

Start with the [offline quickstart](docs/how-to-use.md), [configuration](docs/configuration.md) and [product contract](docs/parquet-products.md). The [family guide](docs/layers.md) documents each displayed feature, its source meaning, processing and limitations. [Coverage and refresh](docs/coverage.md) separates source receipt completeness from geographic and legal qualification.

```sh
python -m pip install .
governance --workspace /path/to/workspace init
governance --workspace /path/to/workspace build \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --original-data /path/to/retained/Governance \
  --output-directory /path/to/new/Governance \
  --allow-partial
governance validate-data /path/to/new/Governance
```

The retained directory must include its catalog and verified originals. Legacy v2–v4 products still require their bound external audits; these remain readable and are protected from cleanup. Existing products are not rewritten automatically. Builds never download sources. Shared, unrecognized or protected inputs prevent cache cleanup; `--keep-workspace-data` is an explicit diagnostic opt-out. Failed builds retain source caches. Installation and initialization acquire no datasets.

See [CLI and Python API](docs/reference/cli.md) and [developer checks](docs/WORKFLOWS.md). Software uses [Apache-2.0](LICENSE); source data rights are provider-specific and are not granted by the software license.

The [2026-10-29 reproducibility review and map gallery](docs/reproducibility-review.md) records the bounded real-data check, required external audit files, exact replay commands and examples for all twenty delivered fields.
