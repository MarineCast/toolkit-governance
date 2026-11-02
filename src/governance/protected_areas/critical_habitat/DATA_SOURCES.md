# Critical habitat reference inventories

Primary service: <https://maps.fisheries.noaa.gov/server/rest/services/All_NMFS_Critical_Habitat/MapServer>

NOAA polygon and line layers retain provider identity, attributes, designation/proposal
status and citations as separate reference evidence. The 2026-10-10 bounded line query
uses the configured planning envelope [-129.7,45.9,-121.5,51.5], with all 23,514 returned
IDs retained and equal before/after rosters. Existing full geometry pages are reused alongside
new responses; retrieval dates remain distinct. The earlier narrower snapshot is preserved.

Retain NOAA metadata, attribution and source disclaimers. Complete selected IDs are not
complete habitat geography, controlling designation text, a legally effective boundary or
2009–2026 history. NMFS inventory coverage does not establish USFWS or Canadian SARA
coverage. Source date fields remain uninterpreted unless separately qualified; no ecological
response or compliance inference is made. Native companions retain full source-feature/part
relations; engineering-mask intersection and H3 reference overlays remain model-ineligible.

The polygon (226) and line (2) service layers declare `EFFECTDATE` as a string. The
2026-10-14 full-native-envelope receipts contain `MM/DD/YYYY`, compact `YYYYMMDD`
and blanks. The source-specific adapter interprets these formats explicitly, alongside
existing ISO dates; blanks remain unknown and original `NOAA_EFFECTDATE` values are
retained. Invalid calendar dates, undeclared numeric units and field-type drift still fail.
This does not extend the generic date parser or establish historical legal applicability.
NOAA's [rockfish action](https://www.fisheries.noaa.gov/action/designation-critical-habitat-puget-sound-georgia-basin-rockfish)
identifies the same `02/11/2015` effective-date value; its November 2014 publication and
the service's dates such as `03/25/2016` establish the month/day convention. The
[humpback action](https://www.fisheries.noaa.gov/action/final-rule-designate-critical-habitat-central-america-mexico-and-western-north-pacific)
is linked by the service records containing `20210521`. These are publisher reference
dates, not a separate current-law certification.


## Canadian DFO aquatic source added 2026-10-19

The [DFO critical-habitat inventory](https://open.canada.ca/data/en/dataset/db177a8c-5d7d-49eb-8290-31e6a45d786c)
publishes [English layer 0](https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/open_data_donnees_ouvertes/dfo_sara_critical_habitat/MapServer/0)
and a translated French layer 1. Acquire layer 0 once; its original English/French
names and population fields are retained. The translated view is not a second
inventory. Open Government Licence - Canada and DFO attribution apply.

Tyler explicitly approved a bounded addition for the existing full R6/R8 grid
cell envelope. The query returned 23 stable source OBJECTIDs and 506,759 response
bytes, below the 50 MB budget. The selection is [-129.48230286187587,
45.875084185370454, -122.06369308406447, 51.550387523832356] in EPSG:4326.
Whole original source-feature geometry and all attributes survive in OriginalData;
the toolkit makes no national acquisition or complete geographic coverage claim.
No geometry is truncated to the query envelope at acquisition.

There are two marine killer-whale population features and 21 freshwater source
features. Only actual positive-dimensional intersections count on the supplied
grids. Source OBJECTID is namespaced as `dfo_aquatic_critical_habitat:<OBJECTID>`;
multipart geometry contributes one source-feature count per cell. U.S. NMFS and
Canadian SARA identities remain distinct, even when species names overlap. These
are source-feature counts, not unique species, biological populations or habitat
units. Names are never a cross-country identity crosswalk.

All 23 provider records report `CH_STATUS_E=Final/Proposed`. Preserve that literal
mixed label, SARA listing status, population, ecology type, waterbody, comments and
species profile link; do not recode it as final, designated or legally protected.
The source supplies no effective dates for these records. DFO says bounding-box
habitat descriptors are not included, and some records explicitly omit riparian
habitat. Those gaps remain visible in source context. Normalization retains source
geometry unchanged in OriginalData and uses the shared repair/clipping policy for
derived parts; eleven invalid source records require repair, producing 251 parts
from 23 features. Parts are lineage, never additional feature counts.

`selection_bbox` declares this partial source scope in the source configuration.
Receipt validation checks that exact selection, and complete regional coverage is
rejected for bounded partial sources. Other sources retain their default full-AOI
behavior. Generic habitat downloading still refuses unbudgeted acquisition.

The flat family exposes **Critical Habitat Count** and **Critical Habitat
Assignment**. Assignment preserves all names/IDs and paired country/source/status
records, with detailed provider context. Line/point/coverage diagnostics remain
hidden support. Current counts and memberships use the same positive-intersection
contract as NOAA; missing coverage remains null/unknown. This is reference geometry,
not a cross-jurisdiction legal-equivalence or ecological-response claim.

## ECCC marine murrelet reference addition — 2026-10-20

Tyler approved exactly eleven public marine reference areas from ECCC's
[National Critical Habitat Dataset](https://open.canada.ca/data/en/dataset/47caa405-be2b-4e9e-8f53-c478ade2ca74),
[polygon layer 3](https://maps-cartes.ec.gc.ca/arcgis/rest/services/CWS_SCF/CriticalHabitat/MapServer/3).
The final amended [Marbled Murrelet recovery strategy (2023)](https://www.canada.ca/en/environment-climate-change/services/species-risk-public-registry/recovery-strategies/marbled-murrelet-amended-final-2023.html),
sections 7.1.4–7.1.6 and Table 9, identifies these marine areas. They concern adult
breeding-period requirements in the Salish Sea and nearby waters; identification
is partial. Critical habitat occurs only where the required biophysical attributes
are present. These polygons are conditional geographic references, not confirmed
habitat throughout every enclosed cell. `RD_Status=1` is the provider's Posted
Final recovery-document status; it does not establish blanket current legal
protection. Effective dates remain unknown and `MODEL_ELIGIBLE=false`.

| OBJECTID | Marine reference area |
| --- | --- |
| 21704 | Desolation Sound |
| 21707 | Toba Inlet |
| 21709 | Cortes |
| 21710 | Discovery Passage |
| 21711 | Bute Inlet |
| 21712 | Sidney |
| 21715 | Redonda |
| 21716 | Halfmoon |
| 21717 | Queens Reach |
| 21718 | Malaspina |
| 21720 | Savary |

The exact-ID query also requires `COSEWIC_ID=39 AND RD_Status=1`; normalization
checks the species, site name and recovery document. Four terrestrial nesting
records (21706, 21708, 21713, 21714) are excluded. No withheld Northern Abalone
locations or broad inferred habitat polygons are acquired. The existing partial
R6/R8 full-cell envelope remains the declared source selection.

Acquisition returned 11 polygons and 4,178,056 response bytes under the 10 MB /
11-feature cap. The page snapshot SHA-256 is
`72d591b90503b6c4170e3351c7b76beca51b1e2babf35e3af66032e5fa0585ff`;
final receipt time is `2026-10-20T11:06:08.267550+00:00`. Whole original geometry,
all original attributes/codes/nulls, source metadata and per-page receipts are
retained in `OriginalData/eccc_marbled_murrelet_marine_critical_habitat/geometry.parquet`.
One invalid original needs derived polygon repair; the original is unchanged.
All 11 remain 11 normalized parts. ECCC/Parks Canada attribution and the Open
Government Licence – Canada apply.

All 11 IDs intersect both grids: 176 R6 cells and 4,547 R8 cells. Source-qualified
IDs remain distinct from DFO and NOAA identities. Count is the number of
intersecting source reference features, never the number of species or confirmed
habitat sites. Assignment retains source names, IDs, conditional qualifications
and original record codes. Polygon coverage is a geometric source-polygon union
over the full EPSG:6933 H3 denominator; it is not measured ecological habitat area.
An independent original-geometry/H3 check validates every new membership and
affected union fraction. Missing coverage remains unknown, including between
publicly supplied reference areas.

## Public handoff boundary

Source evidence and native processing described here are distinct from public
columns. The [flat product contract](../../../../docs/parquet-products.md) and
[exact physical schema](../../../../docs/reference/columns.md) define delivery.
OriginalData preserves source geometry/attributes and receipt evidence; native
manifests, diagnostic products and unused scientific measures are internal build
support. No source qualification is broadened by the application projection.
