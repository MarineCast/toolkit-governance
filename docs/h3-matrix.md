# Explicit H3 overlay matrix

Canonical governance products remain native EPSG:4326 geometry. The optional
`export-h3-matrix` command derives a separate inspection/context table from
checksum-verified native products and an explicitly provided H3 grid. Install
`toolkit-governance[h3]` to enable it. No application or implicit grid is required.

```sh
governance --workspace /path/to/workspace export-h3-matrix \
  --grid /path/to/h3-grid.parquet --length-crs EPSG:32610 \
  --allow-partial --output /path/to/processed/governance-h3-metrics.parquet
```

The input must contain unique, valid `(H3_INDEX, H3_RESOLUTION)` pairs. Each output
row is exactly one provided cell, retaining both resolutions when supplied. The
overlay uses full H3 polygons, not water-clipped footprints or cell centres.
It supports a bounded grid that does not cross the antimeridian. Native products
are validated without modification; their feature IDs and part IDs remain intact.
All configured collection products and manifests are required. Missing or
corrupt products fail the export rather than yielding a misleading partial file.
Raw source checksums are verified against native manifests. Missing raw sources
are allowed only when the native manifest already records them as unavailable.

For each collection, columns prefixed `<collection_id>__` contain:

- `FEATURE_COUNT`: distinct recorded source-backed features with positive area
  or length intersection (or a recorded point inside/on the cell).
- `POLYGON_COVERAGE_FRAC`: area of the union of recorded polygon intersections
  divided by full cell area, calculated in equal-area EPSG:6933. Overlaps and
  clipped parts are not double-counted. This is reference geometry coverage,
  not protected status or legal jurisdiction. Country-water support polygons
  remain derived reference support.
- `LINE_LENGTH_M`: unioned recorded line intersection length in the explicitly
  selected metre-based projected CRS. Use a regional CRS appropriate to the grid.
- `POINT_COUNT`: distinct recorded point features intersecting the cell.
- `INTERSECTION_STATUS`: `recorded_geometry_intersects` or
  `no_recorded_geometry_under_partial_coverage` (or unavailable/complete variants).
- `SOURCE_COMPLETENESS`: the native manifest's explicit completeness status.
- `NATIVE_<column>`: sorted distinct source-attribute values for intersecting
  native parts, represented as lists of strings. These are set summaries, not
  aligned feature records. `NATIVE_GOVERNANCE_FEATURE_ID` and
  `NATIVE_GEOMETRY_PART_ID` link to exact records in the retained native product.
  All non-geometry native attributes are retained, including names, source IDs,
  effective dates, vintage, authority, legal status, QC and family-specific fields.

With incomplete coverage, an empty intersection leaves counts and measures null;
it is not evidence of absence. If a recorded feature intersects, counts and
measures describe only the intersecting records, not the completeness of the
inventory. A geometry type not represented among the intersecting records has
null measures, not inferred zero. `MODEL_ELIGIBLE` is false for every row.
Neither source effective dates nor unknown dates are filtered or inferred:
this is an inventory-snapshot overlay, not an as-of legal reconstruction.
Native dates and legal instruments must be reviewed for date-specific uses.
The sanctuary manifest's complete named West Coast roster is preserved as its
source-completeness label; it does not establish complete authoritative coverage
of arbitrary grid cells, so empty intersections remain null for that roster.

Parquet metadata `governance_h3_matrix` embeds the source and grid checksums,
native manifests with citations/rights/coverage and retrieval/build dates,
configuration identity, field definitions, projection choices, implemented
collections and the native catalog's planned entries. This overlay has its own
schema; it does not change the native manifest contract or claim adoption of
the proposed ecosystem H3 contract. It confers no model eligibility or legal
authority. Snapshot import and rebuild dates do not establish current law or
fresh provider acquisition. Keep raw and generated data local under source terms.
Output writes are atomic and replacement requires `--overwrite`.


Routing collections use declared `metric_groups` keyed by source and component role. Their
collection-level aggregate columns are intentionally absent. Each group points to its native
collection/source/role; all other collections retain their established columns. Empty role
subsets retain the native schema and produce nulls. Delivery1.1.0 includes only dimensionally
applicable routing metrics and retains source-specific coverage and overlap policy. Full native
record relationships remain the companion authority for chart/attribute inspection.
