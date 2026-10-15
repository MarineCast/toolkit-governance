> Version 0.3 public output uses the [flat Parquet workflow](parquet-products.md).
> Native artifacts and release/study commands below describe historical or internal workflows;
> they are not the current public data layout.

# Configuration

The selected workspace contains editable YAML, raw snapshots, processed products,
and inspection outputs. Installed package resources are read-only defaults copied
by `init`; they are never a data/output directory.

## Choose the workspace

Precedence is:

1. CLI `--workspace`.
2. The `GOVERNANCE_WORKSPACE` environment variable.
3. The process current directory.

```sh
governance --workspace /absolute/path/to/governance-workspace init
export GOVERNANCE_WORKSPACE=/absolute/path/to/governance-workspace
governance catalog
```

`init` copies missing config/catalog files and preserves existing files.
Rerunning it does not reset your configuration or acquire data.

## Configuration files

| File | Responsibility |
| --- | --- |
| `config/common.yaml` | Named WGS84 processing extent |
| `config/data/governance/governance.yaml` | Sources, collection registry, clipping, coverage regions, raw/processed paths, catalog, and inspection |
| `config/data/governance/<category>/<collection>.yaml` | Family configuration extending the shared governance file and selecting a collection |
| `config/data/governance/feature_catalog.yaml` | Explicit implemented/planned collection and feature metadata |
| `config/data/presentation_settings.yaml` | Shared presentation settings |

The default `area: full_area` refers to `areas.full_area.bbox_wgs84`:

```yaml
areas:
  full_area:
    description: Northeast Pacific governance processing extent.
    bbox_wgs84:
      min_lon: -180.0
      min_lat: 32.0
      max_lon: -109.0
      max_lat: 72.0
```

The current governance loader requires `full_area`. Keep that name when changing
bounds. Narrowing the extent can remove required family subsets; the sanctuary
publisher still requires its configured six-site roster. Rebuild and validate
products against the new extent rather than reusing old manifests.

## Path rules

Relative paths **inside YAML resolve against the workspace**, even when the
configuration file itself is supplied by absolute path. A relative `--config`
also resolves against the workspace. CLI inspection/overlay `--output` paths and
the overlay's `--grid` path are process-relative; absolute paths avoid ambiguity.

```sh
governance --workspace /absolute/path/to/governance-workspace \
  catalog --config /absolute/path/to/alternate-governance.yaml
```

That alternate file selects configuration, not a different data workspace.
Sources can use explicit absolute local paths. International reconciliation needs
the provisioned local support described in [workflows](WORKFLOWS.md#external-local-inputs).

## Source and coverage settings

Each source records provider, acquisition type, URL/local path, snapshot path,
vintage, license, attribution, legal citation, redistribution terms, authority
scope, limitations, and region-specific coverage. Archive sources may also pin
SHA-256 and archive members/layers. Keep pins paired with the exact intended source.

Configured coverage and runtime availability are different. Downloading a source
does not automatically make its geographic coverage complete. An unavailable or
reference-only source must remain explicitly qualified.

YAML composition supports mapping deep-merges, list replacement, references,
environment values and cycle checks. The loader rejects unknown root/source/collection/
clipping/path/inspection keys, malformed booleans, invalid bounds and invalid source references.
Read the resolved configuration and product manifest after changing it.

Direct/vector caches require compatible identity, selector and support receipts. Only a
reviewed immutable full-source ZIP contract may declare `immutable_full_source_archive: true`;
it also requires a configured verified SHA-256, direct-archive acquisition, an unfiltered
`1=1` selector, no mask and no server filtering. Pinning a local subset alone is insufficient.
Older strict loaders reject this new key; configurations using it require 0.2.1. Existing
source pins are never replaced automatically. See [cache contracts](query-api.md#cache-and-network-modes).

## Output and presentation settings

Defaults place processed collections under `data/processed/domain/governance/`
and maps under `outputs/domains/governance/`. Collection paths are explicit in
the governance configuration. Inspection colors and default visibility are
collection-specific; simplification defaults to 250 metres for display only.

If you change artifact paths, review matching feature-catalog entries before
using `catalog --verify-artifacts`. In maintained repository defaults, keep
`config/` and `src/governance/resources/config/` byte-identical. This parity rule
does not require copying personal workspace edits back into installed resources.
