# Limitations and interpretation

## Geometry and authority

Agency GIS geometry, mapped classifications, derived spatial support, and
controlling legal instruments have different roles. Preserve source status and
citations. Polygon membership alone does not establish permission, prohibition,
current designation, or a species-specific rule. Boundary lines are not silently
converted into jurisdiction polygons.

Country-water polygons are derived support geometry. The
`authoritative_boundary_segments.parquet` filename describes source provenance;
it does not confer controlling legal effect. Read the family authority policy
and source instruments for date-specific use.

## Coverage and missingness

Collection names do not imply complete U.S./Canadian support. Coverage separates
complete, partial, unavailable, unknown, and not applicable. Runtime source
availability is a separate dimension. `--allow-partial` accepts incomplete support;
it does not fill gaps or make a collection complete.

An empty intersection under partial coverage is not observed absence. In the
optional H3 overlay, unsupported counts/measures stay null. Where recorded
geometry intersects, metrics describe those records rather than an exhaustive
legal inventory. The configured sanctuary roster's completeness label does not
certify arbitrary grid-cell coverage.

## Time

Effective dates, source vintage, learned time, retrieval time, and build time
remain distinct. The inspection date filter includes both effective endpoints
and allows unknown dates through. The H3 export is an inventory-snapshot overlay
and does not filter effective dates. Neither is a historical legal reconstruction.

## Validation and publication

Artifact checksum verification establishes file identity, not current source
availability or legal correctness. `catalog --verify-artifacts` checks present
primary products and skips missing artifacts. Family related products require
their own checksum and consistency checks.

Publication is atomic per file. A multi-file family build has no whole-workspace
rollback or combined generation pointer; a failure can leave some outputs written.
Validate the full intended file set before downstream use. Inspection is a display
operation, not release promotion.

## Regional and model acceptance

All native and optional H3 outputs remain **model-ineligible by default**.
Ecological interpretation, policy-response leakage, temporal qualification,
consumer-grid choice, and model eligibility require explicit downstream review.
Governance context does not measure occurrence, detection, or reporting effort.

The loader currently requires the `full_area` name. Some family publishers need
specific source subsets or the fixed sanctuary roster even for partial builds.
The optional H3 grid must be bounded, cannot cross the antimeridian, and needs
an appropriate explicit metre-based length CRS. See [overlay details](h3-matrix.md).

Offline tests and documentation builds do not establish fresh provider
acquisition, complete regional rebuilds, current legal/source verification,
production readiness, or application integration. Historical migration evidence
is documented separately in [migration history](MIGRATION.md).
