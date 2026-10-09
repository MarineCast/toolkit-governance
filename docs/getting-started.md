# Install and configure

Install from a reviewed checkout using Python 3.11+ and an isolated environment.
The package requires a compatible GeoPandas/Shapely/PROJ/Arrow stack; use binary
wheels supported by your interpreter and platform. Offline CI is separate from
regional science acceptance.

```sh
git clone https://github.com/MarineCast/toolkit-governance.git
cd toolkit-governance
python -m venv .venv
. .venv/bin/activate
python -m pip install '.[h3,contract]'
python -m pip check
governance --help
```

A regular install includes optional H3 and shared-schema validation in this example.
Use `python -m pip install .` for the native workflows alone. For development use
`python -m pip install -e '.[test]'`; `test` includes the optional H3/schema test dependencies.
`python -m governance` exposes the same CLI. Run commands from this activated environment.

## Workspace and configuration

Choose a data workspace outside the package installation. The following path is
an example to replace with your own writable destination:

```sh
governance --workspace /path/to/workspace init
governance --workspace /path/to/workspace catalog
governance --workspace /path/to/workspace preflight
```

`init` copies missing packaged YAML/catalog files and preserves existing files.
It does not download or upgrade an existing workspace's edited configuration.
Workspace precedence is `--workspace`, `GOVERNANCE_WORKSPACE`, then current directory.
Set `GOVERNANCE_WORKSPACE` explicitly for Python API or family module entry points.

| Configuration | Review before execution |
| --- | --- |
| `config/common.yaml` | Named `full_area`, default bbox [-180, 32, -109, 72] EPSG:4326 |
| `config/data/governance/governance.yaml` | Sources, snapshot pins, rights, coverage, collections, native output and inspection paths |
| `config/data/governance/feature_catalog.yaml` | 24 collection entries and their implementation status |
| `config/data/presentation_settings.yaml` | Map presentation defaults; simplification does not alter canonical geometry |

The loader currently requires `full_area`. Do not change the area name to invent
an unsupported regional workflow. Configured relative paths resolve against the
workspace even when `--config` is absolute. CLI artifact paths such as `--grid`,
`--matrix`, `--source`, `--output-directory` and inspection `--output` resolve from
the process working directory; use absolute paths to avoid ambiguity.

YAML composition supports includes, mapping merges, list replacement, references
and environment values; hashes redact sensitive configuration. The loader is not
a strict unknown-key schema. Follow existing configuration structure, review the
resolved paths and source pins, and keep private values out of commits.
`preflight` inventories all configured sources, including unused alternatives;
a missing artifact is unavailable, not a passing completeness check.

## First native rebuild

Review [source qualification](sources.md) and [workflow effects](WORKFLOWS.md).
Acquisition is an explicit network operation; run it only with an approved source
scope. For a provisioned workspace, skip the download and build from its cached inputs.

```sh
governance --workspace /path/to/workspace download marine_protected_areas
governance --workspace /path/to/workspace build marine_protected_areas --allow-partial
governance --workspace /path/to/workspace catalog --verify-artifacts
governance --workspace /path/to/workspace inspect --as-of 2026-10-09
```

These are operational examples, not proof that inputs are present. `--allow-partial`
acknowledges incomplete research support; it does not certify coverage or legal
applicability. Existing snapshots/products require explicit `--overwrite` to replace.
`inspect` replaces configured HTML/map-manifest outputs; its date filter permits
unknown dates and is not a legal applicability test. Open the printed HTML locally;
basemap tiles may require network access. Continue with [H3 overlays](h3-matrix.md),
[local releases](WORKFLOWS.md#coherent-local-releases) and [troubleshooting](troubleshooting.md).
