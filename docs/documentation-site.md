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
linked to GitHub because they live outside the site. `site/` is ignored build output.

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
Successful publication is confirmed by the deploy job's environment URL, not by
completion of a build. Repository **Settings → Pages → Source** must be **GitHub
Actions**, and the `github-pages` environment must allow deployments from `main`.
If those settings need changing, a repository administrator must review the change.
No workflow automatically enables Pages or changes environment protection rules.
