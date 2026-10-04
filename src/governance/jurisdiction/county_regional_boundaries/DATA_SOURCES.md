# County-equivalent reference inventory

Source: [2025 Census TIGER/Line counties](https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip).
[Census vintage documentation](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
states a 2025-01-01 boundary/name reference date. The original ZIP includes XML metadata and
NAD83 projection; it is retained unchanged with SHA-256 and retrieval receipt.

`download county_regional_boundaries` explicitly caps the archive at 100,000,000 bytes and checks
the configured SHA-256. Existing files are reused with checksum validation; failed bounded
replacement leaves the previous file intact. `build ... --allow-partial` reads the local archive,
transforms NAD83 to WGS84, retains all source attributes under `CENSUS_`, and applies the shared
native AOI clipping without changing source geometry through map simplification.

The five-digit `GEOID` retains leading zeros and is namespaced by source vintage. These are
Census statistical/cartographic county-equivalent representations, including Alaska equivalents.
U.S. Census Bureau attribution and original metadata accompany local outputs. No independently
current legal boundary, legal effective date, administrative power, offshore jurisdiction, or
Canadian regional district is inferred. Canadian coverage is unavailable, never observed zero.
`MODEL_ELIGIBLE` remains false; empty overlay cells stay null without authoritative absence support.
