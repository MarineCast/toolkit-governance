# Delivery and local publication CLI

These commands operate on retained inventory products and local releases. See
the [basic CLI reference](reference/cli.md) for workspace, acquisition, build,
inspection, and overlay commands, and the [study guide](study-guide.md) for
frozen-study inputs and semantic validation. Run command help from the installed
revision before operational use.

| Command | Required inputs and effects |
| --- | --- |
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
separate requirement; the publisher includes a semantic activation gate for study-contract bundles.

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
