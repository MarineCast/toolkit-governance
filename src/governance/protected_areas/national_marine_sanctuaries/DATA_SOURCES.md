# NOAA national marine sanctuaries

This collection publishes the six current NOAA Office of National Marine
Sanctuaries (ONMS) boundaries intersecting the toolkit's `full_area`: Channel
Islands, Chumash Heritage, Cordell Bank, Greater Farallones, Monterey Bay, and
Olympic Coast.

## Geometry sources

The source roster and individual zipped shapefiles come from the official
[ONMS GIS data page](https://sanctuaries.noaa.gov/library/imast_gis.html). Each
download is checksum-pinned in `config/data/governance/governance.yaml`; raw
archives are retained unchanged and normalized polygons are clipped to
`full_area`.

| Sanctuary | Archive geometry vintage | Current legal boundary |
| --- | --- | --- |
| Channel Islands | 2008-06-18 | [15 CFR part 922 subpart G](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-G) |
| Chumash Heritage | 2024-12-02 | [15 CFR part 922 subpart V](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-V) |
| Cordell Bank | 2015-06-10 expanded boundary | [15 CFR part 922 subpart K](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-K) |
| Greater Farallones | 2015-06-10 expanded boundary | [15 CFR part 922 subpart H](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-H) |
| Monterey Bay | 2014-09-12 | [15 CFR part 922 subpart M](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-M) |
| Olympic Coast | 2004-12 | [15 CFR part 922 subpart O](https://www.ecfr.gov/current/title-15/subtitle-B/chapter-IX/subchapter-B/part-922/subpart-O) |

ONMS metadata states that these GIS files represent sanctuary boundaries but
are not for legal or navigational use. The current CFR boundary descriptions and
coordinates control. The pipeline therefore stores the GIS geometry as mapped
evidence, emits separate authority records, and never infers rules from polygon
membership.

## Designation and boundary history

- Channel Islands was designated September 22, 1980 (`45 FR 65198`).
- Chumash Heritage became effective November 30, 2024; the final rule is
  [`89 FR 83554`](https://www.federalregister.gov/d/2024-23607).
- Cordell Bank was designated May 24, 1989 (`54 FR 22417`) and expanded north
  and west effective June 9, 2015.
- Greater Farallones was designated January 16, 1981 (`46 FR 7936`), expanded
  in 2015, and renamed from Gulf of the Farallones.
- Monterey Bay was designated September 18, 1992 (`57 FR 43310`) and expanded
  to include Davidson Seamount in 2008.
- Olympic Coast became effective July 22, 1994 (`59 FR 24586`); boundary
  coordinate corrections followed in 1995.

The [ONMS Federal Register notice registry](https://sanctuaries.noaa.gov/management/fr_notices.html)
is the amendment-history discovery source. The eCFR and official Federal
Register editions remain controlling.

## Outputs

- `national_marine_sanctuaries.parquet`: canonical full-AOI native geometry,
  retaining separate source polygon parts and overlapping sanctuaries
- `sanctuary_authority_records.json`: one non-spatial designation and authority
  record per current sanctuary
- `manifest.json`: source snapshots, retrieval times, checksums, geometry-part
  counts, source vintages, roster completeness, and area-QC policy
