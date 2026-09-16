# Extraction and validation record

Extraction completed locally on 2026-09-16 from the OrcaCast working tree, preserving unrelated
changes from concurrent toolkit extractions. This is a source/workspace migration, not a Git
history rewrite, remote publication or newly validated scientific release.

## Transfer and implementation

- Relocated 56 governance Python modules, six per-family source notes, the roadmap/catalog,
  seven governance configuration files, five test modules and the catalog generator.
- Preserved 51 governance-owned local data/report files (298,381,776 bytes) at equivalent ignored
  paths. SHA-256 verification preceded source removal. These are historical snapshots/products,
  not bundled package assets or a new regional build.
- Replaced `orcacast.domains.governance` imports with `governance`; replaced the three configuration
  dependencies with private local configuration support. Retained the original software license.
- Added package metadata, installed configuration resources, a workspace initializer, a CLI and
  six extraction-focused tests. `GOVERNANCE_WORKSPACE`/CLI workspace selection replaces the old
  source-tree root discovery. No writes target an installed package directory.
- Replaced catalog discovery through empty source folders with an explicit registry that survives
  wheel installation; forwarded custom inspector configuration to catalog validation. Scientific
  normalization, geometry algorithms, source pins and model-ineligible semantics are retained.
- AST comparison verified 52 of the 56 relocated modules are identical after namespace changes.
  The four other modules contain only the new public exports, selected-config forwarding, catalog
  registry lookup and acquisition user-agent changes.
- Retained the source attribution on legacy seascape support. Those inputs must be explicitly
  provisioned in the selected workspace and are not application runtime imports.

The ignored `migration-local/transfer.json` records source-to-destination file hashes. Exact
originals of removed/edited files and prepared cleanup records are retained in
`migration-local/original-orcacast/` and `migration-local/cleanup/`. These contain local evidence
and are intentionally not committed, published or packaged. Retain them until migration acceptance.

## OrcaCast cleanup boundary

Removed the governance source/config/test trees, generator, raw/processed/output trees, stale
build copies and dedicated bytecode. Updated shared configuration guidance, source inventories,
human-domain boundary prose and notebook policy wording. No application wrapper or dependency
on the new toolkit was introduced.

Mixed historical inventories/release evidence were backed up before removing obsolete code
entries. Retained JSON projections explicitly state that they are historical, not fresh validation.
The generated atlas retains its unrelated sections but omits the extracted domain. Generic
policy/stewardship wording was retained in meaning without the old domain name. Git history is
unchanged; original tracked blobs remain recoverable there.

## Observed validation

Final active-checkout source/text and all-filename scans found no case-insensitive `governance`
matches in OrcaCast. An additional hidden/ignored metadata scan (Python, Markdown, text, JSON,
YAML, TOML, CSV, HTML and notebooks up to 32 MB each) also returned zero matches. Git history,
binary dataset contents and larger ignored text payloads were not rewritten or exhaustively
searched. Every file in the 146-record transfer ledger is absent at its old path; all 51 transferred
local artifact hashes still match. The root has no governance source/config/test/data/output or
build-cache directory. Documentation links, workspace YAML routing and per-checkout whitespace
checks passed. Remote repository availability was not checked.


- Original OrcaCast governance suite before extraction: **13 passed**.
- Standalone toolkit suite after extraction and source removal: **19 passed** with application
  imports blocked, including configuration composition,
  workspace routing, initialization idempotence, resource parity and absence of application imports.
- Regular wheel built and installed in a separate environment. Outside both source checkouts,
  initialization, catalog validation and all 18 collection-stage imports passed with application
  imports explicitly blocked. The installed inspector also rendered an empty-workspace map and
  manifest without claiming source availability. The validation environment reused installed third-party geospatial
  dependencies; a fresh online dependency solve was not performed.
- Graphify code-only extraction indexed **73 code files**, producing **464 nodes, 1,126 clustered
  graph edges and 23 communities**. It skipped documentation semantics; extraction token cost was
  **0 input / 0 output**. Structural edges include inference and are not runtime proof. The first
  unclustered export contained 1,388 edges; clustering collapses parallel structural relationships.
- Graph health: no missing/dangling endpoints; eight self-loop warnings correspond to verified
  recursive calls (configuration composition, geometry traversal and workspace copying), not
  broken references. Parallel-edge collapse limits relationship detail in the clustered graph.
- Local graph artifacts: `graphify-out/graph.json`, `GRAPH_REPORT.md`, and `graph.html`.
  Graphify's recorded Git revision is the existing scaffold HEAD; new extraction files are
  uncommitted. File-level cache fingerprints, rather than HEAD alone, describe this working tree.

Live downloads, regional rebuilding, current legal/source verification, visual browser QA of
maps, OrcaCast model integration and non-Python-3.14/platform acceptance were not run. Copied
historical manifests retain original absolute paths and hashes; do not mistake them for outputs
of the new workspace configuration. The full application test suite is outside this extraction.
