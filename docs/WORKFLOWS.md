# Development and verification

Work from the owning checkout. Read AGENTS.md, affected source/tests and the relevant DATA_SOURCES.md before changing scientific behavior. Source and tests outrank stale prose. Keep `config/` and packaged `src/governance/resources/config/` defaults byte-identical.

```sh
python -m pip install -e '.[test,docs]'
python -m pytest -q
mkdocs build --strict
git diff --check
```

For behavior changes, run focused product/scientific tests first, then the full suite. Validate a regular wheel outside the checkout with consumer/sibling imports blocked and run `pip check`. For prose, verify internal links, strict MkDocs and whitespace checks. Offline fixtures validate software behavior; report live-provider, native/regional, scientific and consumer qualification separately rather than treating fixtures as observations.

Use [the public offline build](how-to-use.md) for acceptance against retained originals and explicit grids. Validate output checksums, schema, identities, null support, preserved source records and exact grid membership. Compare semantic arrays when encoded Parquet bytes can change. Do not download new data as a side effect of a documentation or software test.

Keep temporary native and matrix products outside public delivery. Public output contains only the files declared in [the contract](parquet-products.md). Record input/output hashes, source receipts, code/environment versions and any unrun checks in the task evidence. Do not commit acquired datasets, secrets or local machine paths.

## GitHub merge checks

As checked on 2026-10-21, `main` requires `test (3.11)` and `test (3.14)`,
current-base status and resolved review threads. The separate `main-merge-access`
ruleset permits PR merges through the `main-merge-stevetylda` team, which has
repository write access and currently contains only `stevetylda`. That repository
assignment was explicitly approved on 2026-10-21; future team members inherit its
write access. The safeguards ruleset remains separate and unchanged.
