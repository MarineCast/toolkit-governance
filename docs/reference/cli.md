# CLI reference

The installed command is `governance`; `python -m governance` is equivalent.
Place global `--workspace` before the subcommand.

```sh
governance --help
governance build --help
governance export-h3-matrix --help
```

## Commands and effects

| Command | Required arguments | Options | Effects |
| --- | --- | --- | --- |
| `init` | None | Global `--workspace` | Copies missing config/catalog defaults; no acquisition |
| `preflight` | None | Global `--workspace`; no `--config` | Reads configured source/artifact readiness; no acquisition |
| `catalog` | None | `--config`, `--verify-artifacts` | Validates/prints catalog; optionally verifies present primary artifacts |
| `download` | Collection ID | `--config`, `--overwrite` | Acquires configured source snapshots and writes coverage matrix |
| `build` | Collection ID | `--config`, `--allow-partial`, `--overwrite` | Publishes native products/manifests and coverage matrix from local inputs |
| `inspect` | `--as-of YYYY-MM-DD` | `--config`, `--output` | Replaces consolidated inspection HTML and map manifest |
| `export-h3-matrix` | `--grid`, `--output`, `--length-crs` | `--config`, `--allow-partial`, `--overwrite` | Writes a separate overlay from all configured verified native collections |

`--config` defaults to `config/data/governance/governance.yaml`. `--overwrite`
permits replacing outputs or snapshots for the selected stage; it is not a global
workspace reset. Download/build do not accept date-range or dry-run options.

## Implemented collection IDs

```text
marine_protected_areas
national_marine_sanctuaries
international_boundaries
federal_waters
state_provincial_waters
management_areas
critical_habitat
wildlife_refuges
conservation_designations
county_regional_boundaries
tribal_first_nations_areas
shipping_lanes
traffic_separation_schemes
ports
coast_guard_sectors
```

Use these IDs with `download` and `build`. Planned catalog entries have no
implemented stage modules. The CLI does not provide an `all` collection shortcut.

## Common examples

```sh
governance --workspace ./governance-workspace init
governance --workspace ./governance-workspace catalog
governance --workspace ./governance-workspace download management_areas
governance --workspace ./governance-workspace build management_areas --allow-partial
governance --workspace ./governance-workspace catalog --verify-artifacts
governance --workspace ./governance-workspace inspect --as-of 2026-10-13
```

These are distinct operations. `--allow-partial` accepts coverage limitations but
does not bypass required source subsets, roster checks, or local reconciliation
inputs. Catalog verification skips missing artifacts and does not automatically
verify every secondary product.

## Direct family modules

For direct module use, set the workspace first:

```sh
export GOVERNANCE_WORKSPACE=/absolute/path/to/governance-workspace
python -m governance.fisheries_management.management_areas.download --help
python -m governance.fisheries_management.management_areas.build --help
```

The family modules retain their collection-specific default configuration paths.
Use the top-level CLI for a consistent workspace interface. See
[configuration](../configuration.md) for path resolution and
[how to use](../how-to-use.md) for a complete single-collection workflow.

## Studies and local release commands

The CLI also provides `study-preflight`, `run-study`, `validate-study-release`,
`export-delivery`, `export-shared-manifest`, `publish-generation`,
`verify-generation`, and `activate-generation`. See the [frozen-study guide](../study-guide.md)
for study flags and [delivery/publication reference](../cli.md) for exact release
inputs and command effects. `run-study` is cache-only; publication and activation
remain explicit operations. None of these commands publishes this documentation
site or establishes dataset redistribution permission.
