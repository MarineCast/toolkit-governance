# Offline quickstart

Use Python 3.11 or newer. Install from this checkout with `python -m pip install .`; development dependencies are `python -m pip install -e '.[test,docs]'`.

## Prepare inputs

Choose an explicit workspace and run `governance --workspace /path/to/workspace init`. Initialization copies missing defaults and preserves edits. Review [configuration](configuration.md), then supply a previously validated Governance directory containing its final tables, `catalog.json` and `OriginalData`. Version 5 is self-contained. Legacy v2–v4 products also require their checksum-bound external audits at the recorded paths; retain these when replaying unchanged legacy inputs. See the [reproducibility review](reproducibility-review.md) for the historical bounded check and example maps.

Supply a nonempty Parquet grid with unique, non-null `h3_index` strings, or `H3_INDEX` strings and matching integer `H3_RESOLUTION`. The builder derives full native cell polygons; it does not use clipped cell geometry. Use explicit grid files for every desired resolution. The flat overlay rejects antimeridian-crossing cells and grids spanning more than 180 degrees.

## Build and validate

```sh
governance validate-data /path/to/retained/Governance
governance --workspace /path/to/workspace build \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --original-data /path/to/retained/Governance \
  --output-directory /path/to/new/Governance \
  --allow-partial
governance validate-data /path/to/new/Governance
```

`--original-data` names the complete flat data directory. Inputs absent from that catalog remain unavailable; no fallback network acquisition occurs. `--allow-partial` explicitly accepts qualified incomplete source support; it does not turn null into zero. An existing destination requires `--overwrite`; prefer a new review destination until the results are validated.

Successful ordinary builds remove verified disposable workspace caches and coverage files after validating the final products and originals. Temporary native/overlay and publication staging are removed by the build. No external audit files are created. Shared, unrecognized, symlinked or protected inputs prevent cache cleanup; legacy required audits are protected. Failed builds retain source caches. `--keep-workspace-data` explicitly opts into retaining source caches for diagnostics.

## Inspect without losing qualification

```python
import json
import pyarrow.parquet as pq

table = pq.read_table('/path/to/new/Governance/governance-r6-static.parquet')
contract = json.loads(table.schema.metadata[b'governance'])
print(table.select(['h3_index', 'critical_habitat_count']))
print(contract['fields']['critical_habitat_count'])
```

Read field definitions and original source bindings with the values. An unmatched cell is unknown under partial inventory support. A build timestamp cannot date a restriction or prove the source is current. See [coverage and refresh](coverage.md) before acquiring replacement evidence.
