# Workflows and operational boundaries

Run commands from the owning checkout after installation, or use an installed CLI with an explicit
workspace. Never use the original application as a runtime root.

1. Run `governance --workspace /path/to/workspace init`. It copies missing YAML defaults/catalog
   and preserves edits. Review extent, source pins, rights and all configured input/output paths.
2. Request `download <collection>` explicitly. Archive/ArcGIS acquisition writes configured raw
   snapshots and metadata; downloads are not part of `build` or `init`. Existing snapshots are
   reused unless `--overwrite` is supplied. Pinned archives verify SHA-256.
3. Build one collection from local inputs. The default rejects incomplete full-area support;
   `--allow-partial` permits explicit research/context products. Each family normalizes, clips,
   validates and writes its products/manifests. `--overwrite` allows replacement. Inspect family
   code before execution because secondary publication can write several files after the primary.
4. Use `catalog` for metadata validation and `catalog --verify-artifacts` to check present primary
   artifacts. Missing artifacts are skipped by the inherited catalog validator. This is not a
   whole-release acceptance gate.
5. Render `inspect --as-of YYYY-MM-DD` into the configured output directory. It writes HTML and
   a map manifest, replacing these inspection outputs. It does not promote a scientific release.
   Basemap assets require a browser/network when viewing the HTML.

All stage commands accept `--config`; collection-specific defaults also remain available through
`python -m governance.<category>.<collection>.build` and `.download`. Set `GOVERNANCE_WORKSPACE`
for direct Python/module usage. A CLI `--output` path is interpreted relative to the process cwd;
configured output paths resolve relative to the workspace.

## External local inputs

The inherited international-boundary reconciliation can use these separately provisioned inputs:

- NOAA U.S. maritime limits shapefile at the configured `data/raw/gis/marine/...` path (or its
  configured snapshot where the source reader supports it).
- DFO Federal Marine Bioregions shapefile, with its complete shapefile sidecars.
- A seascape territorial-water support GeoParquet, with upstream provenance and source rights.

These are inputs, not Python imports. Supply them in the workspace or set explicit paths. The
extraction moved governance-owned files only; it did not move shared seascape inputs or require
an application/sibling checkout. Historical OrcaCast labels on a derived support source describe
its original provenance, not a runtime dependency. Do not relabel historical source attribution.
Reconciliation may still require these inputs even with `--allow-partial`.

## Development checks

```sh
python -m pip install -e '.[test]'
python -m pytest -q
python -m pip wheel --no-deps --wheel-dir dist .
git diff --check
```

Verify a regular wheel installation from outside the checkout, initialize a fresh external
workspace, validate its catalog and import all eight families without application imports. Keep
`config/` and `src/governance/resources/config/` byte-identical. Regenerate the editable catalog
with `python -m governance.maintenance.catalog`, then synchronize its packaged resource.

Moved local historical products retain their original bytes, manifests and absolute provenance
paths. They are evidence of the prior build, not freshly validated toolkit releases. Use a new
workspace for rebuilds; do not reuse an old manifest as proof that new configuration was run.
See [migration](MIGRATION.md) for the local transfer/cleanup boundary and unrun checks.

## Coherent local releases

Use the separate [production release workflow](production-readiness.md) to stage all native
products, companions and evidence before an atomic generation-pointer switch. Per-family build
commands still write per-file and must not target an already published generation.
