# Regional Boundaries reference inventory

## U.S. counties

Source: [2025 Census TIGER/Line counties](https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip).
[Census vintage documentation](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
gives a 2025-01-01 boundary/name reference date. The configured SHA-256 pins the
archive; direct acquisition is capped at 100 MB. The reader transforms NAD83 to
WGS84 and retains all attributes and leading-zero five-digit GEOIDs. These are
statistical/cartographic references, not an independent legal boundary finding.

## British Columbia regional districts

Source: [BC ABMS regional districts](https://catalogue.data.gov.bc.ca/dataset/d1aff64e-dbfe-45a6-af97-582b7f6418b9),
[official GeoBC service layer 16](https://delivery.maps.gov.bc.ca/arcgis/rest/services/whse/bcgw_pub_whse_legal_admin_boundaries/MapServer/16).
Contains information licensed under the
[Open Government Licence – British Columbia](https://www2.gov.bc.ca/gov/content?id=A519A56BC2BF44E4A008B33FCF527F61).
Catalogue metadata and licence identity were checked on 2026-10-19.

The source polygons derive from Letters Patent metes and bounds; those descriptions
prevail over digital discrepancies. Regional government operations may differ
while administrative changes are resolved. Neither record-update/OIC dates nor
retrieval time supplies a dated legal history. `LGL_ADMIN_AREA_ID` is the stable
source identity; names, boundary class, group, OIC, update, map-status and all other
attributes remain in OriginalData and prefixed native attributes.

Explicit acquisition uses one feature per page, stable before/after ID rosters,
100-feature / 100-request / 64 MB aggregate response budgets, and full returned
geometry without generalization. The 2026-10-19 receipt contains 28 records:
27 regional districts plus Stikine Region (Unincorporated), ID 361. The latter
remains in OriginalData but is excluded from district memberships. Northern Rockies
Regional Municipality is excluded by the provider's regional district layer.
No municipality or electoral-area substitution is made.

## Output meaning

The public family is **Administrative Boundaries**; its stable machine key remains
`county_regional_boundaries`. Exactly two final metric columns are retained:
**County / District Count** and **County / District Assignment**. The count is
unique source-qualified county/district IDs touched by the full closed native H3
cell. All names/IDs remain paired, including multiple matches, shared-edge and
vertex contacts. Part counts and overlapping source records never inflate totals.

Native processing still clips to the configured AOI; final metrics are recalculated
from checksum-bound full OriginalData polygons to avoid truncating edge cells.
Invalid polygons use `make_valid`, retaining only polygon-dimensional repair parts;
the original geometry stays unchanged. The current receipt needs this for qathet
(ID 322); field metadata records exact repaired IDs and method. No buffers,
nearest-coast assignments, offshore extrapolation or water-only clipping are used.

The eight legacy diagnostic/status columns are removed from final Parquets.
Metadata declares compact support `positive_partial_null_unknown_v1`: positive
counts/nonempty lists have partial inventory support; null is unknown (or unavailable
if no originals exist). Zero and empty lists are unsupported. The consumer derives
browser-only support columns from this declared contract; it does not acquire or
recalculate geometry. `MODEL_ELIGIBLE=false` remains unchanged. Mapped water extents
do not establish legal offshore ownership or exhaustive administrative jurisdiction.

See the [flat product contract](../../../../docs/parquet-products.md#regional-boundaries-interface-2026-10-19).

## Public handoff boundary

Source evidence and native processing described here are distinct from public
columns. The [flat product contract](../../../../docs/parquet-products.md) and
[exact physical schema](../../../../docs/reference/columns.md) define delivery.
OriginalData preserves source geometry/attributes and receipt evidence; native
manifests, diagnostic products and unused scientific measures are internal build
support. No source qualification is broadened by the application projection.
