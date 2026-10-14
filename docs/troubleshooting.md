> Version 0.3 public output uses the [flat Parquet workflow](parquet-products.md).
> Native artifacts and release/study commands below describe historical or internal workflows;
> they are not the current public data layout.

# Troubleshooting

| Symptom | Likely cause | Next step |
| --- | --- | --- |
| `governance: command not found` | Installation environment is not active | Activate the environment used for `pip install`, or use its `python -m governance` |
| Configuration file missing | Workspace not initialized, or selected from another cwd | Run `init` with the intended absolute `--workspace`; check [path rules](configuration.md#path-rules) |
| Build rejects partial/unavailable full-area coverage | Configured coverage is incomplete or source files are absent | Review source records; acquire/provision intended inputs, then use `--allow-partial` only for an explicitly qualified context build |
| No supported in-extent geometry | No readable supported input intersects the processing extent | Check input paths, source query, geometry, and `full_area`; do not replace absence of support with an empty certified product |
| Existing output rejected | Replacement was not requested | Preserve the previous build, use a fresh workspace, or supply `--overwrite` for the intended stage |
| Archive checksum mismatch | Download bytes do not match the pinned archive | Inspect provider/version and snapshot integrity; do not silently replace the pin to accept unexplained bytes |
| International reconciliation cannot find support | Local DFO/seascape inputs or shapefile sidecars are missing | Provision the explicit [external local inputs](WORKFLOWS.md#external-local-inputs); partial acceptance does not remove every prerequisite |
| MPA subset or sanctuary roster validation fails | Required designation/interest subsets or configured sanctuary roster did not survive acquisition/clipping | Inspect the source set and extent; `--allow-partial` does not bypass family validation |
| Catalog passes but a layer is unavailable | Missing products are skipped by catalog verification | Check the intended artifact and manifest; build that collection and read its qualification |
| Layer is available but not visible | Family is hidden by default or date filtering removed known dated records | Enable it in the map control; inspect effective dates and map manifest |
| Map basemap/assets do not load | Viewer network access is unavailable | Restore access for basemap/browser assets; canonical GeoParquet remains separately readable |
| H3 export fails with missing/corrupt native input | All configured collection products/manifests or raw source verification are not satisfied | Verify each native input and its manifest; do not substitute empty collection data |
| H3 grid or CRS rejected | Invalid/duplicate cells, an antimeridian-crossing grid, or a non-metre length CRS | Follow the [overlay input contract](h3-matrix.md) and choose a regional projected CRS |

After a failed multi-file build, inspect both primary and secondary products.
The pipeline has no global transaction rollback. Retain source/configuration
identity and verify the intended file set before using it.

For a reproducible issue, include the command, Python/platform versions,
configuration identity, relevant source/manifest status, and exception. Keep
credentials and restricted source data out of public reports.

## Study and local publication recovery

| Symptom | Check and recovery |
| --- | --- |
| Missing config or unexpected workspace | Run `init` in the intended writable workspace. Place `--workspace` before the command; review environment/cwd precedence and use absolute artifact paths. Initialization preserves existing edits. |
| Unsupported area or config composition error | Retain the named `full_area`; inspect includes/references and common-config paths. Resolve cycles and missing values explicitly; unknown keys are not comprehensively rejected. |
| Geospatial import or H3/schema dependency error | Activate the intended Python 3.11+ environment, run `python -m pip check`, and install `.[h3,contract]` for overlays/shared validation. Confirm platform-compatible geospatial wheels. |
| Source unavailable or partial build rejected | Inspect `preflight`, family source notes, snapshot pins and required support inputs. Provision qualified inputs explicitly or acknowledge partial research support with `--allow-partial`; never fill missing coverage with zero. |
| Existing snapshot/product/delivery/generation | Preserve the existing result. Use a new experiment path; `--overwrite` is explicit only where supported. Immutable generation IDs cannot be replaced. |
| Artifact, raw-source or grid checksum mismatch | Stop consumption/activation. Compare against the retained source/config/grid binding and rebuild into a new workspace using qualified inputs. Do not rewrite manifests to bless mismatching bytes. |
| Missing reconciliation support | Provision the documented shapefile sidecars and seascape support with upstream provenance at configured paths. `--allow-partial` does not remove all required support dependencies. |
| Empty/NULL metric or unexpected unavailable family | Check completeness, role and geometry type. NULL under partial/unknown support is not observed absence; catalog entries do not imply implemented legal products. |
| Inspection map looks stale or incomplete | Confirm chosen config, `--as-of` and output path. Unknown dates pass the inspection filter; simplification and basemap network failures do not change native authority. |
| Interrupted study preparation | Resume only unassembled, complete native staging with identical inputs and `--resume-native`; otherwise preserve it and select a new output directory. |
| `.publish.lock` exists | Confirm the owning PID/workload and filesystem state. Never remove an active lock. After a crash, an operator must inspect and deliberately clear only a proven stale lock before retrying. |
| `.staging-*` or an unreferenced generation remains | Preserve prior `current.json` and candidate evidence. Verify exact membership/hashes; for study bundles run semantic validation too. A completed valid candidate can be explicitly activated; incomplete staging is not a generation. No automatic cleanup is promised. |
| Semantic study validation fails | Keep the current pointer unchanged. Check retained masks/config/source/native/table/schema bindings and independent checks. A checksum pass does not override a scientific failure. Rebuild a new candidate after fixing qualified inputs/code. |
| Pages build passes but site returns 404 | A preview is not publication. Merge the reviewed docs PR, dispatch the workflow on main and inspect the deploy URL plus HTTP/readback. See [publication](documentation-site.md). |
