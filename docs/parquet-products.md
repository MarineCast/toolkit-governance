# Governance Parquet outputs

Version 0.3 produces a flat data directory. Each supplied H3 resolution has at most
one static and one dynamic metric Parquet. There are no data releases, current
pointers, generation directories, public manifests, crosswalks or duplicated study bundles.

```text
Data/Governance/
  governance-r6-static.parquet
  governance-r8-static.parquet
  catalog.json
  OriginalData/
    wdfw_recreational_marine_areas/geometry.parquet
    noaa_critical_habitat_polygon/geometry.parquet
    ...
```

The current inventories are static. No dynamic file is created from retrieval or
build timestamps. A future dynamic table must have a non-null, typed `date` column,
a documented source-backed temporal meaning, and unique `(h3_index, date)` rows.
It uses `governance-r<resolution>-dynamic.parquet`. Source establishment years,
legal effective dates, geometry validity and retrieval times remain distinct.

## Read the data

```python
import json
from pathlib import Path
import pyarrow.parquet as pq

root = Path('Data/Governance')
catalog = json.loads((root / 'catalog.json').read_text())
table = pq.read_table(root / catalog['tables']['6']['static']['path'])
context = json.loads(table.schema.metadata[b'governance'])
```

Static tables contain `h3_index` and metric columns with corresponding `_status`
columns. One row represents one supplied full H3 cell; the resolution is declared
in the filename, catalog and Parquet metadata. R6 and R8 are independent grids.
The producer preserves supplied cells and order, without cross-resolution averaging.
A metric value of zero, a null value and partial support are different states.

The embedded `governance` JSON contains field definitions, units, source citations,
source vintage and receipts, coverage, normalization methods, CRS, geometry support,
original dataset bindings and `model_eligible=false`. It has no release identity.
`catalog.json` contains file paths, checksums, row counts, a last-update timestamp
for every collection/domain area, and original-dataset references. Last update means
processing time, not source observation time or current legal applicability.

Count metrics retain distinct source-backed feature identities. Polygon fractions
use unioned intersection area divided by the full cell area in EPSG:6933. Line
metrics use unioned length in the explicitly supplied metre-based projected CRS.
Point metrics count source-backed point features. Overlapping source/role groups
remain separate and must not be added as unique jurisdiction or route totals.
Empty intersections under incomplete support remain null. Research-only geometry
is not a compliance, exhaustive jurisdiction, or ecological occurrence product.

## Original shapes

Each source dataset has one GeoParquet under `OriginalData/<source-id>/geometry.parquet`.
These are original retrieved feature extents before toolkit clipping, including
original attributes, IDs and date fields. Shared inputs are stored once, even when
used by several collections. Polygon, line and point sources retain their geometry
types. CRS is converted to EPSG:4326 without simplifying or clipping the geometry.
A bounded source query still selects only its received features; retained extents
do not imply an exhaustive global inventory.

The GeoParquet metadata key `governance_original` retains acquisition scope, exact
selected-ID receipts, per-record receipt times, source metadata and original input
checksums. Provider licensing, attribution and redistribution limits remain source-specific.
No ZIP archives or JSON page snapshots are duplicated in the public directory.
Acquisition caches belong in the explicit source workspace, separately from public outputs.
A verified OriginalData directory is itself sufficient for an offline rebuild.

## Build and update

```sh
python -m pip install .
governance --workspace /path/to/source-workspace init
# Review config and explicitly acquire the needed collections or provision local inputs.
governance --workspace /path/to/source-workspace download management_areas
# Builds never download implicitly.
governance --workspace /path/to/source-workspace build \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --output-directory /path/to/Data/Governance --allow-partial
governance validate-data /path/to/Data/Governance
```

`--grid` accepts explicit `H3_INDEX`/`H3_RESOLUTION` grid Parquets, or the static
metric Parquets themselves. No separate public grid files are needed for updates.
Only supplied cells are overlaid; the current overlay rejects antimeridian-crossing
cells. The default line CRS is EPSG:32610; choose a suitable metre-based projected
CRS explicitly for another grid. Native clipping must cover all supplied cells.

To rebuild from retained originals using exactly the current grid:

```sh
governance --workspace /path/to/source-workspace build \
  --grid /path/to/Data/Governance/governance-r6-static.parquet \
  --grid /path/to/Data/Governance/governance-r8-static.parquet \
  --original-data /path/to/Data/Governance \
  --output-directory /path/to/Data/Governance --allow-partial --overwrite
```

Configuration supplies provider identity, versions, selectors, source systems and
normalization profiles. OriginalData is checked against that configuration and its
catalog hashes; changed source versions or selectors require newly qualified inputs.
`--allow-partial` acknowledges partial research coverage without changing its meaning.
`--overwrite` replaces an existing verified flat directory. Builds stage native
geometry, reconciliation and a metrics-only overlay in temporary storage, then
validate the flat output before replacement. Intermediates are removed on exit.
There is a single-writer lock; handled installation errors restore the prior directory.
Readers must check catalog hashes and retry if an update overlaps their read. This
is local replacement, not a filesystem-wide snapshot guarantee during a crash.

## Validation and compatibility

`validate-data` checks exact flat file membership, checksums, original dataset
identity, H3 identity/resolution, unique row keys, units, finite/range checks, and
metric/status associations. Software checks do not establish legal currency or
exhaustive regional coverage.

`export-data --matrix FILE --output-directory DIR` projects an existing verified
internal overlay using the same calculation. It writes the same flat layout and
also reads the qualified original inputs from the selected workspace. Historical
study/generation Python helpers remain for old-artifact regression checks; their
commands and release workflow are retired from the public CLI. Old outputs must
be migrated and checked before deleting them. Source acquisition and public
source-data redistribution remain separate operations.

## Regional migration checked on 2026-10-14

The retained Northeast Pacific study grids contain 2,621 R6 cells and 88,243 R8
cells. Each static table has 94 metric columns and their 94 support-status columns,
plus `h3_index`. A full offline rebuild from the 40 OriginalData datasets matched
every existing validated metric value/status and every original attribute/geometry
byte. The flat dataset uses about 428 MB, replacing roughly 3.8 GB of repeated
builds and releases. The catalog is approximately 11.7 KB.

Validation here covers layout, exact delivery equivalence and offline reproducibility.
It does not refresh agency observations, certify current law or close partial
geographic coverage. Historical source-vintage and unknown retrieval evidence remain
preserved. No dated inventory history was generated.
