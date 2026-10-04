# Governance Toolkit

<img src="docs/assets/governance-toolkit-banner.png" alt="Ink coastal chart with islands, navigation markers, and boundary lines" width="100%">

Species-neutral, source-backed marine governance geometry: protected areas, sanctuaries,
jurisdictional reference boundaries and fisheries management areas. The distribution is
**`toolkit-governance`**; the Python package and command are **`governance`**.
It installs independently of OrcaCast and sibling toolkits.

## Implemented scope

Ten collections have normalization, build and inspection modules; acquisition is explicit and bounded:

- Marine protected areas (NOAA inventory and DFO designations/areas of interest).
- National marine sanctuaries (six NOAA ONMS boundary sources).
- International boundaries (source-preserving reference geometry and reconciliation).
- Federal waters (U.S./Canadian maritime limits and derived reference products).
- State/provincial waters (configured BOEM submerged-lands boundary source).
- Fisheries management areas (configured WDFW recreational marine areas).
- Ports (NGA physical point inventory).
- Critical habitat (provisioned NOAA NMFS polygon and line references).
- County/regional boundaries (U.S. Census county equivalents; Canadian regional gap retained).
- Wildlife refuges (selected FWS and ECCC systems; provisioned reference snapshots).

The catalog includes 24 collections; 14 remain planned. Collection names do not establish
complete U.S./Canadian coverage. Read [contracts](docs/CONTRACTS.md) and the per-family
`DATA_SOURCES.md` files before interpreting outputs. Canonical products use **native geometry**,
not H3; all fields remain **model-ineligible by default**. Reference maps, legal authority,
effective time and source vintage are distinct.

## Install and initialize

Python 3.11+ and a compatible geospatial stack are required. Hosted offline package checks run on Python 3.11 and 3.14.
Real-data validation is separately documented in local release evidence.

```sh
python -m pip install -e '.[test]'
python -m pytest -q
governance --help
governance --workspace /path/to/workspace init
```

For a regular installation, use `python -m pip install .`. `init` copies missing configuration
and catalog files only; it preserves edits and downloads nothing. Workspace precedence is CLI
`--workspace`, then `GOVERNANCE_WORKSPACE`, then the current directory. Package installation
never makes site-packages a data/output directory. An absolute config path selects that file;
relative paths inside it still resolve against the workspace.

Edit `config/common.yaml` and `config/data/governance/governance.yaml` in that workspace. The
inherited `full_area` extent is the Northeast Pacific (-180, 32, -109, 72); the loader currently
requires that named area. Existing configuration supplies real source URLs and snapshot pins,
not synthetic source data. Acquisition must be requested explicitly.

```sh
governance --workspace /path/to/workspace catalog
governance --workspace /path/to/workspace download marine_protected_areas
governance --workspace /path/to/workspace build marine_protected_areas --allow-partial
governance --workspace /path/to/workspace inspect --as-of 2026-09-16
```

Read [workflows](docs/WORKFLOWS.md) before builds: partial coverage requires explicit acceptance,
outputs use per-file atomic replacement, and multi-product builds are not whole-workspace
transactions. `--overwrite` is explicit. Local boundary reconciliation also needs externally
provisioned seascape support; no sibling checkout is implicitly searched.

## Python API and documentation

```python
from governance import initialize_workspace, load_governance_config
from governance.protected_areas.marine_protected_areas.build import build

initialize_workspace('/path/to/workspace')
# Set GOVERNANCE_WORKSPACE before loading configuration or invoking a producer.
config = load_governance_config()
# Acquisition and builds are separate explicit operations.
```

- [Architecture](docs/ARCHITECTURE.md): ownership, APIs, configuration and developer navigation.
- [Contracts](docs/CONTRACTS.md): grain, geometry, missingness, time and provenance.
- [Workflows](docs/WORKFLOWS.md): acquisition, building, inspection and validation.
- [Explicit H3 matrix](docs/h3-matrix.md): optional consumer-grid overlays with retained native authority and missingness.
- [Migration and validation](docs/MIGRATION.md): extraction inventory and acceptance limits.
- [Roadmap](src/governance/TODO.txt): inherited research backlog; current extraction status is in
  the migration report rather than inferred from historical checkboxes.
- [Agent guidance](AGENTS.md): repository-specific rules and Graphify commands.

## License and validation boundary

Software retains the source [Apache 2.0 license](LICENSE). Data has separate source-specific
rights and attribution requirements. Downloaded snapshots, products, local migration evidence
and Graphify caches are ignored and are not distributed in the wheel.

Offline tests and installed-wheel checks do not establish fresh source availability, legal
currency, complete regional coverage, production readiness or downstream model integration.
The proposed MarineCast H3 manifest v0.1 does not cover this native-geometry contract.
