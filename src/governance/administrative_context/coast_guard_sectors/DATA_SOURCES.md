# Coast Guard administrative references

USCG sectors and CCG regions are different organizational units; each source has its own metric
group. Provision bounded snapshots explicitly; the download workflow never performs an implicit
bulk request. USCG FID and CCG OBJECTID_1 identities and every original attribute are retained.
No operational jurisdiction, navigational safety, effective date or model eligibility is inferred.

USCG source: https://services9.arcgis.com/Fr5UUTVwNRJlXAkf/arcgis/rest/services/USCG_Sectors_view/FeatureServer/0
CCG source: https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/open_data_donnees_ouvertes/ccg_gcc_regions/MapServer/0
CCG catalog: https://open.canada.ca/data/en/dataset/02b9fc39-cd07-46ed-a413-42257e7ad717

USCG original metadata, derivative processing/citation metadata and source receipt qualifications
must remain attached to retained originals and product lineage. Redistribution clearance is unresolved. CCG uses Open
Government Licence - Canada and is a 2021 cartographic inventory, not a legal boundary source.

## Combined final interface — 2026-10-19

The public H3 products retain one **Coast Guard Assignment** membership column
(`coast_guard_sectors__feature_memberships_v1`) plus its support status, paired
administrative-feature count and count status. All twelve former CCG/USCG
component diagnostic/count/membership/status columns are removed from final
Parquets. Native processing still distinguishes source/unit roles; source-qualified
names, record IDs, geometry-part lineage, source-specific coverage records and both
OriginalData datasets remain retained.

Method `coast-guard-membership-union-1` unions the two existing typed membership
arrays without reprocessing polygons or summing area. Every overlap survives.
Missing source support remains unknown/unavailable; a verified empty combined list
and zero count require observed empty lists from both components. A support count
counts recorded administrative feature IDs, not equivalent jurisdictions or
operational coverage. The explorer offers only the Assignment feature.

## Derived Western water supplement — 2026-10-19

The CCG map is an administrative reference; its catalog explicitly says operations
are not limited to the drawn boundaries. It does not supply complete water coverage
for the study grid. At the user's request, final assignment method
`coast-guard-western-model-water-assignment-1` extends Western over retained,
explicitly identified BC model-water support. This is a derived geographic
assignment, not an authoritative change to the CCG polygon or operational/legal
jurisdiction. Both checksum-bound originals are preserved. Water-derived records
retain water source feature/part lineage and the CCG unit category identity;
original CCG memberships and every USCG record are unchanged. Partial support
remains partial. See the [product method](../../../../docs/parquet-products.md#western-bc-water-assignment-2026-10-19).

## Public handoff boundary

Source evidence and native processing described here are distinct from public
columns. The [flat product contract](../../../../docs/parquet-products.md) and
[exact physical schema](../../../../docs/reference/columns.md) define delivery.
OriginalData preserves source geometry/attributes and receipt evidence; native
manifests, diagnostic products and unused scientific measures are internal build
support. No source qualification is broadened by the application projection.
