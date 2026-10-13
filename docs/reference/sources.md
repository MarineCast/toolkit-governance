# Sources and rights

The software is Apache-2.0. Source datasets have separate licenses, attribution,
disclaimers, and redistribution terms. The table summarizes **configured source
roles**, not a new check of provider availability or legal currency.

Exact source URLs, archive pins/members, vintages, citations, and regional coverage
are maintained in
[`governance.yaml`](https://github.com/MarineCast/toolkit-governance/blob/main/config/data/governance/governance.yaml).
Built manifests add raw checksums and retrieval information where available.

| Source | Collections | Role and rights considerations |
| --- | --- | --- |
| NOAA MPA Inventory, pinned 2023 geodatabase | Marine protected areas | U.S. discovery/reference compilation; retain contributing management authority and governing-rule gaps |
| DFO Oceans Act MPA service | Marine protected areas | Visual designated-MPA/zone polygons with regulation citations; regulation coordinates control |
| DFO Areas of Interest service | Marine protected areas | Native interest points, not designated areas or proposed boundary polygons |
| NOAA ONMS pinned boundary archives | National marine sanctuaries | Configured six-site West Coast GIS roster; retain source vintages, authority records, and legal/navigation disclaimers |
| IBC digital boundary v1.3 archive | International boundaries | Mapping reference; preserve attribution, section scale, and the mapping-only disclaimer |
| NOAA U.S. maritime services/local vector | International boundaries; federal waters | Reference limit lines; retain NOAA attribution and feature-specific citations, without promoting GIS to controlling authority |
| Archived NRCan GeoBase CGB Level 1 | International boundaries; federal waters | Archived cartographic geometry with source agency, status, dates, and accuracy where available |
| Local DFO Federal Marine Bioregions | International boundaries | Ecosystem-planning support with fuzzy boundaries, not international-boundary authority |
| Provisioned seascape water-support GeoParquet | International boundaries | Derived spatial support; retain upstream rights/provenance, including historical producer labels |
| BOEM/BSEE Submerged Lands Act boundary service | State/provincial waters | State seaward reference line; controlling official coordinates remain distinct |
| WDFW Recreational Marine Area Code service | Management areas | One Washington recreational management system; retain source identity and rule reference |
| DFO Pacific Fishery Management Area references | Management areas | Reference-only configured entry; no pinned machine-readable geometry input |
| NOAA NMFS habitat polygon/line snapshots | Critical habitat | Provision bounded receipts; designation/proposal evidence is separate from complete current legal coverage |
| FWS NWR and selected ECCC CPCAD records | Wildlife refuges | Selected systems only; retain source domain metadata, attribution, and reference limitations |
| ECCC marine CPCAD class/status records | Conservation designations | Qualified classification views overlap existing evidence; do not sum as incremental protected coverage |
| Census TIGER/Line 2025 counties | County/regional boundaries | Statistical/cartographic U.S. county equivalents, not Canadian coverage or current administrative authority |
| BIA LAR and selected NRCan CLSS reserves | Tribal/First Nations catalog family | Distinct administrative reference systems; no inferred traditional territory, sovereignty, title, or fishing rights |
| CHS routing and NOAA2026 routing references | Shipping lanes; traffic-separation schemes | Typed provider/component roles; retain original object/chart identity and planning/navigation disclaimers |
| NGA World Port Index | Ports | Physical points with original fields/coordinates; no port jurisdiction polygon |
| USCG sectors and CCG Western-region references | Coast Guard | Different agency unit types; retain source-specific rights and redistribution qualifications |

## Family source notes

The repository keeps detailed source and authority notes beside each producer:

- [Marine protected areas](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/marine_protected_areas/DATA_SOURCES.md)
- [National marine sanctuaries](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/protected_areas/national_marine_sanctuaries/DATA_SOURCES.md)
- [International boundaries](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/international_boundaries/DATA_SOURCES.md)
- [Federal maritime zones](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/federal_waters/DATA_SOURCES.md)
- [State and provincial waters](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/jurisdiction/state_provincial_waters/DATA_SOURCES.md)
- [Fisheries management areas](https://github.com/MarineCast/toolkit-governance/blob/main/src/governance/fisheries_management/management_areas/DATA_SOURCES.md)

Additional implemented family notes are linked from [layers](../layers.md).
The [source quality index](../sources.md) retains its pinned baseline;
[source acceptance](../source-acceptance.md) records retained study evidence and
remaining qualifications. Source configurations and built manifests govern the
inputs used by a selected workspace.

## Reading provenance

Keep **source vintage**, **retrieval time**, **effective dates**, **learned time**,
and **build time** separate. A fresh download does not make an archived geometry
new, and a new build does not establish current law. Family attributes and
manifests retain these distinctions rather than assigning a single universal
"as of" date.

Before distributing any raw snapshot or derived artifact, inspect the source's
`license`, `attribution`, `redistribution`, `legal_citation`, and `limitation`
records in its manifest. Preserve citations and qualification when consuming
or displaying products. Software licensing alone does not establish dataset
redistribution permission.

See [layers](../layers.md) for file inventories and
[limitations](../limitations.md) for interpretation boundaries.
