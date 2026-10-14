# Governance 0.2.1 correction handoff

Work started from fetched `codex/governance-hardening` at
`091396409a03b8f8b5f7eac9c7f1a7d53b41d471`; local and remote tips matched and the
working tree was clean. The changes affect toolkit-governance only.
Implementation commit: `46fd5c5de99e3ea0e086f822401509bab901d7f1`; the subsequent
documentation commits contain this validation handoff.

## Finding dispositions

| Finding | Disposition and correction |
| --- | --- |
| Mixed intersection collections dropped | Fixed: recursively retain original-dimension components, union them once per native part and keep one cell/source/part membership. Polygon/line boundary-only contacts remain excluded; point-boundary policy and source/proposal groups stay intact. |
| Repair fractions mixed units | Fixed: original-family repaired support supplies the denominator; retained parts supply the same-unit numerator. Canonical dateline splitting supplies consistent geodesic vertices. Remnant and repair-delta diagnostics remain separate. Finite/range failures raise; only bounded roundoff is snapped. |
| Receiptless ZIP qualification | Fixed: receipts required by default; the explicit immutable full-source contract plus verified configured pin permits qualified legacy ZIPs only. Existing bad receipts cannot fall back. Local override acquisition also validates receipts. Direct downloads reject selectors/masks they cannot apply; handled refresh failures restore cache and metadata. |
| DFO zero subarea | Confirmed in the configured live source and fixed: six published zero-subarea codes qualify, including 21-0. Management areas remain strictly positive; new zero-area pairs require qualification. Null/malformed/negative/fractional/Python or NumPy boolean identifiers fail. |
| Getter producer provenance | Added package/version and explicit nullable revision from matching installed VCS metadata only. No Git runtime dependency or unrelated-cwd revision guess. |
| Fisheries docs | Current WDFW, DFO and ADF&G adapter support precedes historical Phase 1 limitations. |

## Files and compatibility

- `shared/query_overlay.py`: dimension extraction before membership/union metrics.
- `shared/spatial.py`: explicit-family measurements, original-dimension fractions,
  dateline-split denominator, recursive remnant detection and error checks.
- `shared/acquisition.py`: receipt qualification, local overrides, malformed/member
  mismatch failures, validation before vector parsing and direct selector enforcement.
- `shared/config.py` and both governance YAML copies: optional strict boolean
  `immutable_full_source_archive` (default false). Twelve existing official pinned
  ZIP source contracts declare it: Census counties, IBC, two NRCan CGB members,
  six NOAA ONMS archives, NOAA MPA inventory and ODFW. The immutable identity is the
  configured checksum; an upstream URL may change, in which case acquisition fails.
  Archive/member inventory scope is distinct from regional/legal completeness.
- `management_areas/pacific.py` and its source notes: qualified identifier behavior;
  no provider geometry or bulk dataset fixture committed.
- `query.py`, `shared/artifacts.py`, package metadata: package 0.2.1, rebuild method
  `native-reference-2.1`, query method `native-reference-query-2.1`. The query result
  schema stays version 1 with additive producer provenance. Revision is null/unavailable
  for ordinary wheels and editable/source runs without matching immutable VCS metadata.
- `tests/test_hardening_corrections.py`, adjusted regional invalid-subarea control,
  `scripts/accept_corrections_wheel.py`: regressions and reproducible wheel smoke.
- Contracts, workflow/query/H3/layer/readiness docs, previous handoff link and MkDocs
  navigation: current behavior, version boundary and validation evidence.

Getter signatures, native schema, rights, identities and model-ineligible defaults are
preserved. Existing source pins are unchanged. Old configurations without the new flag
still load but receiptless archives fail until explicitly qualified or properly receipted.
Configurations declaring the new flag require 0.2.1; older strict loaders reject that key.
No receipt/completeness evidence is manufactured for legacy bytes. No historical product
or release is rebuilt/relabelled; legacy H3 projected length and point-feature counting
remain unchanged.

## Reproduction and regression evidence

Before implementation, the initial tests produced **8 failed, 4 passed**: polygon+line,
polygon+point and line+point intersection memberships were discarded; hole/multipart
fragments were discarded; fully retained and clipped repaired polygons mixed dimensions;
unpinned and pin-only receiptless ZIPs were accepted.

A read-only archive of the reviewed commit, tested with the expanded regressions, produced
**15 failed, 4 passed, 30 deselected**. This additionally proves the actual-H3 public getter
case and all six DFO zero identifiers fail on the original code. The fixed expectations use
independent EPSG:6933 projections of known polygon shapes and Geod endpoint calculations,
not the producer's measure helper. A targeted legacy comparison checks only equal-area
polygon union and distinct feature counts on identical support (relative tolerance 1e-8).
Point counting, projected/geodesic length and legacy dateline differences are deliberately
not forced into parity.

