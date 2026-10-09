# Troubleshooting

Read the error with the installed revision's `governance COMMAND --help` and
preserve existing data before choosing a recovery action. Failures do not establish
absence of governance features or a legal interpretation.

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
| Interrupted study preparation | Requires PR7. Resume only unassembled, complete native staging with identical inputs and `--resume-native`; otherwise preserve it and select a new output directory. |
| `.publish.lock` exists | Confirm the owning PID/workload and filesystem state. Never remove an active lock. After a crash, an operator must inspect and deliberately clear only a proven stale lock before retrying. |
| `.staging-*` or an unreferenced generation remains | Preserve prior `current.json` and candidate evidence. Verify exact membership/hashes; for study bundles run semantic validation too. A completed valid candidate can be explicitly activated; incomplete staging is not a generation. No automatic cleanup is promised. |
| Semantic study validation fails | Requires PR7. Keep the current pointer unchanged. Check retained masks/config/source/native/table/schema bindings and independent checks. A checksum pass does not override a scientific failure. Rebuild a new candidate after fixing qualified inputs/code. |
| Pages build passes but site returns 404 | A preview is not publication. Merge the reviewed docs PR, dispatch the workflow on main and inspect the deploy URL plus HTTP/readback. See [publication](documentation-site.md). |

For an incident record retain command/revision, workspace/config hashes, input IDs,
error output and validation reports locally. Redact credentials and private paths
before sharing. Keep unpublished datasets, maps and source receipts out of public
issues and documentation. Release verification reads files; it does not authorize
source redistribution or source re-acquisition.
