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
