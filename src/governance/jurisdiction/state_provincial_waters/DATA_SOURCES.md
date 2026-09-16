# State and provincial waters sources

Phase 1 acquires the BOEM Submerged Lands Act (state seaward) boundary line from
the national BOEM/BSEE ArcGIS layer and clips it to `full_area`.

- Service: <https://gis.boem.gov/server/rest/services/BOEM_BSEE/MMC_Layers/MapServer/8>
- Legal context: Submerged Lands Act, 43 U.S.C. 1301-1315.
- Limitation: BOEM states that controlling coordinates are on official OPDs and
  SOBDs. The GIS line is not converted to a state-water polygon.

British Columbia marine administrative applicability is not assumed equivalent
to U.S. state waters. Provincial-water geometry remains unavailable.
