# Typed CHS / NOAA routing references

Source definitions and rights:

- [Official CHS catalog](https://open.canada.ca/data/dataset/6ab2803a-aace-4e60-83ed-44a7e0ccd1d8)
  links the live EPSG:4326 service, object dictionary and OGL-Canada. Query layers 2–5 only,
  record exact AOI/ID roster/pages/metadata/retrieval time, and cap network bytes explicitly.
  Preserve MERGE_SRC, LNAM, ENC_NAME, CATTSS, STATUS, dates, ORIENT and every other attribute.
- [NOAA2026 metadata](https://www.fisheries.noaa.gov/inport/item/67919/full-list)
  links the pinned `VesselRoutingMeasure.zip`, containing a NAD83 GeoPackage. Publication
  2026-03-16/source period 2024-07–2026-03 is not legal effective time. No maintenance planned;
  completeness untested; planning-only, not navigation. Do not substitute the older live service.
- [Marine Cadastre disclaimer](https://hub.marinecadastre.gov/pages/disclaimer) governs NOAA
  source reuse. Government-hosted information is public-domain unless otherwise annotated;
  retain attribution, do not claim ownership/endorsement, and do not present modified content
  as unchanged official information. CHS requires [OGL-Canada](https://open.canada.ca/en/open-government-licence-canada)
  attribution/license and no endorsement. Current releases are local only.

`routing.py` explicitly maps provider object types to fifteen separate source/role groups across
shipping and TSS families. `shipping_lanes` is a catalog family name: navigation lines,
recommended tracks/centerlines/lane parts, two-way route parts, fairways and recommended routes
are not all mandatory lanes. Ferry routes are outside scope. Nonrouting NOAA types are excluded.
Unknown object types fail closed. No legal effective date, enforcement status or compliance is
inferred from raw DATSTA/DATEND/STATUS or CFR/citation fields. Original date strings may be blank,
partial or recurring, so they stay raw. Source chart object types and their attributes are not
converted into independent legal claims.

`download` requires provisioned bounded snapshots. NOAA preparation uses `noaa_source_frame`
to retain original GPKG FID as SOURCE_FID before writing a source GeoParquet; keep original ZIP,
its hash/receipt and the frame transformation receipt alongside it. CHS snapshots retain exact
metadata and complete ID-batched GeoJSON responses. Build requires explicit `--allow-partial`.
Native EPSG:4326 geometry uses existing AOI clipping; no presentation simplification replaces it.

CHS logical object identity uses source object type plus LNAM where present, with fallback to
snapshot OBJECTID when absent. Repeated chart records remain separate SOURCE_FEATURE_ID/part
records with ENC_NAME retained. Counts describe distinct object identifiers within each role,
not unique physical routes or whole schemes. Unions remove additive area/length overlap within
one source/role, including repeated charts. Geometry disagreements across charts remain a union;
no inferred preferred chart scale or cross-source deduplication. Never sum role/source groups as
unique route coverage. All fields are model-ineligible and all products remain research-only.


The LNAM object-identity interpretation follows IHO S-57 section4.3:
https://iho.int/uploads/user/pubs/standards/s-57/31Main.pdf . It establishes feature-object identity,
not independent proof of a unique real-world route or current governing rule.
