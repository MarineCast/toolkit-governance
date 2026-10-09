# Frozen study rebuild and validation

The study workflow is introduced by [PR7](https://github.com/MarineCast/toolkit-governance/pull/7),
inspected at `fe1dcc0e9e244b111a0b80d33acd0ab6fe9feaaf`. Use a reviewed revision
containing that PR before running the commands below. They are unavailable on the
main baseline documented in the [CLI reference](cli.md). The documentation alone does not supply study code or authorize new acquisitions.

The [current checkpoint](production-readiness.md#current-frozen-study-checkpoint-2026-10-09)
is a cache-only, local research release. Frozen membership does not establish
complete source coverage. A study window is retained as requested context without
daily replication or inferred legal history. The water mask selects reporting
support; governance measurements still intersect full H3 cells.

## Required inputs

- Reviewed schema-version-1 study JSON, UTC time scope and supported reporting policy.
- Explicit Parquet grids with `H3_INDEX` and `H3_RESOLUTION`: one distinct resolution
  per file, including R6. An R8 companion is supplied independently, not rolled up.
- Nonempty, valid EPSG:4326 water-mask geometry, named layer and checksum-bound mask provenance.
- Provisioned cache workspace containing effective config, raw inputs and required
  reconciliation support; cached query envelopes can under-cover an expanded study.
- Caller-supplied approved shared schema admitting `reference_geometry`, with pinned reference.
- New preparation directory, distinct intended permanent generation path, release
  ID, full software Git SHA and suitable metre-based length CRS.

The study configuration and mask are externally provisioned; the CLI does not
create a study definition, discover grids or silently download source support.
Install `.[h3,contract]` from the reviewed checkout. Replace every example path and
placeholder below with the actual retained input and intended release identity.

```sh
governance study-preflight \
  --study /path/to/study.v1.json \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --mask /path/to/land-water.gpkg --mask-layer WATER_LAYER \
  --mask-manifest /path/to/mask-source-manifest.json \
  --cache-workspace /path/to/cache-workspace

governance run-study \
  --study /path/to/study.v1.json \
  --grid /path/to/grid-r6.parquet --grid /path/to/grid-r8.parquet \
  --mask /path/to/land-water.gpkg --mask-layer WATER_LAYER \
  --mask-manifest /path/to/mask-source-manifest.json \
  --cache-workspace /path/to/cache-workspace \
  --output /path/to/new-preparation \
  --permanent-release-path /path/to/releases/research-v1 \
  --release-id research-v1 --software-revision FULL_40_CHARACTER_GIT_SHA \
  --schema /path/to/approved-schema.json --schema-reference PINNED_SCHEMA_REFERENCE \
  --length-crs EPSG:32610 --staging-cap-bytes 2700000000

governance validate-study-release /path/to/new-preparation
```

`study-preflight` reads bindings and scope without downloading. `run-study` uses
one worker, copies cached config/raw support, rebuilds native products, creates
matrix/delivery/shared companions and records validation. It estimates staging
space and refuses a cap/free-space violation. EPSG:32610 is appropriate only for
the qualified zone-10 study; select and validate a suitable CRS for other domains.
Preparation does not activate a release. Use the explicit publisher in the
[CLI reference](cli.md), then verify the permanent path and resolve current once.

## Acceptance and recovery

Study validation checks retained input checksums, effective configuration, native
schema/geometry and companions, raw-source bindings, exact grid order/membership,
matrix/delivery values, static temporal interpretation, shared-schema validation,
all positive-area mask intersections and sampled independent overlay calculations.
The independent calculation still shares GEOS/projection libraries and is not legal
certification. PR7 repeats semantic validation before a study-contract generation
can be activated or selected for rollback; baseline byte verification alone is insufficient.

After an interrupted overlay, `run-study` with the same arguments plus
`--resume-native` can reuse complete verified native staging. It checks input and
retained-file bindings and refuses an assembled `delivery/` or `study-contract.json`.
Do not delete those markers to force a resume. Preserve the failed candidate for
inspection and use a new output path if assembly has begun. See
[troubleshooting](troubleshooting.md) for lock and pointer recovery.
