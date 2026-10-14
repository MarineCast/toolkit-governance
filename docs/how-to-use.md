# Install, build and update

Follow the [Parquet output guide](parquet-products.md). Initialize an explicit source
workspace, review configured providers, pins and source rights, and acquire or
provision inputs explicitly. Then build on supplied H3 grids into `Data/Governance`.

Builds do not acquire data. They retain one original GeoParquet per source dataset,
write one static metric Parquet per resolution, and remove temporary native and
overlay intermediates. Current source inventories have no reconstructed date axis.
Updates replace the current flat directory after validation; there are no releases.

For single-layer in-memory exploration see [query API](query-api.md). Source dates
and retrieval times are distinct, and all current metrics remain model-ineligible.
