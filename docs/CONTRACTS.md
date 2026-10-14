# Governance product contracts

The [public output contract](parquet-products.md) is one static and optional dated metric
Parquet per supplied resolution, a small update catalog, and OriginalData per dataset.
There are no governance data releases or public manifest sidecars. Native normalization
products described below are temporary build intermediates.

The extraction preserves the original scientific calculations and source-specific distinctions.
Internal native GeoParquet uses EPSG:4326. `GOVERNANCE_FEATURE_ID` identifies a source-backed feature;
`GEOMETRY_PART_ID` is unique within each artifact and distinguishes clipped parts. Do not join
by row order or hide duplicates. Native intermediates contain no H3 fields. Public metric tables use the explicitly supplied H3 grid.

Geometry remains native points/lines/polygons as appropriate. Shared clipping handles the
antimeridian and preserves source bounds, retained geometry type, measure fraction and diagnostics.
Map simplification is presentation-only and does not replace canonical data. Report unavailable
comparison geometry instead of inventing jurisdiction boundaries. Derived country-water support
is not controlling legal geometry.

`EFFECTIVE_START`/`EFFECTIVE_END`, `SYSTEM_LEARNED_AT`, `SOURCE_VINTAGE`, retrieval and build times
have different meanings. The inherited map date filter includes both effective endpoints and
allows unknown dates through; it is an inspection aid, not proof of legal applicability at a date.
Preserve source citations, authority scope, legal-binding status and limitations. DFO areas of
interest are distinct from designated MPAs; cartographic references are distinct from controlling
legal coordinates. Source documents remain authoritative.

Coverage distinguishes complete, partial, unavailable, unknown and not applicable. Missing source
coverage is never observed absence or zero. Measurement states distinguish observed, derived,
estimated, fallback and unavailable. Partial builds require explicit `--allow-partial`; this
acknowledgement does not make coverage complete. `MODEL_ELIGIBLE` remains false. Species-policy
response, temporal leakage and ecological interpretation require downstream review.

Native manifests record configuration and common-extent hashes, sources, exact artifact SHA-256,
clipping metadata, schema and known limitations. `load_manifest` verifies the artifact hash and
rejects H3/model-eligible manifests. Public flat output embeds the source, field and coverage metadata in Parquet. A staged
replacement is validated before installation, with a writer lock and restoration on handled
installation errors. Readers check catalog hashes and retry if an update overlaps a read.
There are no immutable generations or current pointers. See [workflows](WORKFLOWS.md).

The catalog has 24 entries and seventeen implemented map families. `catalog --verify-artifacts` verifies
present configured primary artifacts; missing artifacts are skipped, not certified as complete.
Secondary products and legal/source completeness require their own checks. The inspector reports
unavailable/planned layers separately. The flat Parquet metadata defines its own governance product contract. It does not claim
automatic organization-wide shared-schema adoption. No sidecar schema export is needed
for normal public data writes. See the [CLI reference](cli.md).

Version 0.2 rebuilds use `native-reference-2.0`: establishment years no longer fabricate exact dates, marine zero area is preserved separately from total-site area, and point/geodesic-line/unwrapped-equal-area measures have distinct definitions. Valid empty products retain canonical schema; unavailable input remains a failure/status. See [query contracts](query-api.md).

Version 0.2.1 rebuilds use `native-reference-2.1`: repaired source and retained measures
include only the original dimension, and geodesic denominators use canonical dateline-split
support. Query method `native-reference-query-2.1` retains same-dimensional fragments from
nested intersection collections without duplicating native-part memberships. Finite/range
checks precede roundoff snapping. Schema shapes and legacy products remain readable; no
historical artifact is relabeled. See the [correction handoff](hardening-corrections.md).
