# Architecture

The package owns source acquisition, normalization, explicit-grid overlay and flat Governance products. It has no application or sibling-toolkit runtime dependency.

1. Configuration selects source identity, local inputs, acquisition rules and qualified coverage.
2. Explicit acquisition or provisioning retains original geometry/attributes with receipt and hash evidence.
3. Offline normalization produces temporary EPSG:4326 source-qualified features and parts, preserving originals separately.
4. An explicit H3 grid defines cell support. The production overlay uses `application_only=True` to compute required counts and memberships without unused line/point/area derivatives. Unified marine conservation computes its separately qualified polygon-union coverage. All methods preserve missingness and source distinctions; native engines retain scientific reconstruction support.
5. `build_products` / `export_products` materializes the twenty selected features with readable name lists for memberships, writes those plus H3 identity to flat Parquets, and retains original GeoParquets and a local catalog. Version 5 embeds the lossless scientific support partition in final Parquet metadata. No separate audit/coverage output is retained by a successful ordinary build. Legacy external audits remain readable and protected while their existing products depend on them.
6. `validate_products` restores scientific support, recomputes the selected assignment view and checks exact arrays, presence/membership consistency, qualified absence, output contracts, identities and hashes before use. `compact-data` applies the same self-contained projection to explicitly selected retained deliveries offline. Ordinary line/polygon overlap checks use the original geometry dimension even when clipping collapses it to a point/edge.

Presentation grouping may combine retained identity arrays but cannot change source meaning, invent legal status or pool incompatible quantities. OriginalData is the retained input boundary; native artifacts and H3 matrices are implementation intermediates, not additional public deliveries. Consumers read the declared product and source contracts rather than depending on internal module layouts.
