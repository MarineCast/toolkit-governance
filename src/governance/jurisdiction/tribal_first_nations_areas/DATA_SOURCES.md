# Official provider administrative references

## BIA AIAN National LAR

Primary service: https://biamaps.geoplatform.gov/server/rest/services/DivLTR/BIA_AIAN_National_LAR/FeatureServer/0
Provider context: https://www.bia.gov/service/tribal-consultations/bia-data-governance-bia-open-data-and-bia-tract-viewer

Use original LARID for provider area identity and OBJECTID for original source record identity.
Keep all BIA-prefixed source fields, including undecoded CLASSIFICATION. Do not infer traditional
territory, all interested Tribes, sovereign jurisdiction, land ownership or treaty fishing rights.
BIA metadata permits public reference use subject to its limitations; retain complete metadata
and acquire directly from BIA. The source is not suitable for legal, survey, engineering or
navigation use. Snapshot receipts do not establish source vintage or legal effective dates.

## NRCan CLSS Indian Reserve records

Primary service: https://proxyinternet.nrcan-rncan.gc.ca/arcgis/rest/services/CLSS-SATC/CLSS_Administrative_Boundaries/MapServer/0
Catalogue: https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067
Licence: https://open.canada.ca/en/open-government-licence-canada

The qualified first subset requires distributionTypeEng=Indian Reserve and
jurisdictionEng=British Columbia. Sechelt Land and other classes are not folded into this subset.
Retain adminAreaId, original OBJECTID and all NRCAN-prefixed fields. Provider representationPurpose
values, including Legal, remain raw attributes and never override canonical reference status.
Modified local geometry must retain attribution/licence and no-endorsement qualifications.

## Provisioning and delivery

Provision explicitly bounded complete source snapshots with fresh exact-grid ID rosters and
page receipts. The download wrapper refuses implicit nationwide acquisition. The selected
application-grid features preserve full native source geometry before established AOI clipping;
partial support never establishes absence outside received features. Distinct source groups have
no pooled territory metric. Published local generations must retain raw snapshots, metadata and
rights evidence, native feature/part relations, metric dictionary and independent overlay checks.
