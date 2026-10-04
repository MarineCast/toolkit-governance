# Selected wildlife-refuge reference inventory

The source roster deliberately includes only these official inventory classifications:

- [FWS National Realty Boundaries](https://www.arcgis.com/home/item.html?id=745ed874c1394da3a9aae50267c9e049),
  layer 0: `RSL_TYPE = 'NWR'`. Attribute domain defines this as National Wildlife Refuge.
- [ECCC CPCAD](https://maps-cartes.ec.gc.ca/arcgis/rest/services/CWS_SCF/CPCAD/MapServer/0):
  `TYPE_E IN ('National Wildlife Area', 'Marine National Wildlife Area', 'Migratory Bird Sanctuary')`.
  Other provincial, private and Indigenous conserved-area classes are not treated as equivalent.

FWS data are compiled by the National Wildlife Refuge System Division of Realty. Its resource-grade
mapping dissolves tract interiors and generalizes select features by 1–30 metres, with geometry
repairs, curve densification and projection for the service. It is neither acquisition-approved
land nor a legal description. The source advises consulting FWS Realty for legal descriptions and
individual sites about public access. The archived source item includes its no-warranty disclaimer.
Retain FWS attribution and that disclaimer.

CPCAD is ECCC's compiled official protected/conserved-area reporting inventory. Preserve ECCC and
reporting-partner attribution under the [Open Government Licence - Canada](https://open.canada.ca/en/open-government-licence-canada).
Source fields include site type, reporting status, parent/zone identity, establishment/qualification
years, governance and management. Preserve their domain metadata and raw values without translating
a year into a legal effective date or claiming that a mapped status establishes present compliance.

`download wildlife_refuges` reuses provisioned inputs and refuses unbudgeted acquisition. Provision
ArcGIS snapshot-schema-version 1 inputs with the layer metadata, exact selection and AOI predicate,
complete object-ID query response, ID-batched feature pages, retrieval time and byte budget. Verify
no transfer-limit flags, missing/duplicated IDs or ArcGIS error responses. The first bounded run
used 10 IDs per page, EPSG:4326 output, AOI [-180,32,-109,72], 132 U.S. plus 68 Canadian source
query candidates and a 120 MB cap. Exact AOI clipping retained 132 U.S. and 40 Canadian
features; 28 Canadian server candidates were outside the precise AOI. The native pipeline
repaired 64 invalid FWS source geometries; immutable raw responses and repair diagnostics are
retained. Full acquisition evidence is retained in the local release.

The normalizer defensively filters types again. `SOURCE_FEATURE_ID` namespaces the snapshot's
OBJECTID; source GlobalID, organization codes and Canadian parent/zone IDs remain attributes.
These IDs must not be assumed stable across future snapshots. Every original attribute survives
under `FWS_` or `ECCC_`; canonical effective dates and legal citations remain null. Native geometry
is clipped through the shared antimeridian-safe pipeline. All outputs remain research-only and
model-ineligible. Empty cells are unknown absence, and these selected systems do not establish
an exhaustive inventory of every feature that might be called a refuge.
