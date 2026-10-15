# CLI reference

Use `governance --help` and command help from the installed revision. Global
`--workspace` precedes the command; output and grid paths are explicit process paths.
Configuration-relative source paths resolve against the selected source workspace.

| Command | Effect |
| --- | --- |
| `init` | Copy missing defaults; no acquisition |
| `download COLLECTION --config FILE [--overwrite]` | Explicit qualified source acquisition into the source workspace |
| `build --grid FILE [--grid FILE] --output-directory DIR [--original-data DIR] [--length-crs CRS] [--allow-partial] [--overwrite] [--keep-workspace-data]` | Offline normalization and overlay; write flat data, validate, then clean disposable workspace data |
| `export-data --matrix FILE --output-directory DIR [--overwrite]` | Project an existing internal overlay and retain original datasets |
| `validate-data DIR` | Read-only flat membership, checksum, grain and value/status validation |
| `clean-workspace DIR [--config FILE]` | Verify the saved flat output and retained source checksums, then remove disposable workspace `data/`; preserve the folder if it includes unretained/unrecognized data, symlinks or protected configuration/output |
| `catalog [--config FILE] [--verify-artifacts]` | Configured collections; optional retained internal-artifact checks |
| `availability`, `preflight` | Read source/collection readiness; no acquisition |
| `get COLLECTION --bbox WEST SOUTH EAST NORTH` | In-memory single-layer query; see query API for bounded acquisition and offline mode |

`build` and `export-data` accept `--config` and optional `--software-revision` for
software provenance. There is no release ID. Existing flat output needs explicit
`--overwrite`; partial source coverage needs `--allow-partial` for builds.
Successful builds clean disposable workspace `data/` by default; use
`--keep-workspace-data` to retain caches. Failed builds keep source data. Cleanup
does not affect external caches or final outputs. Future builds can reuse
`OriginalData` with `--original-data DIR`, or explicitly acquire fresh inputs.

The old `run-study`, generation publication/activation/verification, manifest export,
per-collection CLI build, `inspect`, and query multi-file export commands are retired.
Native normalization, reconciliation and historical validators remain Python
implementation utilities. Public data writes use the [flat Parquet contract](../parquet-products.md).
