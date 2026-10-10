# Source and quality index

The links below pin the documentation baseline to main
`65fbebb3416673fbd147f4a4d634fa34b8df7679`. Read the notes together with effective
workspace source configuration and retained source receipts. Notes describe source
roles and rights; they do not certify complete geographic coverage, source freshness,
current law or model eligibility. All 15 implemented collections remain research-only.

The [source acceptance inventory](source-acceptance.md) records all 24 families,
all 45 configured sources, expanded-scope qualification gaps and bounded resource
estimates. The [production-readiness inventory](production-readiness.md) records
configured source rights and limitations. Follow the scientific acceptance evidence;
a successful site build does not qualify source coverage. Local study bundles retain
`source-evidence-index.json`, `preflight.json`, metric/native/delivery companions,
`validation.json` and study contracts. They are not publicly hosted by this site.

## Implemented family notes

| Family | Pinned source notes |
| --- | --- |
| `coast_guard_sectors` | [Coast Guard administrative references](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/administrative_context/coast_guard_sectors/DATA_SOURCES.md) |
| `management_areas` | [Fisheries management-area sources](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/fisheries_management/management_areas/DATA_SOURCES.md) |
| `county_regional_boundaries` | [County-equivalent reference inventory](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/jurisdiction/county_regional_boundaries/DATA_SOURCES.md) |
| `federal_waters` | [Federal maritime-zone sources](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/jurisdiction/federal_waters/DATA_SOURCES.md) |
| `international_boundaries` | [International boundaries sources](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/jurisdiction/international_boundaries/DATA_SOURCES.md) |
| `state_provincial_waters` | [State and provincial waters sources](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/jurisdiction/state_provincial_waters/DATA_SOURCES.md) |
| `tribal_first_nations_areas` | [Official provider administrative references](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/jurisdiction/tribal_first_nations_areas/DATA_SOURCES.md) |
| `conservation_designations` | [ECCC reported marine classifications](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/protected_areas/conservation_designations/DATA_SOURCES.md) |
| `marine_protected_areas` | [Marine protected-area sources](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/protected_areas/marine_protected_areas/DATA_SOURCES.md) |
| `national_marine_sanctuaries` | [NOAA national marine sanctuaries](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/protected_areas/national_marine_sanctuaries/DATA_SOURCES.md) |
| `wildlife_refuges` | [Selected wildlife-refuge reference inventory](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/protected_areas/wildlife_refuges/DATA_SOURCES.md) |
| `shipping_lanes` | [Typed CHS / NOAA routing references](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/vessel_management/shipping_lanes/DATA_SOURCES.md) |
| `traffic_separation_schemes` | [Typed CHS / NOAA routing references](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/vessel_management/traffic_separation_schemes/DATA_SOURCES.md) |

Two implemented families currently have no `DATA_SOURCES.md`: their code and
configured provenance are the available baseline references, pending source-owner notes.

- `critical_habitat`: [normalizer](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/protected_areas/critical_habitat/normalize.py), [build](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/protected_areas/critical_habitat/build.py).
- `ports`: [normalizer](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/administrative_context/ports/normalize.py), [build](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/src/governance/administrative_context/ports/build.py).

See [configured source definitions](https://github.com/MarineCast/toolkit-governance/blob/65fbebb3416673fbd147f4a4d634fa34b8df7679/config/data/governance/governance.yaml)
for snapshot paths, authority scope, rights, query support and missingness.
The critical-habitat study checkpoint retains an old line-query footprint; ports
are point references. Neither constitutes complete designation or port-footprint coverage.

## Unavailable families and acceptance

The nine catalog families still unavailable at this checkpoint are seasonal closures,
gear restrictions, harvest regulations, salmon management zones, exclusion zones,
speed restriction zones, whale approach regulation zones, management regions and
reporting areas. An existing management-area polygon does not implement all fisheries
systems. Regulatory products require qualified applicability, instruments and independent
effective/knowledge-time history. Geometry labels and acquisition dates cannot supply those.

A practical acceptance review checks source roster/scope and rights, snapshot identity,
query support, native attributes/part identities, geometry diagnostics, empty-intersection
semantics, temporal limitations, overlay/delivery correspondence and final release validation.
Configured-source receipt fractions are not geographic completeness denominators.
Keep unknown/unavailable/partial support distinct from observed absence; retain native
companions for precise record relationships. See [contracts](CONTRACTS.md),
[H3 methodology](h3-matrix.md) and [study acceptance](study-guide.md#acceptance-and-recovery).
