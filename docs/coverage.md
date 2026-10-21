# Coverage and refresh

Coverage describes the evidence available for a requested source, scope and cell. It is not a binary test of whether a governance rule exists.

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Valid source checksum | Exact retained bytes | Source currency or authority |
| Reconciled query receipt | The declared bounded request was acquired consistently | Complete geography, all source classes or current law |
| Positive intersection | A documented reference intersects the stated support | Universal restriction, legal ownership or protection |
| No recorded intersection under partial support | No retained match | Zero, false, no habitat, no restriction or no jurisdiction |
| Product validation | Contract/checksum/identity consistency | Scientific or legal completeness |

## Offline rebuild from retained originals

Use the public `build_products` API or `governance build --original-data` with a complete validated flat Governance directory and explicit grids. The builder verifies its catalog, substitutes originals by source ID, normalizes in temporary storage, computes the supplied cell products and writes a new flat directory. It never downloads missing sources. Keep the original directory until the replacement has been reviewed and validated.

```python
from governance.products import build_products, validate_products

result = build_products(
    ['/path/to/grid-r6.parquet', '/path/to/grid-r8.parquet'],
    '/path/to/review/Governance',
    workspace='/path/to/workspace',
    config_path='/path/to/workspace/config/data/governance/governance.yaml',
    original_data='/path/to/retained/Governance',
    allow_partial=True,
    keep_workspace_data=True,
)
print(validate_products(result))
```

Use the explicit API `workspace` argument; relative YAML paths retain workspace semantics. A refresh with unchanged originals is a processing refresh, not a new observation or newer legal inventory.

## Acquiring replacement evidence

Read the family's authoritative DATA_SOURCES notes and inspect resolved configuration/preflight. Select an explicit bounded provider operation, with declared source IDs, query scope, limits, rights and required receipts. `download COLLECTION` is an explicit acquisition path; some sources require separately provisioned official snapshots and refuse implicit bulk requests. Never silently change a pin or substitute a different provider edition.

Review geometry type, feature/record/part identities, source dates, selectors, receipt completeness, authority scope and rights before promoting replacement originals. Compare delivered fields, all overlaps, support states and nulls on the same grid. Keep counts and coverage denominators consistent with the [product contract](parquet-products.md). Retain qualifications where source editions disagree or legal evidence is incomplete.

## Geographic and legal gaps

Each [family page](layers.md) explains its gaps. Regional source coverage is not global coverage. Indigenous administrative references do not define all Indigenous territories or rights. Geographic country/state assignments do not establish legal marine ownership. Critical-habitat polygon presence does not resolve conditional habitat attributes. Conservation proposals/interim references do not enter designated count/coverage. Exclusion/routing geometry does not establish current activation or vessel-specific applicability.

Do not infer dates between snapshots, construct a 2009-present history, or report legal absence from missing input. Preserve all unknowns in downstream views and exports.
