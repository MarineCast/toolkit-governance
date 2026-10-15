![Coastal chart](assets/governance-toolkit-banner.png)

# Marine governance Parquets

`toolkit-governance` produces H3 cells × metric columns in a flat `Data/Governance`
directory. Keep R6 and R8 in separate static Parquets, with one optional dated
Parquet per resolution when temporal evidence supports it. A small update catalog
and one original-shape GeoParquet per source dataset complete the output.

Start with the [Parquet output guide](parquet-products.md) for installation,
acquisition boundaries, building, reading and updating. There are no governance
data releases or current pointers. Units, source provenance, coverage and missingness
are embedded in the Parquets. Original feature extents live in `OriginalData`.

Seventeen implemented collections cover protected areas, jurisdictional references,
fisheries systems, vessel-management references and administrative context.
Seven other catalog families remain planned. The default native normalization
extent is the Northeast Pacific (-180, 32, -109, 72); H3 cells are supplied explicitly.

Read [contracts](CONTRACTS.md), [layers](layers.md), [sources and rights](reference/sources.md)
and [limitations](limitations.md) before interpreting metrics. All current outputs
remain research-only and model-ineligible. Geometry, current law, effective dates,
source vintage and retrieval times are distinct.
