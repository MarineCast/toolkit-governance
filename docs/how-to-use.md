# Install, build, and inspect

Start with the [single-layer getter](query-api.md); use the advanced workflows below for local products and releases.

This guide starts with a fresh workspace and builds one collection. Acquisition
is an explicit network operation; initialization, catalog inspection, and local
product reading need no download.

## 1. Install from a clone

Python 3.11+ and a compatible geospatial stack are required. From the repository:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install .
governance --help
```

For editable development and tests, use `python -m pip install -e '.[test]'`.
For the documentation preview, use `python -m pip install -e '.[docs]'`.
An installed wheel can run from any directory; a sibling repository is not required.

## 2. Initialize and review a workspace

```sh
governance --workspace ./governance-workspace init
governance --workspace ./governance-workspace catalog
governance --workspace ./governance-workspace preflight
```

`init` copies missing defaults and preserves existing edits. It downloads nothing
and creates no processed product. `catalog` validates and prints the registry,
including planned entries; it does not acquire or certify data. `preflight`
reports configured source and artifact availability without downloading.

Review these workspace files before acquisition:

| File | Review |
| --- | --- |
| `config/common.yaml` | The `full_area` WGS84 bounds |
| `config/data/governance/governance.yaml` | Source URLs/pins, source rights and coverage, raw/processed paths, and inspection settings |
| `config/data/governance/feature_catalog.yaml` | Implementation status, primary artifact locations, and feature metadata |
| `config/data/presentation_settings.yaml` | Map presentation settings |

The default extent covers the Northeast Pacific: `(-180, 32, -109, 72)`.
The current loader requires the name `full_area`. Changing the extent requires
rebuilding products and reviewing family constraints, including the sanctuary
publisher's fixed six-site roster. See [configuration](configuration.md).

## 3. Acquire one collection

The collection now configures three distinct systems: WDFW recreational marine areas,
DFO Pacific subareas and ADF&G groundfish reporting. For this WDFW-only build example,
edit `collections.management_areas.source_ids` in the workspace governance YAML to contain
only `wdfw_recreational_marine_areas`. Other source definitions can stay configured.
This selects one source with no external reconciliation-support prerequisite; it does
not merge systems or request all three inventories. The command requests network acquisition:

```sh
governance --workspace ./governance-workspace download management_areas
```

The downloader retains the selected WDFW snapshot under the configured raw path and
writes the source coverage matrix. Cached bytes are reused only after pin/receipt and
scope checks. For a small bbox query without configuring collection-wide builds, use
[get_fishery_management_areas with sources="wdfw_recreational_marine_areas"](query-api.md).
DFO and ADF&G have separate bounded adapters and rights qualifications; review
[sources and rights](reference/sources.md) before acquisition or redistribution.

Other collection IDs are listed on [layers](layers.md). The CLI has no acquisition
`--dry-run`; review the selected collection's inputs and paths before downloading.

## 4. Build from retained inputs

The configured management-area coverage is partial outside its Washington source
system. Accept that explicitly for a research/context build:

```sh
governance --workspace ./governance-workspace build management_areas --allow-partial
```

Default outputs:

```text
governance-workspace/
  data/processed/domain/governance/
    source_coverage_matrix.json
    fisheries_management/management_areas/
      management_areas.parquet
      manifest.json
```

`build` uses local inputs and does not download. `--allow-partial` acknowledges
coverage limits; it does not create absent geometry or make coverage complete.
Valid zero-match products retain schema and qualified coverage. Missing/unqualified inputs
remain failures or unavailable support; they never become observed absence.

!!! note "Replacement and multi-file publication"
    Existing product replacement requires `--overwrite`. Native artifact/manifest pairs
    stage and roll back handled failures under a writer lock; readers verify exact hashes.
    Two renames are not crash-atomic, and multi-product family builds have no global rollback.
    After a failed build, verify the primary and related files before use. A new
    workspace is useful when comparing a changed source/configuration with a
    retained build. See [workflows](WORKFLOWS.md).

## 5. Verify and read the native product

```sh
governance --workspace ./governance-workspace catalog --verify-artifacts
```

This verifies **present configured primary artifacts**. Missing artifacts are
skipped; this command is not a complete-release acceptance gate. Check that the
intended collection was built, and inspect its manifest and related files.

From the same directory used for the example workspace:

```python
from pathlib import Path
import geopandas as gpd
from governance.shared.artifacts import load_manifest
from governance.shared.schema import validate_governance_geometry

