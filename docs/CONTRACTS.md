# Contracts

The canonical public contract is [Parquet products](parquet-products.md). [Family pages](layers.md) define displayed features and preserve source-specific meanings. Source DATA_SOURCES.md files govern acquisition and provider qualifications; source code and tests remain authoritative for implemented behavior.

Required invariants are explicit H3 row identity, exact native feature/record/part lineage, separate source and legal times, declared units and denominators, all-overlap memberships, honest null support and `model_eligible=false`. A successful build or complete query receipt cannot establish current law or complete geographic inventory.

Use [CLI/Python API](reference/cli.md) for the production entry points and [coverage/refresh](coverage.md) for retained-original rebuilds. Public files have no releases, pointers, manifest sidecars or study bundles.

Product contract v5 stores exactly the selected feature columns plus H3, with checksum-bound scientific support inside the final Parquet metadata. No external audit is required for new products. Validation restores original arrays, checks the materialized view and rejects presence flags inconsistent with membership/completeness evidence. Legacy v2–v4 external audits remain required for their unchanged products. See the [delivery contract](parquet-products.md#compact-delivery-and-external-audit).
