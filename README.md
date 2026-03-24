# shintowiki-scripts

A bot framework and automation pipeline for [shinto.miraheze.org](https://shinto.miraheze.org), with Wikidata integration via QuickStatements and a static GitHub Pages dashboard.

**Dashboard:** [emmaleonhart.github.io/shintowiki-scripts](https://emmaleonhart.github.io/shintowiki-scripts/) — project overview, QuickStatements status, and [run history](https://emmaleonhart.github.io/shintowiki-scripts/runs.html)

**Wiki:** [shinto.miraheze.org](https://shinto.miraheze.org) — the wiki this pipeline maintains

**Bot status:** [User:EmmaBot](https://shinto.miraheze.org/wiki/User:EmmaBot) — live pipeline status, current stage, and run history on-wiki

---

## How it works

Everything runs through **GitHub Actions** — no scripts are run locally. The pipeline is a chain of reusable workflows orchestrated by `cleanup-loop.yml`:

```
cleanup-loop.yml (orchestrator)
├─ generate-quickstatements.yml   → generates Wikidata QuickStatements files
├─ wiki-cleanup.yml               → runs all wiki editing scripts (5 chunks + deprecated)
├─ random-wait.yml                → random delay before QS submission (schedule only)
├─ submit-quickstatements.yml     → submits atomic operations to QuickStatements API
└─ build-run-history.yml          → rebuilds the run history page from reports
```

A separate workflow, `generate-pages.yml`, builds and deploys the GitHub Pages site (daily at 00:30 UTC).

### Triggers

| Trigger | What happens |
|---------|--------------|
| Push to main (excluding .state/.log/.errors) | Full pipeline run |
| Daily schedule (00:00 UTC) | Full pipeline run + random-delayed QS submission |
| Manual dispatch | Full pipeline run |

---

## Repository structure

```
shintowiki-scripts/
├── .github/workflows/          # GitHub Actions workflow chain (7 files)
├── shinto_miraheze/            # Wiki editing bot scripts (~46 Python, 3 shell)
├── modern-quickstatements/     # Wikidata QuickStatements generation + submission
│   ├── reports/                # JSON run reports from QS submissions
│   └── _site/                  # Generated QS dashboard pages
├── _site/                      # GitHub Pages output (main site)
├── generate_pages.py           # Generates the main GitHub Pages site
├── EmmaBot.wiki                # Wiki template for User:EmmaBot status updates
└── docs: README.md, SCRIPTS.md, API.md, SHINTOWIKI_STRUCTURE.md,
          HISTORY.md, VISION.md, TODO.md, DEVLOG.md
```

---

## Wiki editing pipeline (wiki-cleanup.yml)

The main cleanup job runs all `shinto_miraheze/` scripts in order, grouped into chunks with state commits between them. Each chunk's state files are committed to git so progress is preserved if a later chunk fails.

### Chunk 1: Import & Categorization
| Script | Purpose |
|--------|---------|
| `reimport_from_enwiki.py` | Reimports pages from enwiki XML to fix broken template transclusions (10/run) |
| `overwrite_deleted_enwiki_pages.py` | Overwrites local pages whose enwiki source was deleted |
| `create_wanted_categories.py` | Creates stub pages for Special:WantedCategories |
| `categorize_uncategorized_categories.py` | Tags uncategorized categories under EmmaBot umbrella |
| `triage_emmabot_categories.py` | First-pass triage: checks EmmaBot categories against enwiki |
| `triage_emmabot_categories_jawiki.py` | Second-pass triage: checks against jawiki |
| `triage_emmabot_categories_secondary.py` | Third-pass triage: secondary heuristics |
| `triage_secondary_single_member.py` | Moves single-member categories to triaged bucket |
| `create_shrine_ranking_pages.py` | Creates shrine ranking article pages (TEMPORARY) |

### Chunk 2: Structural Fixes
| Script | Purpose |
|--------|---------|
| `delete_unused_templates.py` | Deletes pages from Special:UnusedTemplates |
| `fix_double_redirects.py` | Fixes Special:DoubleRedirects |
| `resolve_double_category_qids.py` | Simplifies QID disambiguation pages where all targets resolve to the same category |

### Chunk 3: Wikidata
| Script | Purpose |
|--------|---------|
| `generate_p11250_quickstatements.py` | Generates P11250 QuickStatements for items missing the property |
| `clean_p11250_quickstatements.py` | Removes applied QuickStatements lines |
| `tag_pages_without_wikidata.py` | Tags pages lacking `{{wikidata link}}` |
| `clean_wikidata_cat_redirects.py` | Removes wikidata category tags from redirect pages |

### Chunk 4: Final Core
| Script | Purpose |
|--------|---------|
| `fix_template_noinclude.py` | Moves stray categories/wikidata links into `<noinclude>` on templates |
| `categorize_uncategorized_pages.py` | Tags uncategorized mainspace pages |
| `tag_untranslated_japanese.py` | Detects and categorizes pages with untranslated Japanese text |

### Cleanup Loop
| Script | Purpose |
|--------|---------|
| `delete_unused_categories.py` | Deletes Special:UnusedCategories (skips `{{Possibly empty category}}`) |
| `migrate_talk_pages.py` | Rebuilds talk pages with discussion content from Wikipedia |
| `delete_orphaned_talk_pages.py` | Deletes talk pages with no subject page |
| `delete_broken_redirects.py` | Deletes Special:BrokenRedirects |
| `remove_crud_categories.py` | Strips crud category tags from pages |

### Deprecated (Sunday only)
| Script | Purpose |
|--------|---------|
| `normalize_category_pages.py` | Enforces canonical category page layout |
| `tag_shikinaisha_talk_pages.py` | Adds "generated from Wikidata" notice to shikinaisha talk pages |
| `fix_erroneous_qid_category_links.py` | Fixes category/QID mismatches |
| `remove_legacy_cat_templates.py` | Removes legacy template artifacts from categories |
| `move_categories.py` | Moves/renames categories per configured CSV |
| `create_japanese_category_qid_redirects.py` | Creates QID redirects for Japanese-named categories |

---

## QuickStatements pipeline (modern-quickstatements/)

Generates and submits Wikidata property edits via the [QuickStatements API](https://quickstatements.toolforge.org/):

| Script | What it does |
|--------|--------------|
| `generate_p958_qualifiers.py` | Generates P958 (section) qualifiers for P13677 (Kokugakuin Museum entry ID) |
| `generate_modern_shrine_ranking_qualifiers.py` | Generates P459 (determination method) qualifiers for P13723 (shrine ranking) |
| `submit_daily_batch.py` | Submits atomic QS operations; writes JSON reports to `reports/` |
| `generate_run_history.py` | Builds `_site/runs.html` from all report JSONs |

Atomic files submitted daily:
- `modern_shrine_ranking_qualifiers.txt` — P459 qualifiers on P13723
- `p4656_jawiki_references.txt` — P4656 ja.wiki references on P13723
- `p958_qualifiers.txt` — P958 section qualifiers on P13677
- `remove_shikinai_hiteisha.txt` — Remove P31=Q135026601 (Shikinai Hiteisha)

The submission job **never fails the workflow** — it logs the outcome (submitted/partial/skipped/failed) to a JSON report and exits cleanly. The run history page at `runs.html` tracks all outcomes over time.

---

## GitHub Pages dashboard

**Live at:** [emmaleonhart.github.io/shintowiki-scripts](https://emmaleonhart.github.io/shintowiki-scripts/)

Deployed via `generate-pages.yml` (daily at 00:30 UTC). The `build-run-history.yml` workflow also updates `runs.html` after every pipeline run.

| Page | URL | Source |
|------|-----|--------|
| Project overview | [index](https://emmaleonhart.github.io/shintowiki-scripts/) | `generate_pages.py` — automation status + P11250 overview |
| Shrine ranking dashboard | [shrine-ranking](https://emmaleonhart.github.io/shintowiki-scripts/shrine-ranking.html) | `modern-quickstatements` — P13723/P958 QuickStatements status |
| Run history | [runs](https://emmaleonhart.github.io/shintowiki-scripts/runs.html) | `generate_run_history.py` — QS submission history with outcome badges |
| P11250 QuickStatements | [p11250](https://emmaleonhart.github.io/shintowiki-scripts/p11250.html) | Copy-paste QuickStatements for Wikidata P11250 |

---

## Credentials / secrets

All credentials are injected via GitHub Actions secrets/variables. No credentials in source code.

### Shintowiki (Miraheze)

| Name | Type | Purpose |
|------|------|---------|
| `WIKI_USERNAME` | Variable | Bot-password login for shinto.miraheze.org (format: `MainUser@BotName`) |
| `WIKI_PASSWORD` | Secret | Bot password for shinto.miraheze.org |

Used by `wiki-cleanup.yml` for all wiki editing operations.

### Wikidata / Wikimedia

| Name | Type | Purpose |
|------|------|---------|
| `MW_BOTNAME` | Secret | Wikimedia bot-password login (format: `User@BotName`) for Wikidata editing |
| `BOT_TOKEN` | Secret | Wikimedia bot password token (the password part of the bot-password) |

Reserved for future direct Wikidata editing via the MediaWiki API. Not currently used by any workflow — all Wikidata edits currently go through QuickStatements.

### QuickStatements

| Name | Type | Purpose |
|------|------|---------|
| `QS_TOKEN` | Secret | API token from your [QuickStatements user page](https://quickstatements.toolforge.org/) |
| `QS_USERNAME` | Secret | Wikidata username for QuickStatements submissions |

Used by `submit-quickstatements.yml` to submit atomic QuickStatements batches.

---

## Setup (for local development)

```bash
pip install mwclient requests
```

Scripts are designed for CI execution. For local testing, set `WIKI_USERNAME` and `WIKI_PASSWORD` environment variables. See [API.md](API.md) for access patterns.

---

## Documentation

| File | Contents |
|------|----------|
| [SCRIPTS.md](SCRIPTS.md) | Full catalog of all scripts with status |
| [API.md](API.md) | How every external service is accessed |
| [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) | Page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, categories, templates, talk pages |
| [HISTORY.md](HISTORY.md) | Wiki development timeline and context |
| [VISION.md](VISION.md) | Architecture plan and future direction |
| [TODO.md](TODO.md) | Prioritized list of open tasks |
| [DEVLOG.md](DEVLOG.md) | Running log of all significant operations |
