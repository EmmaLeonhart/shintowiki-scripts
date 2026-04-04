# modern-quickstatements

Automated QuickStatements generation and submission for Wikidata shrine property maintenance. Part of the [shintowiki-scripts](https://github.com/EmmaLeonhart/shintowiki-scripts) pipeline.

**Dashboard:** [shrine-ranking](https://emmaleonhart.github.io/shintowiki-scripts/shrine-ranking.html) | **Run history:** [runs](https://emmaleonhart.github.io/shintowiki-scripts/runs.html)

## What this does

Generates QuickStatements v1 files for batch Wikidata edits and submits them daily via the QuickStatements API. Tracks submission outcomes in JSON reports and serves a run history dashboard.

### Property work

**P13723 (shrine ranking) — Modern shrine ranking qualifiers:**
- Adds `P459` (determination method) → `Q712534` (modern system of ranked Shinto shrines) qualifier to all existing `P13723` statements
- Phase 3 (non-atomic, manual): migrates P31/P1552 shrine ranking statements to P13723
- ~4,179 statements across all shrines with P13723

**P13677 (Kokugakuin Museum entry ID) — Section qualifiers:**
- Adds `P958` (section, verse, paragraph, or clause) qualifiers to P13677 statements
- Qualifies each entry ID with the relevant section of the Kokugakuin database

**P4656 (Wikimedia import URL) — jawiki references:**
- Adds P4656 references pointing to ja.wikipedia.org source pages for modern P13723 statements

**P31 (instance of) — Shikinai Hiteisha removal:**
- Removes incorrect P31=Q135026601 (Shikinai Hiteisha / non-Engishiki shrine) statements

## Files

| File | Description |
|------|-------------|
| `generate_modern_shrine_ranking_qualifiers.py` | Generates P459 qualifiers + Phase 3 migration lines |
| `generate_p958_qualifiers.py` | Generates P958 section qualifiers for P13677 |
| `submit_daily_batch.py` | Submits atomic QS files via API; writes JSON report to `reports/` |
| `test_wikidata_qualifier.py` | Applies P459 qualifiers to P13723 via Wikidata API directly (10/run) |
| `direct_daily_edits.py` | Fallback: applies edits via Wikidata API directly when QuickStatements API fails |
| `fetch_p11250_from_wiki.py` | Fetches P11250 QS lines from `[[QuickStatements/P11250]]` wiki page; writes `p11250_miraheze_links.txt` |
| `generate_run_history.py` | Builds `_site/runs.html` from all report JSONs |

### Generated files (atomic — submitted daily)

| File | Contents |
|------|----------|
| `modern_shrine_ranking_qualifiers.txt` | P459 qualifiers on existing P13723 |
| `p958_qualifiers.txt` | P958 section qualifiers on P13677 |
| `p4656_jawiki_references.txt` | P4656 ja.wiki references on P13723 |
| `remove_shikinai_hiteisha.txt` | Remove P31=Q135026601 |
| `p11250_miraheze_links.txt` | P11250 (ShintoDB article ID) links fetched from shintowiki |

### Generated files (non-atomic — manual submission only)

| File | Contents |
|------|----------|
| `migrate_*.txt` | Phase 3 migration lines (remove old property + add new P13723) |
| `p958_manual_review.txt` | P958 lines needing human review |

## How submission works

The `submit_daily_batch.py` script:
1. Reads each atomic `.txt` file
2. Submits all lines as a single QuickStatements batch via the API
3. Retries up to 10 times with 20s delay between attempts
4. Writes a JSON report to `reports/` with outcome, batch details, and API responses
5. **Never exits non-zero** — logs outcome (submitted/partial/skipped/failed) and exits cleanly

The submission job is part of the `cleanup-loop.yml` workflow chain. Its success or failure does not affect the overall workflow status.

### Run history page

`generate_run_history.py` reads all `reports/*.json` files and generates `_site/runs.html` — an HTML dashboard showing:
- Summary counts by outcome (submitted, partial, failed, skipped, nothing to do)
- Per-run cards with timestamp, outcome badge, and batch-level details
- Color-coded status indicators

This page is served via GitHub Pages at `/runs.html`.

## Required secrets

| Secret | Description |
|--------|-------------|
| `QS_TOKEN` | API token from your [QuickStatements user page](https://quickstatements.toolforge.org/) |
| `QS_USERNAME` | Wikidata username associated with the token |

Set in **Settings → Secrets and variables → Actions** on the GitHub repo. If either is not set, the submission step logs "SKIPPED" and continues without error.

## Local usage

```bash
pip install requests

# Generate QuickStatements files
python generate_p958_qualifiers.py
python generate_modern_shrine_ranking_qualifiers.py

# Build run history page (reads reports/*.json)
python generate_run_history.py
```

Non-atomic files (migration lines) must be copy-pasted into [QuickStatements](https://quickstatements.toolforge.org/) manually.
