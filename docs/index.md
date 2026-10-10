# Governance Toolkit

![Ink coastal chart with islands, navigation markers, and boundary lines](assets/governance-toolkit-banner.png)

Species-neutral, source-backed marine governance geometry: protected areas,
sanctuaries, jurisdictional reference boundaries and fisheries management areas.
The distribution is **`toolkit-governance`**; the Python package and command are
**`governance`**. It installs independently of OrcaCast and sibling toolkits.

Fifteen collection pipelines are implemented; the 24-entry catalog includes nine
planned families. All current collections are **research-only**. Collection names
do not establish complete U.S./Canadian coverage, current regulatory compliance or
legal applicability. Canonical products retain native EPSG:4326 geometry and all
fields remain **model-ineligible by default**. Missing support is never observed
absence. Read the [scientific contracts](CONTRACTS.md) and
[production readiness and limitations](production-readiness.md) before using outputs.

## Get started

Python 3.11+ and a compatible geospatial stack are required. From a repository checkout:

```sh
python -m pip install .
governance --help
governance --workspace /path/to/workspace init
governance --workspace /path/to/workspace catalog
```

Initialization copies missing configuration only; it preserves edits and downloads
nothing. Review the workspace's extent, source pins, rights and paths before
acquisition or builds. Follow the [workflows](WORKFLOWS.md) for explicit downloads,
partial-build acceptance and overwrite boundaries. The [repository README](https://github.com/MarineCast/toolkit-governance/blob/main/README.md)
contains installation and API examples.

The current local frozen-study checkpoint contains 2,621 R6 cells and 88,243 R8
cells with 173 delivery fields. It is a bounded research release; cached query
footprints and unknown completeness remain explicit. See [current readiness](production-readiness.md#current-frozen-study-checkpoint-2026-10-09).

## Documentation guide

- [Install and configure](getting-started.md): practical installation and workspace setup.
- [CLI reference](cli.md): command effects and required arguments.
- [Frozen study](study-guide.md): PR7 workflow, inputs, recovery and validation.
- [Source and quality index](sources.md): pinned family notes and acceptance evidence.
- [Troubleshooting](troubleshooting.md): configuration, staging, locks and publication.
- [Scientific contracts](CONTRACTS.md): geometry, grain, provenance, time and missingness.
- [Workflows](WORKFLOWS.md): acquisition, build, inspection and external inputs.
- [Explicit H3 matrix](h3-matrix.md): optional consumer-grid overlays retaining native authority.
- [Production readiness](production-readiness.md): source-specific limitations and release boundaries.
- [Architecture](ARCHITECTURE.md): package ownership and configuration.
- [Migration and validation](MIGRATION.md): historical extraction evidence and unrun checks.
- [Documentation site](documentation-site.md): local preview, CI artifacts and publication.

Software uses the [Apache 2.0 license](https://github.com/MarineCast/toolkit-governance/blob/main/LICENSE).
Data has separate source-specific rights and attribution requirements. Offline tests
and documentation builds do not establish source freshness, legal currency,
complete coverage or downstream model integration.
