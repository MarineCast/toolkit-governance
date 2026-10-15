# NOAA NMFS habitat reference inventories

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