root = Path("governance-workspace").resolve()
product = root / "data/processed/domain/governance/fisheries_management/management_areas"
manifest = load_manifest(product / "manifest.json", verify_artifact=True)
frame = gpd.read_parquet(manifest["artifact"]["path"])
validate_governance_geometry(frame)

print(manifest["source_completeness"])
print(manifest["known_limitations"])
print(frame[["GOVERNANCE_FEATURE_ID", "GEOMETRY_PART_ID", "FEATURE_NAME",
             "SOURCE_COVERAGE_STATUS", "MODEL_ELIGIBLE"]].head())
```

`load_manifest` checks manifest version, model policy, H3 policy, and the primary
artifact SHA-256. The schema validator checks native CRS, identity, geometry, and
required fields. Neither establishes current legal applicability or complete
source coverage. For a family with `related_artifacts`, verify those listed
checksums separately; the primary loader does not automatically verify them.

## 6. Render the inspection map

Choose an explicit date. This example renders an inspection view for October 13,
2026:

```sh
governance --workspace ./governance-workspace inspect --as-of 2026-10-13
```

Open `governance-workspace/outputs/domains/governance/governance_layers.html`.
The adjoining `governance_layers_map_manifest.json` records the inspection.
Enable the fisheries management layer in the layer control; that family is hidden
by default. Other collections are unavailable until their products are built,
and planned catalog families are reported separately.

The map uses simplified display geometry while retaining canonical products.
Viewing it needs network access for basemap/browser assets. Inspection replaces
its configured HTML and map manifest. The effective-date filter includes both
endpoints and keeps unknown dates visible; it is an inspection aid, not a legal
as-of reconstruction.

## 7. Build additional collections

Use the same explicit stages for each selected family:

```sh
governance --workspace ./governance-workspace download federal_waters
governance --workspace ./governance-workspace build federal_waters --allow-partial
```

Read the [collection-specific inputs and outputs](layers.md) before running a
different family. International-boundary reconciliation needs separately
provisioned local DFO/seascape support. MPA and sanctuary publishers also validate
their required subsets or roster, so `--allow-partial` cannot bypass those checks.

## Optional: export an explicit H3 overlay

Install the optional dependency from the clone:

```sh
python -m pip install '.[h3]'
```

After **all configured native collection products and manifests** (currently fifteen) are present and
verified, supply your own bounded grid with unique valid `H3_INDEX` and
`H3_RESOLUTION` pairs:

```sh
governance --workspace ./governance-workspace export-h3-matrix \
  --grid /absolute/path/to/h3-grid.parquet \
  --length-crs EPSG:32610 \
  --allow-partial \
  --output ./governance-workspace/outputs/governance-h3-metrics.parquet
```

EPSG:32610 is an example for an appropriate regional grid; choose a metre-based
projected CRS suitable for your actual cells. This is a separate snapshot context
overlay with nulls for unsupported intersections and `MODEL_ELIGIBLE=false`.
Read the [overlay contract](h3-matrix.md) for grid, time, provenance, and metric
semantics.

## Frozen studies, delivery, and local generations

The [frozen-study guide](study-guide.md) documents read-only `study-preflight`,
cache-only `run-study`, semantic validation, and interrupted-stage recovery.
Studies require supplied grids, a checksum-bound water mask, provisioned source
support, an approved shared schema, and explicit release identity. They retain
static inventories and separate fishing-area relations rather than inventing
daily legal history or catch/effort quantities.

[Delivery and publication](cli.md) describes per-resolution exports and immutable
local generations. Prepared delivery, verification, publication, and activation
are distinct actions. These data workflows are separate from documentation
publication through GitHub Pages.

## Python workspace selection

Direct Python/module use selects the workspace through `GOVERNANCE_WORKSPACE`:

```python
import os
from pathlib import Path
from governance import initialize_workspace, load_governance_config

workspace = Path("governance-workspace").resolve()
initialize_workspace(workspace)
os.environ["GOVERNANCE_WORKSPACE"] = str(workspace)
config = load_governance_config()
print(config.collections["management_areas"].artifact_path)
```

Initialization and config loading are separate from download/build calls.
See [CLI reference](reference/cli.md) and [troubleshooting](troubleshooting.md)
for command options and common failures.
