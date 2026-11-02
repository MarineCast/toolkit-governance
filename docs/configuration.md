# Configuration

Workspace precedence is CLI `--workspace`, then `GOVERNANCE_WORKSPACE`, then the current directory. Python product APIs also accept an explicit `workspace`. Package resources are read-only defaults, never the place for acquired data or output.

`init` copies missing configuration and catalog files without replacing user edits or acquiring data. Prefer absolute paths in commands. Relative configuration paths and paths inside YAML resolve against the workspace; an absolute alternate config file does not change that workspace.

| File | Purpose |
| --- | --- |
| `config/common.yaml` | Named WGS84 processing extent (`full_area`) |
| `config/data/governance/governance.yaml` | Sources, collections, clipping, coverage, input and intermediate paths |
| `config/data/governance/<category>/<collection>.yaml` | Family overrides of shared configuration |
| `config/data/governance/feature_catalog.yaml` | Acquisition collection metadata and implementation status |

Source definitions retain provider, acquisition type, source/local paths, exact pins, vintage, attribution, license, authority scope, redistribution terms and regional support. A configured source is not evidence of availability or complete geographic coverage. Do not auto-update pins, reinterpret blank rights as permission or extend a source's legal scope.

YAML supports mapping deep merges, list replacement, references, environment values and cycle checks. Unknown keys, malformed booleans, invalid bounds and invalid source references fail. Keep the required `full_area` name when changing bounds; revalidate source rosters and required subsets for the new extent.

For offline refresh, pass a complete verified flat directory through `--original-data`; the builder substitutes catalog-bound originals for configured source paths. See [refresh](coverage.md). `--output-directory` remains explicit. Presentation is a consumer responsibility; source and metric geometry remain scientific inputs.

Maintained repository `config/` defaults and `src/governance/resources/config/` must remain byte-identical. Personal workspace edits do not need to be copied into package resources. Source-specific receipt requirements and immutable archive exceptions remain in the authoritative family source notes. A pinned local subset does not establish full-source completeness.
## Optional run settings file

The CLI and `build_products` / `export_products` Python APIs accept `env_file`
(`--env-file` before the CLI command). The default is `.env` in the selected
workspace. An explicitly requested missing file fails before processing. Only
`GOVERNANCE_CONFIG`, `GOVERNANCE_OUTPUT_DIRECTORY`, `GOVERNANCE_GRIDS`, and
`GOVERNANCE_ORIGINAL_DATA` are read; unrelated settings and credentials are ignored.
No values are copied into the process environment. `.env` never selects workspace.

Precedence is explicit argument, process environment, selected `.env`, then packaged
configuration path default. Output and grids have no implicit defaults: build
requires both, export requires output and its explicit matrix argument. Grids in
the file/environment use a JSON array, for example
`GOVERNANCE_GRIDS='["/absolute/path/to/grid.parquet"]'` in a shell-style file.
Paths from the file resolve beside it. Explicit/environment paths preserve cwd
resolution, except configuration paths resolve against workspace. YAML paths
continue to resolve against workspace. Quotes and inline comments are supported;
variable interpolation, duplicate known keys, empty values and malformed known
settings fail with key/line diagnostics that omit values.

Copy `.env.example` to a local, ignored `.env` and edit the paths. No date settings
are provided: static governance inventory does not establish legal effective dates.
Overwrite, acquisition, partial coverage, and cleanup remain explicit API/CLI choices.
`resolve_settings` is a read-only resolver; it validates syntax and required settings,
while downstream product readers validate grid content, source readiness and output
contracts. No source downloads occur during settings resolution.
