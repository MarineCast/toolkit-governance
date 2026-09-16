# International boundaries sources

This layer publishes source-native Canada–United States boundary references and
derived country-water support polygons. It never creates a compromise line:
source geometries are compared as published, retained independently, and are not
snapped, averaged, or silently substituted for one another. Treaties,
coordinates, monuments, official records, and agency notices remain the
controlling legal authorities.

## Boundary sources

### International Boundary Commission digital boundary v1.3

- Versioned archive: <https://www.internationalboundarycommission.org/uploads/shapefile/us-canada-boundary-v1-3.zip>
- Product page: <https://www.internationalboundarycommission.org/en/maps-coordinates/coordinates.php>
- Pinned SHA-256: `eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1`
- Retained fields: section number/name and section-specific `MaxScale`.
- Limitation: IBC states that the digital line is for mapping only and must not
  be used to define the boundary. The toolkit therefore uses the line as the
  reconciliation baseline while preserving that non-controlling status.

The full-AOI slice contains sections 21–29. Their published scales are retained
per record: the western 49th parallel and 141st-meridian sections are 1:62,500,
the Straits of Georgia/Juan de Fuca section is 1:200,000, and Portland Canal and
Southeast Alaska are 1:250,000. Reconciliation uses 0.5 mm at source scale as a
transparent precision proxy; it is not represented as surveyed accuracy.

### NOAA U.S. Maritime Limits and Boundaries

- Service: <https://maritimeboundaries.noaa.gov/arcgis/rest/services/MaritimeBoundaries/US_Maritime_Limits_Boundaries/MapServer/>
- Catalog: <https://www.fisheries.noaa.gov/inport/item/39963>
- Authority fields: feature-level `LEGAL_AUTH`, `AOR`, `SUPP_INFO`, publication
  date, approval date, region, and unilateral-claim flag are retained.
- Limitation: NOAA labels the GIS reference “NOT FOR LEGAL USE.” The service does
  not report a positional-accuracy field for these records, so precision remains
  unknown rather than being inferred.

### Natural Resources Canada GeoBase CGB Level 1

- Archived archive: <https://www.download-telecharger.services.geo.ca/pub/nrcan_rncan/archive/vector/geobase_cgb_lgc/cgb_lgc_canada_shp_en.zip>
- Product specification: <https://www.download-telecharger.services.geo.ca/pub/nrcan_rncan/archive/vector/geobase_cgb_lgc/doc/GeoBase_cgb_en_Product_Specifications.pdf>
- Pinned SHA-256: `305bfb2445fdf408922b320740e66c79786fb35e81116dd21ca0c9a43f968381`
- Retained fields: source agency, source description, legislative/cartographic
  status, update dates, and `ACCUR` positional accuracy when present.
- Limitation: CGB is an archived cartographic product. Its international line
  records identify IBC lineage and its maritime records identify DFO lineage,
  but the geometry is not promoted to a controlling legal boundary.

## Canadian water-support context

The Fisheries and Oceans Canada Federal Marine Bioregions source used by the
canonical seascape water geometry is included in reconciliation as context:
<https://open.canada.ca/data/en/dataset/23eb8b56-dac8-4efc-be7c-b8fa11ba62e9>.
DFO describes bioregions as ecosystem-planning geometry whose boundaries may be
fuzzy. They are not international-boundary authority.

The canonical seascape artifact
`data/processed/domain/environmental_layer/seascape/spatial_support/water_geometry/TERRITORIAL_WATER_POLYGON.parquet`
is used only for full-domain spatial support, clipping, and labeled
country-water reference polygons. Its manifest records its mixed upstream
lineage. `LEGAL_BINDING_STATUS=derived_reference_geometry`,
`SOURCE_ROLE=spatial_support_only`, and
`SOURCE_LEGAL_STATUS=not_legal_authority` are mandatory on every published
country-water record.

Country labels are checked against the archived NRCan CGB country-area polygon.
That agreement is a QC test of allocation, not evidence that the assembled
seascape exterior is a legal maritime limit.

## Published products and unresolved segments

- `international_boundaries.parquet`: canonical mixed line/polygon inspection
  layer, clipped to `full_area`.
- `authoritative_boundary_segments.parquet`: source-authority-published IBC,
  NOAA, and NRCan segments, with legal status, scale/accuracy, and
  `BOUNDARY_QC_REASON`. “Authoritative” describes provenance, not legal effect.
- `country_water_polygons.parquet`: derived seascape support polygons with
  explicit country-allocation QC and non-authority status.
- `boundary_reconciliation.parquet`: per-IBC-section, per-source sampled distance
  results in EPSG:3347, including sample count, source scale, precision proxy,
  median/P95/max distance, match fractions, and reconciliation status.
- `manifest.json`: source checksums, clipping diagnostics, authority policy,
  related-artifact checksums, and the enumerated unresolved marine sections.

The current reconciliation aligns the IBC line closely with the NOAA and CGB
boundary references. Portland Canal remains only partially represented by the
DFO/seascape support interface, while Southeast Alaska lies outside the northern
coverage of those support products. Those support gaps are published as
unresolved comparisons; they are not repaired or snapped. Rebuild the artifacts
to refresh the exact measured values and manifest counts.
