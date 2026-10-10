# CLI reference

This reference matches `governance.cli` in main at
`65fbebb3416673fbd147f4a4d634fa34b8df7679`, inherited by the docs branch.
Run `governance COMMAND --help` for exact argument syntax in your installed revision.
Place the global `--workspace` before the command. The additional frozen-study commands are documented in the [study guide](study-guide.md);
install a reviewed revision containing PR7 to use them.

| Command | Required inputs and effects |
| --- | --- |
| `init` | Copies missing defaults; no acquisition or overwrite |
| `catalog [--config FILE] [--verify-artifacts]` | Validates catalog; optional checksum checks of present primary products; missing products are skipped |
| `preflight` | Read-only inventory using workspace default config; no `--config` flag |
| `download COLLECTION [--config FILE] [--overwrite]` | Explicit acquisition into configured raw paths; may require source-specific provisioning |
| `build COLLECTION [--config FILE] [--allow-partial] [--overwrite]` | Native build from local inputs; primary/secondary writes are per file |
| `inspect --as-of YYYY-MM-DD [--config FILE] [--output FILE]` | Writes consolidated map HTML and map manifest |
| `export-h3-matrix --grid FILE --output FILE --length-crs CRS [--config FILE] [--allow-partial] [--overwrite]` | Requires `h3` extra and verified native products; explicit grid only |
| `export-delivery --matrix FILE --output-directory DIR --release-id ID --software-revision SHA` | Projects verified overlay into separate wide tables and companions per resolution |
| `export-shared-manifest --artifact FILE --local-manifest FILE --schema FILE --schema-reference REF` | Requires `contract` extra; validates against caller-supplied pinned schema admitting `reference_geometry`; writes new shared companion |
| `publish-generation --source DIR --release-root DIR --release-id ID --scientific-method-version VERSION --software-revision SHA` | Copies quiescent prepared inputs, hashes/verifies members and atomically activates local generation |
| `verify-generation PATH` | Reads generation membership and hashes; baseline does not establish scientific completeness |
| `activate-generation --release-root DIR --release-id ID` | Verifies and selects an existing immutable generation; no data rewrite |

`SHA` is a full 40-character lowercase Git SHA, not a branch name. Choose a new
release ID using letters, digits, underscore, dot or hyphen, starting with a letter
or digit and at most 128 characters. Generations cannot be overwritten. Source and
release root must be separate, non-nested directories; symlinks are forbidden.
The baseline publisher checks bytes and membership. Scientific acceptance is a
separate requirement; PR7 adds a semantic activation gate for study-contract bundles.

```sh
governance --workspace /path/to/workspace export-delivery \
  --matrix /path/to/governance-h3-metrics.parquet \
  --output-directory /path/to/new-delivery \
  --release-id research-v1 --software-revision FULL_40_CHARACTER_GIT_SHA
governance export-shared-manifest \
  --artifact /path/to/new-delivery/governance-inventory-r6.parquet \
  --local-manifest /path/to/new-delivery/governance-inventory-r6.manifest.json \
  --schema /path/to/approved-schema.json --schema-reference PINNED_SCHEMA_REFERENCE
```

Confirm the delivery paths printed by `export-delivery` in your installed revision. A schema reference must identify the reviewed
schema revision; schemas are never fetched implicitly. Export does not authorize
redistributing datasets. See [contracts](CONTRACTS.md) for native/shared distinctions.
