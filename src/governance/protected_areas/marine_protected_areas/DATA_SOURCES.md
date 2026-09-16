# Marine protected-area sources

This producer combines two deliberately different source roles. NOAA's MPA
Inventory is used for U.S. discovery and reference metadata. DFO's Oceans Act
services provide Canadian designated-MPA reference polygons and separate Area of
Interest points. Neither source is silently promoted above the governing legal
instrument.

## United States: NOAA MPA Inventory

The [NOAA MPA Inventory](https://marineprotectedareas.noaa.gov/dataanalysis/mpainventory/)
is a national reference compilation of existing MPAs. The toolkit pins NOAA's exact
2023 geodatabase archive, preserves it unchanged, and clips its combined polygon
layer locally to `full_area`. The live service's bounded spatial query was
evaluated but timed out on its highly detailed national geometry, so it is not
the release acquisition path. The archive retains source site ID, management
agency, agency/site URL, establishment year, conservation purpose, protection
classification, management-plan status, permanence, constancy, and
fishing/vessel/anchoring restriction classifications.

NOAA states that the inventory is dynamic reference information, is not a legal
document, and is not better than the original contributing sources. Therefore:

- `MANAGEMENT_AUTHORITY` and a deterministic `AUTHORITY_ID` identify the source
  agency recorded for each site.
- `GOVERNING_RULE_CITATION` records the applicable program framework.
- `GOVERNING_RULE_STATUS` remains
  `program_framework_only_site_rule_not_in_inventory` until the site-specific
  proclamation, CFR provision, state rule, establishment instrument, or approved
  management plan is verified from the managing agency.
- Inventory protection classifications remain reference metadata. They are not
  treated as legal activity rules or converted to a score.

The canonical output includes every polygon in the pinned official archive that
intersects configured `full_area`. This is complete for the acquired archive,
not a claim that every legally protected U.S. marine site has current GIS in the
inventory.

## Canada: DFO Oceans Act sources

The [DFO Oceans Act MPA dataset](https://open.canada.ca/data/en/dataset/a1e18963-25dd-4219-a33f-1a38c4971250)
publishes designated MPA polygons, zone names, site URLs, regulation titles, and
source areas. DFO says these GIS boundaries are visual representations only;
official regulation coordinates control. The toolkit retains that status and the
feature regulation citation.

The separate [DFO Oceans Act Areas of Interest service](https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/open_data_donnees_ouvertes/oceans_act_areas_of_interest_sites_dinteret_de_la_loi_sur_les_oceans/MapServer)
publishes points rather than proposed boundaries. Those native points are
published separately with `DESIGNATION_STATUS=area_of_interest`; no area is
buffered or inferred.

## Activity and IUCN fields

Allowed/prohibited activities and IUCN reporting categories are retained only
when explicitly sourced. NOAA's archive supplies an `IUCNcat` reference value,
which is retained as `IUCN_REPORTING_CLASS` with inventory-reference status; DFO's
selected spatial layers do not supply a comparable site category. Neither source
provides complete site-level legal activity rules. NOAA's fishing, vessel, and
anchoring classifications are preserved in their own reference fields and are
not reinterpreted as exact allowed/prohibited activities.

## Outputs

- `marine_protected_areas.parquet`: canonical full-AOI native geometry
- `mpa_designation_polygons.parquet`: designated/reference MPA polygons
- `area_of_interest_geometry.parquet`: non-designated native AOI points
- `source_authority_evaluation.json`: U.S. authority and governing-rule gap audit
- `manifest.json`: source snapshots, retrieval times, checksums, clipping,
  designation counts, and no-score policy
