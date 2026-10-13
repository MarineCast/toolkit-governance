# Regional availability and source qualification

The software supports bounded native/H3 queries; regional source acceptance is a separate
question. `governance availability` emits 408 layer/provider/region rows with separate
implementation, acquisition completeness, geographic completeness, legal-currentness,
geometry type, temporal capability, source vintage, rights and limitations. The same
versioned matrix ships as `governance/resources/availability.json`. Runtime query results
add actual request receipts; the static matrix never claims an acquired roster is complete.

| Region | Qualified software/source additions | Remaining evidence |
| --- | --- | --- |
| Central/mid-Oregon | Pinned ODFW published 2016 native boundaries; NOAA discovery inventory | Current designation instruments, full source roster and Oregon fishery vectors |
| Washington | WDFW recreational identity retained; NOAA/source reference families | Commercial/species-specific rosters, legal applicability/history |
| Southern BC | DFO designated inventories; TC 2026 Saturna/Pender and Swiftsure coordinate rings | Nitinat authoritative coastline; other instruments/systems; legal-currentness |
| Northern BC | Query-capable DFO/NRCan/ECCC qualified provider systems | DFO whole-area/current applicability, provincial marine inclusion taxonomy and legal applicability |
| Southeast Alaska | Bounded ADF&G groundfish statistical adapter | Other fisheries/protected-system rosters and fresh regional receipt acceptance |
| Gulf of Alaska | Same distinct reporting system | Independent regional geometry/completeness and current instrument evidence |
| Aleutians/dateline | Split queries, split native geometries and exact generic H3 cells | Provider-by-provider positive-longitude support and full-system regional acceptance |
| Arctic Alaska | Synthetic geometry/API fixture only | Qualified provider roster, acquisition/geometry support, source terms and instruments; groundfish layer extent alone is insufficient |

All output remains model-ineligible research reference. Source-query completeness is
neither a geographic denominator nor legal-currentness. Dates in geometry inventories are
not automatically the dates that a rule came into force. Traditional territories/treaties/
fishing rights cannot be inferred from BIA land references or NRCan reserves.

## Sources checked on 2026-10-13

The official [ODFW coordinates/download page](https://oregonmarinereserves.com/rules/)
provides the independently pinned 20,803-byte 2016 archive. Inspection found 14 original
placemarks with multipart geometry; current OARs remain a separate legal authority. The
[ADF&G service metadata](https://gis.adfg.alaska.gov/mapping/rest/services/CF_public/Groundfish/MapServer/3?f=pjson)
declares polygon geometry, original statistical codes, geometry dates, supported queries,
a dateline-spanning extent ending about 68.5 N and restrictions on reproduction/distribution.
No national source download or public dataset redistribution accompanies this work.

The [TC 2026 instrument](https://tc.canada.ca/en/interim-order-protection-killer-whale-orcinus-orca-waters-southern-british-columbia)
supplies two closed vessel-zone rings and one closed Swiftsure speed ring. Its Nitinat
boundary follows the coastline, which requires separately pinned support. The official
[DFO Pacific area maps](https://www.pac.dfo-mpo.gc.ca/fm-gp/maps-cartes/areas-secteurs/index-eng.html)
led to the official Pacific `DFO_BC_PFMA_SUBAREAS_50K_V3_1/MapServer/0` service. Its subarea polygon hierarchy is now implemented separately, retaining MGNT_AREA, SUBAREA_, OBJECTID and GLOBALID. Metadata copyright/licence fields are blank: local reference inspection is supported, while dataset redistribution, whole-area/legal applicability and historical qualification remain unresolved. [BC Parks/Tantalis](https://catalogue.data.gov.bc.ca/dataset/bc-parks-ecological-reserves-and-protected-areas)
is a park/eco-reserve/protected-area inventory; mapping every park to a marine designation
would change meaning and is not implemented. Existing ECCC marine classifications remain
separate provider evidence.

Each blocked matrix row identifies the missing input. Proposed or unresolved geometry is
never manufactured to fill the coverage checklist. Historical local study releases and
source-acceptance notes retain their original counts, pins and acceptance boundaries;
this software hardening does not activate or recertify them.
