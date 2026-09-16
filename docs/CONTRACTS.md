# Native-geometry product contracts

The extraction preserves the original scientific calculations and source-specific distinctions.
Canonical GeoParquet uses EPSG:4326. `GOVERNANCE_FEATURE_ID` identifies a source-backed feature;
`GEOMETRY_PART_ID` is unique within each artifact and distinguishes clipped parts. Do not join
by row order or hide duplicates. Canonical products contain no H3 fields or implicit grid.

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
rejects H3/model-eligible manifests. Atomic writes are per file; the multi-file family pipeline
has no global rollback or combined atomic generation pointer. Consumers must verify manifests
and treat missing or inconsistent outputs as incomplete.

The catalog has 24 entries and six implemented map families. `catalog --verify-artifacts` verifies
present configured primary artifacts; missing artifacts are skipped, not certified as complete.
Secondary products and legal/source completeness require their own checks. The inspector reports
unavailable/planned layers separately. Native manifests are not the proposed MarineCast H3
manifest v0.1; no shared-contract adoption is claimed.
