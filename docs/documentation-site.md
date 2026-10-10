# Documentation site

The site renders tracked Markdown and assets in `docs/`. It does not run acquisition,
scientific producers, or publish datasets, local migration evidence or generated maps.

## Build and preview locally

Use an isolated Python 3.11+ environment from the checkout:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python -m pip check
.venv/bin/python -m mkdocs build --strict
.venv/bin/python -m mkdocs serve
```

Open the address printed by MkDocs. Navigation coverage, missing Markdown links
and anchors are warnings that fail the strict build. Repository source notes are
linked to a pinned GitHub revision in the [source index](sources.md) because they
live outside the site. External source availability requires a separate check;
MkDocs validates local navigation/links/anchors, not remote provider uptime. `site/` is ignored build output.

## Pull requests and main

The **Documentation site** workflow builds on every pull request targeting `main`,
every push to `main`, and manual `workflow_dispatch` runs. Each successful build
uploads `documentation-site` with a seven-day retention. Download and extract it
from the Actions run, then serve the extracted directory with `python -m http.server`.
This artifact is a preview, not a hosted PR site.

Build jobs have only `contents: read` and checkout does not persist credentials.
Pull request code never reaches a deployment job or gets a Pages/OIDC write token.
The existing **Offline package checks** workflow remains separate and unchanged.

## Publish after review

A main push validates and uploads the preview; it does **not** publish. After manual
review and merge, a maintainer must run **Documentation site** from the Actions tab
with branch **main**. Only this manual main run uploads a Pages artifact and enables
the deployment job. Runs from other branches build a preview and skip deployment.
Publishing is serialized in the `github-pages` concurrency group without cancelling
an in-progress publication. Only the deploy job has `pages: write` and `id-token: write`.
It uses the `github-pages` environment and the official GitHub Pages Actions.

The intended canonical URL is <https://marinecast.github.io/toolkit-governance/>.
Confirm publication using the deploy job's environment URL and an HTTP 200
readback of the rendered homepage and linked pages. A successful build only
confirms a preview artifact. Repository **Settings → Pages → Source** must be **GitHub
Actions**, and the `github-pages` environment must allow deployments from `main`.
If those settings need changing, a repository administrator must review the change.
No workflow automatically enables Pages or changes environment protection rules.


## Verified publication checkpoint

On 2026-10-09 the canonical URL returned HTTP **404**. Read-only API checks
reported Pages `build_type: workflow`, HTTPS enabled, and an existing
`github-pages` environment with a custom branch policy allowing `main`.
These settings were inspected, not changed. Documentation/site setup and agent
guidance are consolidated with the study implementation in
[PR7](https://github.com/MarineCast/toolkit-governance/pull/7); it incorporates the
earlier PR6 documentation change, so PR6 is not a separate merge dependency.
Publication is blocked on user review/merge of the combined change followed by
the authorized manual main dispatch.
Recheck settings and environment protections at dispatch time. If administrator
settings or permissions must change, obtain that approval explicitly.

Do not describe this site as live until deployment and HTTP/content readback pass.
A local preview and downloadable CI artifact support review before merge.