The new tests also cover nested collections, holes, multipart fragments, null/boundary-only
contacts, part grain and budgets, finite fractions/error rejection, repair diagnostics,
compatible/narrow/malformed/mismatched receipts, selector/mask conflicts, pins, local
acquisition overrides, refresh rollback, actual H3 cells and query/source time separation.

## DFO evidence

Official service and layer metadata and two bounded identifier queries were retrieved
2026-10-14 00:42 UTC (2026-10-13 America/New_York). No geometry was requested. Integer
MGNT_AREA and SUBAREA_ fields have null domains; no coded type metadata establishes a sentinel.
`SUBAREA_ = 0` returned six named/labelled records without transfer-limit indication.
The raw pairs are `(103,0)`, `(109,0)`, `(110,0)`, `(21,0)`, `(22,0)`, `(111,0)`.
Record 461 has `MGNT_AREA=21`, `SUBAREA_=0`, NAME `Subarea 21-0`, LABEL `21-0`,
GLOBALID `{422E68F7-5258-4270-BC80-D586220A6B0C}`. A separate query for nonpositive
management areas, negative subareas and null identifiers returned no records.

The [exact GIS layer](https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/Pacific/DFO_BC_PFMA_SUBAREAS_50K_V3_1/MapServer/0)
and [official 2026 guidance](https://www.pac.dfo-mpo.gc.ca/fm-gp/mammals-mammiferes/whales-baleines/srkw-measures-mesures-ers-eng.html)
independently identify 21-0. Therefore zero is a qualified provider subarea identifier,
not null/unknown. NAME `Subarea 111` versus LABEL `111-0` is preserved without reinterpreting
hierarchy or synthesizing whole-area polygons. The complete six-row attribute summary is
in the [source notes](https://github.com/MarineCast/toolkit-governance/blob/codex/governance-hardening/src/governance/fisheries_management/management_areas/DATA_SOURCES.md).
Blank service rights, geographic completeness and current legal applicability remain unqualified.
Offline fixtures use synthetic geometry and UUIDs; temporary evidence stays local.

## Validation

All final checks passed on macOS 26.6.2 arm64. Python 3.14.6 uses the clean provisioned
native/H3 environments; Python 3.11.16 uses a new wheel environment sharing provisioned
third-party dependencies. The latter is not a clean dependency-closure claim. H3 is
physically absent from the 3.14 native environment. Every wheel smoke runs from `/tmp`,
verifies the installed package location, blocks OrcaCast/application imports, imports all
17 families, checks resource/default parity and uses a new synthetic workspace.

| Final check | Observed result |
| --- | --- |
| New focused regressions, Python 3.14 | 53 passed, 0 failed/skipped; 6.75 s |
| Full offline suite, Python 3.14 source | 158 passed, 2 skipped; 31.36 s |
| Full offline suite, Python 3.11 installed wheel | 158 passed, 2 skipped; 35.60 s |
| Native wheel/import/getter, no H3 (3.14) | Passed; 1 feature / 2 native parts; H3 request raises ImportError |
| H3 wheel/import/getter (3.14 and 3.11) | Passed; each returns 1 feature, 2 native parts, 3 R7 cells, 4 positive memberships |
| `pip check`, all three wheel environments | No broken requirements found |
| Native installed CLI help/catalog/preflight/availability/offline getter | Passed; missing operational inputs remain unavailable in preflight |
| Configuration/resource/wheel byte parity | 10 config files identical; 168 package files match the final wheel; all source pins unchanged |
| Strict MkDocs build and `git diff --check` | Passed |

The two skips are the opt-in Alaska and Pacific live getter smokes, not failed or certified
regional checks. The DFO identifier investigation above actually ran separately. Python 3.14
reports 26 non-failing warnings: independent/legacy Shapely transform deprecations and upstream
CartoDB key warnings. Python 3.11 reports 2 upstream CartoDB warnings. Dependency versions for
3.14 include GeoPandas 1.2.0, pandas 3.0.6, Shapely 2.2.0 and H3 4.5.0; 3.11 uses Shapely 2.1.2.
Other operating systems/interpreters were not tested.

Final wheel: `toolkit_governance-0.2.1-py3-none-any.whl`, 258,786 bytes, SHA-256
`49018ca65e4eea65c3d106b276c05faa50f26ddb2b62e5d01db8f566c304bedd`.
After the full suites, only a source-notes sentence was clarified; package code is unchanged.
The wheel was rebuilt and all three outside-checkout acceptance/pip checks were repeated.
An initial no-isolation build in the lean 3.14 runtime lacked setuptools; rebuilding with
already provisioned Python 3.11 setuptools succeeded. No runtime dependency or source pin
was changed to overcome that tooling limitation.

These are the exact commands used for final acceptance (use new workspace paths when rerunning):

```sh
# Run from the owner checkout unless a cd is shown.
PYTHONPATH=src /tmp/governance-hardening-h3/bin/python -m pytest -q tests/test_hardening_corrections.py
PYTHONPATH=src /tmp/governance-hardening-h3/bin/python -m pytest -q
/tmp/governance-corrections-311-env/bin/python -m pytest -q
/Users/tylerstevenson/Documents/Codex/2026-10-03/pl/work/viewshed311/bin/python -m pip wheel . --no-deps --no-build-isolation --wheel-dir /tmp/governance-corrections-dist
/Users/tylerstevenson/Documents/Codex/2026-10-03/pl/work/viewshed311/bin/python -m venv --system-site-packages /tmp/governance-corrections-311-env
/tmp/governance-hardening-native/bin/python -m pip install --no-deps --force-reinstall /tmp/governance-corrections-dist/toolkit_governance-0.2.1-py3-none-any.whl
/tmp/governance-hardening-h3/bin/python -m pip install --no-deps --force-reinstall /tmp/governance-corrections-dist/toolkit_governance-0.2.1-py3-none-any.whl
/tmp/governance-corrections-311-env/bin/python -m pip install --no-deps --force-reinstall /tmp/governance-corrections-dist/toolkit_governance-0.2.1-py3-none-any.whl

cd /tmp
/tmp/governance-hardening-native/bin/python /Users/tylerstevenson/Documents/Code_Repos/MarineCast/Toolkits/toolkit-governance/scripts/accept_corrections_wheel.py /tmp/governance-corrections-native-review
/tmp/governance-hardening-h3/bin/python /Users/tylerstevenson/Documents/Code_Repos/MarineCast/Toolkits/toolkit-governance/scripts/accept_corrections_wheel.py /tmp/governance-corrections-h3-review --h3
/tmp/governance-corrections-311-env/bin/python /Users/tylerstevenson/Documents/Code_Repos/MarineCast/Toolkits/toolkit-governance/scripts/accept_corrections_wheel.py /tmp/governance-corrections-311-review --h3
/tmp/governance-hardening-native/bin/python -m pip check
/tmp/governance-hardening-h3/bin/python -m pip check
/tmp/governance-corrections-311-env/bin/python -m pip check
/tmp/governance-hardening-native/bin/governance --help
/tmp/governance-hardening-native/bin/governance --workspace /tmp/governance-corrections-native-review catalog
/tmp/governance-hardening-native/bin/governance --workspace /tmp/governance-corrections-native-review preflight
/tmp/governance-hardening-native/bin/governance --workspace /tmp/governance-corrections-native-review availability
/tmp/governance-hardening-native/bin/governance --workspace /tmp/governance-corrections-native-review get fishery-management-areas --bbox -123.01 48.49 -122.99 48.51 --source wdfw_recreational_marine_areas --mode offline --allow-partial

cd /Users/tylerstevenson/Documents/Code_Repos/MarineCast/Toolkits/toolkit-governance
/tmp/governance-hardening-native/bin/python -m mkdocs build --strict --site-dir /tmp/governance-corrections-site
git diff --check
```

The configuration parity/pin check used the following independent read-only assertions:

```python
from pathlib import Path
import subprocess, yaml, zipfile
repo = Path.cwd()
paths = sorted(p for p in (repo / "config").rglob("*") if p.is_file())
with zipfile.ZipFile("/tmp/governance-corrections-dist/toolkit_governance-0.2.1-py3-none-any.whl") as wheel:
    for path in paths:
        relative = path.relative_to(repo / "config")
        assert path.read_bytes() == (repo / "src/governance/resources/config" / relative).read_bytes()
        assert path.read_bytes() == wheel.read("governance/resources/config/" + relative.as_posix())
old = yaml.safe_load(subprocess.check_output(["git", "show", "0913964:config/data/governance/governance.yaml"]))["sources"]
new = yaml.safe_load((repo / "config/data/governance/governance.yaml").read_text())["sources"]
assert {k: v.get("expected_sha256") for k, v in old.items()} == {k: v.get("expected_sha256") for k, v in new.items()}
```

The bounded offline R7 multipart smoke recorded 0.1069 s (3.14) and 0.1023 s (3.11),
with 3 cells / 1 logical feature / 2 native parts / 4 memberships and zero network bytes.
These are single small engineering samples, not regional speedup claims.


## Merge readiness and limits

The three correctness findings are fixed and DFO zero-subarea behavior is resolved for
the configured source version. Recommend merge after ordinary review and hosted CI.
These engineering checks do not establish full regional completeness, historical/legal
reconstruction or production certification. Full regional rebuilds, historical-release
recertification, legal-currentness review, source redistribution approval and browser map
visual QA were not run. Production data/releases are untouched; no merge, tag, release
activation or dataset publication is authorized by this work.
