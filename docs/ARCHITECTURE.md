# Architecture

The package owns source acquisition, normalization, explicit-grid overlay and flat Governance products. It has no application or sibling-toolkit runtime dependency.

1. Configuration selects source identity, local inputs, acquisition rules and qualified coverage.
2. Explicit acquisition or provisioning retains original geometry/attributes with receipt and hash evidence.
3. Offline normalization produces temporary EPSG:4326 source-qualified features and parts, preserving originals separately.
4. An explicit H3 grid defines cell support. The production overlay uses `application_only=True` to compute required counts and memberships without unused line/point/area derivatives. Unified marine conservation computes its separately qualified polygon-union coverage. All methods preserve missingness and source distinctions; native engines retain scientific reconstruction support.
5. `build_products` / `export_products` writes flat Parquets, original GeoParquets and a small catalog. Embedded Arrow metadata carries definitions, lineage, temporal grain and qualifications.
6. `validate_products` checks the output contract, identities and hashes before use.

Presentation grouping may combine retained identity arrays but cannot change source meaning, invent legal status or pool incompatible quantities. OriginalData is the retained input boundary; native artifacts and H3 matrices are implementation intermediates, not additional public deliveries. Consumers read the declared product and source contracts rather than depending on internal module layouts.
