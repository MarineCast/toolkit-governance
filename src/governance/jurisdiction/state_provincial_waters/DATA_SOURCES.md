# State and provincial waters sources

Phase 1 acquires the BOEM Submerged Lands Act (state seaward) boundary line from
the national BOEM/BSEE ArcGIS layer and clips it to `full_area`.

- Service: <https://gis.boem.gov/server/rest/services/BOEM_BSEE/MMC_Layers/MapServer/8>
- Legal context: Submerged Lands Act, 43 U.S.C. 1301-1315.
- Limitation: BOEM states that controlling coordinates are on official OPDs and
  SOBDs. The GIS line is not converted to a state-water polygon.

British Columbia marine administrative applicability is not assumed equivalent
to U.S. state waters. Provincial-water geometry remains unavailable.

The public delivery's single State / Province Assignment now uses geographic
model-water support: retained TIGER/Line county `STATEFP` 53/41 clipped to U.S.
water support for WA/OR, and the retained water source's explicit
`AREA=BRITISH_COLUMBIA` region for BC. The source-native BOEM diagnostics remain
unchanged. This is geographic assignment for modeling, not legal water ownership
or statutory provincial jurisdiction. Unmatched support stays unknown; counties
are not extended offshore. See [geographic water assignments](../../../../docs/parquet-products.md#geographic-water-assignment-interfaces-2026-10-19).

## Public handoff boundary

Source evidence and native processing described here are distinct from public
columns. The [flat product contract](../../../../docs/parquet-products.md) and
[exact physical schema](../../../../docs/reference/columns.md) define delivery.
OriginalData preserves source geometry/attributes and receipt evidence; native
manifests, diagnostic products and unused scientific measures are internal build
support. No source qualification is broadened by the application projection.
