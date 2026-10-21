# Offline quickstart

Use Python 3.11 or newer. Install from this checkout with `python -m pip install .`; development dependencies are `python -m pip install -e '.[test,docs]'`.

## Prepare inputs

Choose an explicit workspace and run `governance --workspace /path/to/workspace init`. Initialization copies missing defaults and preserves edits. Review [configuration](configuration.md), then supply a previously validated Governance directory containing `catalog.json` and `OriginalData`. A directory containing only copied geometry files is insufficient.

Supply a nonempty Parquet grid with unique, non-null `h3_index` strings, or `H3_INDEX` strings and matching integer `H3_RESOLUTION`. The builder derives full native cell polygons; it does not use clipped cell geometry. Use explicit grid files for every desired resolution. The flat overlay rejects antimeridian-crossing cells and grids spanning more than 180 degrees.

## Build and validate

```sh
governance validate-data /path/to/retained/Governance
governance --workspace /path/to/workspace build \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --original-data /path/to/retained/Governance \
  --output-directory /path/to/new/Governance \
  --allow-partial --keep-workspace-data
governance validate-data /path/to/new/Governance
```

`--original-data` names the complete flat data directory. Inputs absent from that catalog remain unavailable; no fallback network acquisition occurs. `--allow-partial` explicitly accepts qualified incomplete source support; it does not turn null into zero. An existing destination requires `--overwrite`; prefer a new review destination until the results are validated.

`--keep-workspace-data` retains source caches. Without it, a successful build attempts to remove disposable source-workspace data only after verifying retained outputs/originals; shared, unrecognized, symlinked or protected inputs prevent cleanup. Failed builds retain source caches. Temporary native/overlay intermediates are removed by the build.

## Inspect without losing qualification

```python
import json
import pyarrow.parquet as pq

table = pq.read_table('/path/to/new/Governance/governance-r6-static.parquet')
contract = json.loads(table.schema.metadata[b'governance'])
print(table.select(['h3_index', 'critical_habitat__recorded_feature_count']))
print(contract['fields']['critical_habitat__recorded_feature_count'])
```

Read field definitions and original source bindings with the values. An unmatched cell is unknown under partial inventory support. A build timestamp cannot date a restriction or prove the source is current. See [coverage and refresh](coverage.md) before acquiring replacement evidence.
