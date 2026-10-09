# Conditional agent checks

All commands run from the owning checkout unless the command changes directory. These are
software acceptance checks, not authorization for source acquisition or a regional rebuild.

## Installed-wheel acceptance

For package/resource changes, run focused tests then `python -m pytest -q`. CI checks Python
3.11 and 3.14. Use the following existing CI recipe with a fresh writable `RUNNER_TEMP` in a local
shell (for example `RUNNER_TEMP=$(mktemp -d)`). Build/install dependencies must already be
provisioned; do not install new tooling as part of a documentation-only task.

```sh
python -m pip wheel . --no-deps --wheel-dir "$RUNNER_TEMP/dist"
wheel_env="$RUNNER_TEMP/wheel-env"
python -m venv --system-site-packages "$wheel_env"
"$wheel_env/bin/python" -m pip install \
  --force-reinstall --no-deps "$RUNNER_TEMP"/dist/*.whl
outside="$RUNNER_TEMP/wheel-smoke"
workspace="$RUNNER_TEMP/governance-workspace"
mkdir -p "$outside"
cd "$outside"
"$wheel_env/bin/python" - <<'PY'
from importlib.resources import files

import sys
class BlockApplication:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"orcacast", "domains"}:
            raise ImportError("Application imports forbidden in installed smoke")
sys.meta_path.insert(0, BlockApplication())
import governance
import governance.delivery
import governance.shared_contract
import governance.jurisdiction.tribal_first_nations_areas.build
import governance.administrative_context.coast_guard_sectors.build
import governance.protected_areas.conservation_designations.build
import governance.administrative_context.ports.build
import governance.protected_areas.critical_habitat.build
import governance.jurisdiction.county_regional_boundaries.build
import governance.protected_areas.wildlife_refuges.build
import governance.vessel_management.shipping_lanes.build
import governance.vessel_management.traffic_separation_schemes.build
import governance.preflight
import governance.releases
import governance.fisheries_management.management_areas.build
import governance.jurisdiction.federal_waters.build
import governance.jurisdiction.international_boundaries.build
import governance.jurisdiction.state_provincial_waters.build
import governance.protected_areas.marine_protected_areas.build
import governance.protected_areas.national_marine_sanctuaries.build

root = files("governance")
required = (
    "resources/config/common.yaml",
    "resources/config/data/governance/feature_catalog.yaml",
    "resources/config/data/governance/governance.yaml",
    "resources/config/data/presentation_settings.yaml",
)
assert all(root.joinpath(*path.split("/")).is_file() for path in required)
PY
"$wheel_env/bin/governance" --help
"$wheel_env/bin/governance" --workspace "$workspace" init
"$wheel_env/bin/governance" --workspace "$workspace" catalog
"$wheel_env/bin/governance" --workspace "$workspace" preflight
```

The wheel environment shares provisioned third-party dependencies as CI does; it does not prove
runtime dependency closure in a clean environment. Run outside the checkout, reject application
imports and verify the installed package's location if that boundary is uncertain. The smoke
imports the six legacy families plus preflight/release/public geometry modules and checks packaged config/catalog resources, `--help`,
fresh-workspace initialization, catalog validation and preflight. Add affected family imports for
package changes beyond this existing CI smoke scope. Keep config and packaged copies
byte-identical. Record platform, interpreter, skips and dependency limitations.

## Regional and release boundaries

Read [workflows](WORKFLOWS.md) and [production readiness](production-readiness.md) before
acquisition/build/inspection or delivery/publication. For behavior changes to those gates, run
`python -m pytest -q tests/test_config_and_catalog.py tests/test_workspace.py tests/test_releases.py`
plus relevant delivery tests in `tests/test_h3_matrix.py` (with `.[test,h3]` provisioned),
then the full suite. Preflight inventories every configured source including unused alternatives;
missing products are unavailable, not passed. The production-readiness guide owns exact
`export-delivery`, `publish-generation`, `verify-generation` and `activate-generation` recipes.
Preserve full software revision/method identity, per-resolution grain, native companion/source
bindings and metric status semantics. Publication requires all members/bytes verified, immutable
non-overwritable IDs, the exclusive publisher lock and an atomic current pointer; readers resolve
once. A crash lock requires operator inspection, never automatic deletion. Explicit rollback
selects a verified prior generation. Delivery shape does not establish shared-schema conformance.
Do not execute those data commands as routine software checks.

Read the workflow effects before acquisition/build/inspection. `init` copies defaults;
`download` is explicit, `build` uses local inputs, and `inspect` writes replaceable HTML/map
outputs. `catalog --verify-artifacts` skips missing artifacts and cannot certify a whole release.
Partial support needs `--allow-partial`; replacement needs `--overwrite`; neither relaxes source
rights, geometry/schema/provenance validation or downstream model eligibility. Per-file atomic
writes are not a multi-product transaction. Use a new workspace for rebuilds, preserve snapshot
pins and prove the resulting manifests rather than reusing historical evidence. Any release
publication requires the owning workflow's actual validation/promotion gates and user scope.

## Codebase navigation

Use scoped `rg` for known paths/literals/configuration/prose. For relationships, use an existing
`graphify-out/graph.json` only after checking relevant manifest/source coverage and freshness.
Fallback to source search for missing/stale/incomplete indexes; AST-only graphs omit prose and
may miss dynamic use. Source/tests outrank schemas/contracts, architecture and navigation caches.
Graphify is optional isolated tooling (`graphifyy==0.9.62`), not a runtime dependency.

```sh
graphify explain "build_collection"
graphify affected "build_collection" --relation calls --depth 1
```

`affected` follows callers; no-match is not proof of no use. Use syntax-aware search only when
available and needed. Build/refresh only when explicitly requested, from this checkout:
`graphify extract . --code-only --no-cluster`. Clustering/HTML are optional requested exports,
not prerequisites for navigation. Check intentional deletions before overriding shrink protection;
honor `.gitignore`/`.graphifyignore` exclusions for generated data, builds and migration archives.
Do not build at MarineCast root/grouping directories/`.github`, overwrite maintained instructions
or enable hooks implicitly. Graph/report/HTML caches remain disposable local-only files; sharing
requires an explicit owner policy covering destination, revision, freshness and review.
