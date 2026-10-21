# CLI and Python API

Run `governance --help` and `governance COMMAND --help` for the installed version's options. Put global `--workspace` and optional `--env-file` before the command.

| Command | Purpose / main options |
| --- | --- |
| `init` | Copy missing configuration; no acquisition |
| `availability` | Read configured regional source qualifications |
| `preflight` | Inspect readiness without acquisition |
| `catalog` | Validate source/collection catalog; `--config`, optional `--verify-artifacts` |
| `download COLLECTION` | Explicit source acquisition; `--config`, `--overwrite`; source provisioning limits apply |
| `build` | Offline public build; repeat `--grid`, `--output-directory`, optional `--original-data`, `--config`, `--allow-partial`, `--length-crs`, `--software-revision`, `--overwrite`, `--keep-workspace-data` |
| `export-data` | Export an already built internal matrix; `--matrix`, `--output-directory`, `--config`, `--software-revision`, `--overwrite` |
| `validate-data DIRECTORY` | Verify flat outputs and embedded contracts |
| `clean-workspace DIRECTORY` | Verify retained output/originals before disposable workspace cleanup; `--config` |

Use `build` for ordinary refresh. An internal matrix is not a public output contract. Cleanup can fail closed for shared, protected or unrecognized inputs. Preserve input data until validated replacements exist.

## Python product API

```python
from governance.products import build_products, export_products, validate_products

output = build_products(
    ['/absolute/grid.parquet'], '/absolute/review/Governance',
    config_path='/absolute/workspace/config/data/governance/governance.yaml',
    original_data='/absolute/retained/Governance',
    allow_partial=True, keep_workspace_data=True,
)
validation = validate_products(output)
```

Both product writers accept `workspace` and `env_file`. Explicit arguments override process environment, selected `.env` settings and configuration defaults. `build_products` accepts `length_crs` (default `EPSG:32610`), `software_revision` and `overwrite` in addition to the arguments above. It performs temporary native normalization/overlay and exports a validated flat product offline. `export_products(matrix, output_directory, ...)` is the lower-level exporter. Neither implicitly acquires sources.

See [configuration](../configuration.md) for workspace/path precedence and optional run settings, [quickstart](../how-to-use.md) for grid schema, and [product contract](../parquet-products.md) for outputs and errors. Retired study/release commands are not production delivery interfaces.
