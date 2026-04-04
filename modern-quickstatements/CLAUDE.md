# modern-quickstatements

## Workflow Rules
- **Commit early and often.** Every meaningful change gets a commit with a clear message explaining *why*, not just what.
- **Do not enter planning-only modes.** All thinking must produce files and commits. If scope is unclear, create a `planning/` directory and write `.md` files there instead of using an internal planning mode.
- **Keep this file up to date.** As the project takes shape, record architectural decisions, conventions, and anything needed to work effectively in this repo.
- **Update README.md regularly.** It should always reflect the current state of the project for human readers.

## Project Description

Automated QuickStatements generation and submission for Wikidata shrine property maintenance. This subdirectory generates QuickStatements v1 files for batch Wikidata edits (P13723 shrine ranking qualifiers, P958 section qualifiers, P4656 jawiki references, Shikinai Hiteisha removals) and submits them daily via the QuickStatements API as part of the shintowiki-scripts pipeline.

## Architecture and Conventions

### File layout
- `generate_*.py` — QuickStatements generators. Each queries Wikidata SPARQL and outputs `.txt` files.
- `submit_daily_batch.py` — API submission script. Reads atomic `.txt` files, submits via QS API, writes JSON reports.
- `direct_daily_edits.py` — Fallback: applies edits via Wikidata API directly when QuickStatements API fails.
- `fetch_p11250_from_wiki.py` — Fetches P11250 QS lines from `[[QuickStatements/P11250]]` wiki page for daily batch submission.
- `generate_run_history.py` — Reads `reports/*.json` and builds `_site/runs.html`.
- `reports/` — JSON run reports (one per submission attempt).
- `_site/` — Generated HTML/TXT files for GitHub Pages.

### Submission behavior
- Only **atomic** operations (each line independent) are submitted automatically.
- **Non-atomic** operations (paired remove+add) require manual submission.
- The submission script **never exits non-zero** — it logs outcomes and exits cleanly. The run history page tracks failures.
- Missing `QS_TOKEN` or `QS_USERNAME` results in a "skipped" outcome, not an error.

### Workflow integration
This subdirectory's scripts are called by these GitHub Actions workflows:
1. `generate-quickstatements.yml` — pre-flight generation before wiki cleanup
2. `submit-quickstatements.yml` — post-cleanup submission with report commit
3. `test-wikidata-qualifier.yml` — direct Wikidata API edits (P459 qualifiers on P13723, bypasses QS)
4. `build-run-history.yml` — final action: rebuilds the run history page
5. `generate-pages.yml` — daily GitHub Pages build includes `_site/runs.html`
