# Federal maritime-zone sources

This producer preserves the native line geometry and zone identity published by
the source agencies. It does not buffer lines into polygons, infer a zone from a
nominal nautical-mile distance, dissolve nested zones, or publish an
`IS_FEDERAL_WATER` field.

## United States

NOAA Office of Coast Survey recommends its dynamic services for the most current
maritime limits and boundaries. The producer archives each relevant service
layer separately, with the full acquisition request, raw response pages,
retrieval time, checksum, and source metadata:

- [12 nautical mile territorial sea (layer 1)](https://maritimeboundaries.noaa.gov/arcgis/rest/services/MaritimeBoundaries/US_Maritime_Limits_Boundaries/MapServer/1)
- [24 nautical mile contiguous zone (layer 2)](https://maritimeboundaries.noaa.gov/arcgis/rest/services/MaritimeBoundaries/US_Maritime_Limits_Boundaries/MapServer/2)
- [EEZ and maritime boundaries (layer 3)](https://maritimeboundaries.noaa.gov/arcgis/rest/services/MaritimeBoundaries/US_Maritime_Limits_Boundaries/MapServer/3)
- [NOAA source description and legal references](https://nauticalcharts.noaa.gov/data/us-maritime-limits-and-boundaries.html)

These services publish polylines, not complete zone polygons. A source layer can
contain an outer-limit segment and a shared international-boundary segment. The
producer therefore records both `ZONE_TYPE` (the separately published zone
layer) and `GEOMETRY_ROLE` (the source rule for the individual segment). NOAA
marks the GIS data as not for legal use; controlling charts and legal
instruments prevail. The source feature publication date is used as
`SOURCE_VINTAGE`, while the snapshot retrieval time remains in the manifest.

The selected NOAA layers do not publish internal-water polygons. Internal-water
geometry is recorded as unavailable and is not inferred shoreward of a baseline.

## Canada

Canada's [Oceans Act](https://laws-lois.justice.gc.ca/eng/acts/O-2.4/) keeps
internal waters, territorial sea, contiguous zone, and exclusive economic zone
legally distinct. The Canadian Hydrographic Service calculates maritime limits
and official ENCs depict them, but this review did not identify a current public
machine-readable authoritative download for all four Canadian zones:

- [Canadian Hydrographic Service maritime-boundary role](https://www.dfo-mpo.gc.ca/science/hydrography-hydrographie/advise-expertise-eng.html)
- [GeoBase Canadian Geopolitical Boundaries archive](https://www.download-telecharger.services.geo.ca/pub/nrcan_rncan/archive/vector/geobase_cgb_lgc/)

The producer publishes the available archived GeoBase CGB Level 1 EEZ limit
lines, retaining their feature-level source agency (DFO where present), source
status, update date, type, and positional-accuracy field. CGB is an archived
government cartographic reference, not the controlling legal boundary. Canadian
internal-water, territorial-sea, and contiguous-zone geometries remain explicit
unavailable states; they are not generated from the EEZ, shoreline, seascape
water support, or nominal offsets.

## Outputs

- `federal_maritime_limits.parquet`: combined U.S. and Canadian native limit lines
- `us_maritime_zone_limits.parquet`: U.S. source-native limit lines
- `canadian_maritime_zone_limits.parquet`: available Canadian EEZ reference lines
- `zone_availability.json`: explicit country-by-zone availability and source gaps
- `manifest.json`: source snapshots, vintages, checksums, clipping diagnostics,
  counts, geometry policy, and related-artifact checksums

Every geometry output is clipped deterministically to configured `full_area`
after acquisition. Raw snapshots remain unchanged.
