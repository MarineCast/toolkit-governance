# Transport Canada fixed-zone reference

This implementation parses the exact pinned [2026 interim order](https://tc.canada.ca/en/interim-order-protection-killer-whale-orcinus-orca-waters-southern-british-columbia), version 2026-05-22.
Closed Schedule 2 coordinate rings provide Saturna/Pender vessel-restriction references;
the closed Schedule 3 Swiftsure ring provides a speed reference. Native records retain
instrument version, clause, authority, applicability, exception references, original
10 knots over ground where applicable, and the June 1 through November 30 2026 dates
with an inclusive day-precision end. The pinned original instrument remains authoritative
for full exceptions and interpretation; these records are research-only.

The Nitinat speed boundary explicitly follows the coastline and is excluded pending
pinned authoritative coastline support. Moving-animal approach distance and Schedule 1
border/coastal support are separate unresolved contracts. No straight coastline closure,
legal-currentness certification, navigation/safety score or historical reconstruction is supplied.
HTML changes fail the existing pin or parser roster validation; never auto-update the pin.
All acquisition/output stays in the caller workspace under retained source terms.


The 2026-10-20 Vessel Routing & Regulations interface keeps every typed identity
record and exposes one **Routing / regulation recorded** boolean. This combines
recorded-reference presence, not mandatory legal status or area/length measures.
True requires a recorded feature; false requires independently evidenced complete
full-cell inventory coverage for every expected component and observed empty
memberships. Current no-hit support remains unknown. Existing native roles,
source attributes/dates and applicability/exceptions remain retained. Unused numeric area/length/point arrays are not computed or exported by the
production application overlay. Original geometry, roles and source attributes
remain retained; internal scientific engines can reconstruct qualified measures. See the
canonical `docs/parquet-products.md` vessel-family contract.


The display combines all eight shipping roles and all seven traffic-scheme roles
as Shipping Lanes & Traffic Separation Zones; Speed Restriction Zones stays separate.
Every original role, source record, feature ID and part remains paired in the
combined identity. The hidden shipping-only quartet is compatibility support,
not a separate displayed feature. No mixed area/length coverage is inferred.

## Public handoff boundary

Source evidence and native processing described here are distinct from public
columns. The [flat product contract](../../../../docs/parquet-products.md) and
[exact physical schema](../../../../docs/reference/columns.md) define delivery.
OriginalData preserves source geometry/attributes and receipt evidence; native
manifests, diagnostic products and unused scientific measures are internal build
support. No source qualification is broadened by the application projection.
