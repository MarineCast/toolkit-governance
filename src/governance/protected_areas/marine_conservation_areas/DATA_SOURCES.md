# Unified marine conservation interface

This family consumes retained OriginalData owned by Marine Protected Areas,
Conservation Designations, Wildlife Refuges and National Marine Sanctuaries. It
adds no acquisition source, download or legal taxonomy. Those source families'
DATA_SOURCES files remain the acquisition and provenance authorities.

The [Parquet contract](../../../../docs/parquet-products.md#unified-marine-conservation-areas-2026-10-19)
defines eligible marine records, site-ID crosswalk evidence, original geometry
lineage, full-cell union coverage and separate proposed/interim reference support.
Unqualified terrestrial records and unresolved site identities are disclosed in
embedded audit metadata. The original provider attributes and source bindings
remain unchanged. Existing/interim/proposed status and PA/OECM/legal designations
remain distinct; no conservation score or legal-equivalence assertion is made.

## Public handoff boundary

Source evidence and native processing described here are distinct from public
columns. The [flat product contract](../../../../docs/parquet-products.md) and
[exact physical schema](../../../../docs/reference/columns.md) define delivery.
OriginalData preserves source geometry/attributes and receipt evidence; native
manifests, diagnostic products and unused scientific measures are internal build
support. No source qualification is broadened by the application projection.
