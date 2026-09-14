# shintowiki-scripts

A bot framework and automation pipeline for [shinto.miraheze.org](https://shinto.miraheze.org), with Wikidata integration via QuickStatements and a static GitHub Pages dashboard.

## ⚡ Emergency batch — every QuickStatement, in run order

**▶ [ALL.txt](https://github.com/EmmaLeonhart/shintowiki-scripts/raw/main/_site/emergency-batch/ALL.txt)** — **10,000** lines drawn at random from the 131,567 in the corpus, sized to one QuickStatements paste. Regenerate for a different draw; the [chunked files](_site/emergency-batch/) still hold every line.
([chunked files](_site/emergency-batch/) · [page with per-language counts](https://emmaleonhart.github.io/shintowiki-scripts/emergency-batch.html) · [orphan detail](https://emmaleonhart.github.io/shintowiki-scripts/orphan-label-fixes.html))

**▶ [The three lost shrines](docs/lost-shrines.md)** — a **separate** 42-line batch, not part of `ALL.txt`: fresh items for the three shrines whose Wikidata items were repurposed onto different subjects. Creations are a different QuickStatements shape, so they are kept out of every atomic file and run deliberately.

Linked here rather than only on the dashboard because the README updates the moment it is pushed, while Pages waits on a deploy.

**Run order is deliberate — in the chunks.** `00-orphan-labels.*.txt` runs first, and its **9,976** lines are labels for shrines that carry a *description with no label* in that language. Wikidata's uniqueness constraint is on the **(label, description) pair**, so a description with no label stakes the half that matters least, and when a label finally arrives the completed pair can collide — and it is the *label* edit that gets rejected. A description with no label costs a label. The standing remedy (`audit_orphan_descriptions.py`) therefore **deletes** the description; that is right only where no label exists. Measured 2026-09-06: **9,976 of 10,250 orphans (97%) already have a generated label** sitting in `shinto-label-generator/`, so for almost all of them the deletion would throw away a description we can complete instead. Hence labels first, then the remaining **121,591** lines. `ALL.txt` samples across the whole corpus uniformly, so it carries about 8% of the orphan labels rather than leading with all of them; work the `00-orphan-labels` chunks directly if that ordering is what you want.

Nothing in the batch deletes a description. Regenerate with `python site/generate_emergency_batch.py`.

---

**Dashboard:** [emmaleonhart.github.io/shintowiki-scripts](https://emmaleonhart.github.io/shintowiki-scripts/) — project overview, QuickStatements status, and [run history](https://emmaleonhart.github.io/shintowiki-scripts/runs.html)

**Wiki:** [shinto.miraheze.org](https://shinto.miraheze.org) — the wiki this pipeline maintains

**Bot status:** [User:EmmaBot](https://shinto.miraheze.org/wiki/User:EmmaBot) — live pipeline status, current stage, and run history on-wiki

---

## How it works

Everything runs through **GitHub Actions**. The pipeline is a chain of reusable workflows orchestrated by `cleanup-loop.yml`:

```
cleanup-loop.yml (orchestrator)
├─ generate-quickstatements.yml   → generates Wikidata QuickStatements files
├─ wiki-cleanup.yml               → runs all wiki editing scripts (5 chunks + deprecated)
├─ random-wait.yml                → random delay before QS submission (schedule only)
├─ submit-quickstatements.yml     → submits atomic operations to QuickStatements API
├─ direct-daily-edits.yml         → fallback: applies edits via Wikidata API if QS submission fails
├─ test-wikidata-qualifier.yml    → applies P459 qualifiers via Wikidata API directly
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

The root is kept deliberately small: only core docs + workflow files, the
remote-queue files (read in place by the claude.ai routine), and dotfiles.
Everything else lives in a purpose-named directory.

```
shintowiki-scripts/
├── .github/workflows/          # GitHub Actions workflow chain (the pipeline)
├── shinto_miraheze/            # Wiki-editing bot scripts — the main bot
│   ├── orchestrators/          #   per-namespace sweepers, ops/, *.state
│   └── EmmaBot.wiki            #   User:EmmaBot status-page template
├── modern-quickstatements/     # Wikidata QuickStatements generation + submission
│   ├── reports/                #   JSON run reports from QS submissions
│   └── _site/                  #   generated QS dashboard pages
├── site/generate_pages.py      # Builds the main GitHub Pages dashboard (→ _site/)
├── fandom/                     # shinto.fandom import scripts + their input list
├── shinto-label-generator/     # Sub-project: multilingual shrine-label QuickStatements
├── _site/                      # GitHub Pages output (committed; updated by CI)
├── docs/                       # Reference docs (see Documentation below)
│                                # (archive/ removed 2026-05-28; retired scripts are deleted, not archived)
│
│   # Wiki ↔ repo content-sync dirs (one <title>.wiki per page; see docs/SYNCING.md):
├── need_translation/  git_synced/  miraheze_unique/  fandom_unique/  duplicated_content/
│
│   # Root files (kept minimal):
├── README.md  CLAUDE.md  DEVLOG.md  todo.md  queue.md
├── remote_queue.py + remote_queue.json + consume_remote_queue.state
│                               #   built here; the claude.ai remote routine reads
│                               #   the JSON at the repo root, so these stay in root
└── !runClaude.bat  .gitignore  .gitattributes  .nojekyll
```

---

## Wiki editing pipeline (wiki-cleanup.yml)

The main cleanup job runs all `shinto_miraheze/` scripts in order, grouped into chunks with state commits between them. Each chunk's state files are committed to git so progress is preserved if a later chunk fails.

### Chunk 1: Import & Categorization
| Script | Purpose |
|--------|---------|
| `overwrite_deleted_enwiki_pages.py` | Overwrites local pages whose enwiki source was deleted |
| `create_wanted_categories.py` | Creates stub pages for Special:WantedCategories |
| `categorize_uncategorized_categories.py` | Tags uncategorized categories under EmmaBot umbrella |
| `triage_emmabot_categories.py` | First-pass triage: checks EmmaBot categories against enwiki |
| `triage_emmabot_categories_jawiki.py` | Second-pass triage: checks against jawiki |
| `triage_emmabot_categories_secondary.py` | Third-pass triage: secondary heuristics |
| `triage_secondary_single_member.py` | Moves single-member categories to triaged bucket |
| `enrich_jawiki_categories.py` | Enriches categories with jawiki interwiki data |
| `create_shrine_ranking_pages.py` | Creates shrine ranking article pages (TEMPORARY) |

### Chunk 2: Structural Fixes
| Script | Purpose |
|--------|---------|
| `delete_unused_templates.py` | Deletes pages from Special:UnusedTemplates |
| `fix_double_redirects.py` | Fixes Special:DoubleRedirects |
| `resolve_double_category_qids.py` | Simplifies QID disambiguation pages where all targets resolve to the same category |

### Chunk 3: Wikidata-related wiki edits

> ⛔ **There is no date check here, and no date belongs here.** This section said
> *"paused until May 2026 via a date check in the workflow"* until 2026-09-14, four
> months after that date and long after the mechanism changed. These steps edit
> **shintowiki**, so they are gated on the wiki lockout
> (`steps.lockout.outputs.locked`); Wikidata writes are gated separately by
> `shinto_miraheze/wikidata_editing_lockout.state`. Ask the state file — CLAUDE.md
> forbids copying its date anywhere, precisely because a duplicated freeze date is one
> a reader can act on after it has expired. Each step runs at `--max-edits 50`,
> separate from the global `WIKI_EDIT_LIMIT`.

| Script | Purpose |
|--------|---------|
| `generate_p11250_quickstatements.py` | Generates P11250 QuickStatements for items missing the property |
| `clean_p11250_quickstatements.py` | Removes applied QuickStatements lines |
| `clean_wikidata_cat_redirects.py` | Removes wikidata category tags from redirect pages |

`tag_pages_without_wikidata.py` was in this list and is not a step any more — the
`mainspace_orchestrator` owns that work, and the workflow step is commented out with
that note beside it. The script is still on disk.

### Chunk 4: Final Core
| Script | Purpose |
|--------|---------|
| ~~`fix_template_noinclude.py`~~ | ~~Moves stray categories/wikidata links into `<noinclude>` on templates~~ (disabled — one-time fix completed) |
| `categorize_uncategorized_pages.py` | Tags uncategorized mainspace pages |
| `tag_untranslated_japanese.py` | Detects and categorizes pages with untranslated Japanese text |
| `tag_untranslated_japanese.py --category` | Re-buckets 300+ untranslated pages with extended thresholds (TEMPORARY) |

> **Three scripts this section used to list were deleted on 2026-07-05 and their steps
> are gone, each for a recorded reason** — `reimport_from_enwiki.py` (0 imports across
> three runs; its input queue drained), `migrate_talk_pages.py` (removed 2026-04-22, the
> talk-page rebuild was predicated on a wiki direction no longer being pursued), and
> `normalize_category_pages.py` (ported to the `normalize_category_page` orchestrator op,
> so it runs on every sweep instead of Sundays only). The reasons live beside the
> commented-out steps in `wiki-cleanup.yml`.

### Cleanup Loop
| Script | Purpose |
|--------|---------|
| `delete_unused_categories.py` | Deletes Special:UnusedCategories (skips `{{Possibly empty category}}`) |
| `delete_orphaned_talk_pages.py` | Deletes talk pages with no subject page |
| `delete_broken_redirects.py` | Deletes Special:BrokenRedirects |
| `remove_crud_categories.py` | Strips crud category tags from pages |

### Bookkeeping
| Script | Purpose |
|--------|---------|
| `update_bot_userpage_status.py` | Updates User:EmmaBot status page with pipeline stage and run info |

### Deprecated (Sunday + monthly)
| Script | Schedule | Purpose |
|--------|----------|---------|
| `tag_shikinaisha_talk_pages.py` | Sunday | Adds "generated from Wikidata" notice to shikinaisha talk pages |
| `fix_erroneous_qid_category_links.py` | 1st of month | Fixes category/QID mismatches |
| `remove_legacy_cat_templates.py` | 1st of month | Removes legacy template artifacts from categories |
| `move_categories.py` | 1st of month | Moves/renames categories per configured CSV |
| `create_japanese_category_qid_redirects.py` | 1st of month | Creates QID redirects for Japanese-named categories |

---

## History archive repo

Full per-page revision history offloaded by the `history_offload` op lives in a separate repository: **[EmmaLeonhart/shintowiki-xml-archives](https://github.com/EmmaLeonhart/shintowiki-xml-archives)**.

- **Layout:** `xml/{first_char}/{safe_title}.xml` — one `Special:Export` dump per page, sharded by the first character of the slug.
- **Viewer:** [emmaleonhart.github.io/shintowiki-scripts/wikihistory.html](https://emmaleonhart.github.io/shintowiki-scripts/wikihistory.html) — takes `?page=<Title>` and renders the archived XML.
- **Producer:** `shinto_miraheze/orchestrators/ops/history_offload.py` (archive) + `shinto_miraheze/orchestrators/ops/_archive_repo.py` (clone/commit/push).
- **Gates:** `ENABLE_HISTORY_OFFLOAD=1` turns the op on; `ENABLE_REVDEL=1` separately enables stage 3 (hiding old revisions on-wiki so they drop out of Miraheze XML dumps).
- **Auth:** `ARCHIVE_REPO_DEPLOY_KEY` secret (SSH deploy key) in CI; `gh auth token` locally. Note the account is **EmmaLeonhart** (no hyphen), not `Emma-Leonhart`.

---

## QuickStatements pipeline (modern-quickstatements/)

⚠ **The QuickStatements API is retired (2026-07-04) and nothing here calls it.** This
section described it as the mechanism until 2026-09-14. `submit_daily_batch.py` makes
no network calls at all — its own docstring says *"the QS_TOKEN/QS_USERNAME secrets are
no longer used"* — and it exits non-zero so `direct-daily-edits.yml` fires.
`direct_daily_edits.py` is therefore **the only path to Wikidata**, not a fallback, and
CLAUDE.md's "ONE path only" rule is about that script.

Dozens of `generate_*.py` scripts each emit QuickStatements lines into an atomic `.txt`
file; the drip samples across all of them and executes ~500 lines a day through the
Wikidata API at a randomised ~35-40s spacing. A representative few:

| Script | What it does |
|--------|--------------|
| `generate_p958_qualifiers.py` | P958 (section) qualifiers for P13677 (Kokugakuin Museum entry ID) |
| `generate_modern_shrine_ranking_qualifiers.py` | P459 (determination method) qualifiers for P13723 (shrine ranking) |
| `submit_daily_batch.py` | Inert since the QS API was retired; writes a JSON report to `reports/` and exits 1 |
| `direct_daily_edits.py` | **The** write path: executes ~500 sampled lines a day via the Wikidata API |
| `fetch_p11250_from_wiki.py` | Fetches P11250 lines from shintowiki into `p11250_miraheze_links.txt` |
| `generate_run_history.py` | Builds `_site/runs.html` from every JSON in `reports/` |
| `wdqs_transport.py` | Shared throttled/retrying WDQS transport (2.5s floor, 429 bails, 15/45/135 backoff) |

**The list of atomic files is `ATOMIC_FILES` in `direct_daily_edits.py` — 83 of them as
of 2026-09-14, not the five this section used to name.** It is not reproduced here
because a hand-copied list of a generated set goes stale silently; that is what
happened to the five.

`test_wikidata_qualifier.py` was in the table above and no longer exists.

All outcomes (submitted/partial/skipped/failed) are logged to JSON reports, and
`runs.html` tracks them over time. ⛔ Those reports are NOT covered by the
"reports expire after a week" rule — `generate_run_history.py` globs every file in
`reports/` to build the page, so they are its data. See CLAUDE.md.

---

## GitHub Pages dashboard

**Live at:** [emmaleonhart.github.io/shintowiki-scripts](https://emmaleonhart.github.io/shintowiki-scripts/)

Deployed via `generate-pages.yml` (daily at 00:30 UTC). The `build-run-history.yml` workflow also updates `runs.html` after every pipeline run.

| Page | URL | Source |
|------|-----|--------|
| Project overview | [index](https://emmaleonhart.github.io/shintowiki-scripts/) | `site/generate_pages.py` — automation status + P11250 overview |
| Shrine ranking dashboard | [shrine-ranking](https://emmaleonhart.github.io/shintowiki-scripts/shrine-ranking.html) | `modern-quickstatements/_site/index.html` — P13723/P958 QuickStatements status (renamed during Pages build) |
| Run history | [runs](https://emmaleonhart.github.io/shintowiki-scripts/runs.html) | `generate_run_history.py` — QS submission history with outcome badges |
| P11250 QuickStatements | [p11250](https://emmaleonhart.github.io/shintowiki-scripts/p11250.html) | `site/generate_pages.py` — copy-paste QuickStatements for Wikidata P11250 |

---

## Credentials / secrets

All credentials are injected via GitHub Actions secrets/variables. No credentials in source code.

### Shintowiki (Miraheze)

| Name | Type | Purpose |
|------|------|---------|
| `WIKI_USERNAME` | Variable | Bot-password login for shinto.miraheze.org (format: `MainUser@BotName`) |
| `WIKI_PASSWORD` | Secret | Bot password for shinto.miraheze.org |

Used by `wiki-cleanup.yml` for all wiki editing operations.



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

Scripts are designed for CI execution. For local testing, set `WIKI_USERNAME` and `WIKI_PASSWORD` environment variables. See [API.md](docs/API.md) for access patterns.

---

## Documentation

| File | Contents |
|------|----------|
| [docs/SCRIPTS.md](docs/SCRIPTS.md) | Full catalog of all scripts with status |
| [docs/API.md](docs/API.md) | How every external service is accessed |
| [docs/SHINTOWIKI_STRUCTURE.md](docs/SHINTOWIKI_STRUCTURE.md) | Page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, categories, templates, talk pages |
| [docs/SYNCING.md](docs/SYNCING.md) | Every wiki↔repo↔Wikidata sync pathway, direction, and conflict policy |
| [docs/HISTORY.md](docs/HISTORY.md) | Wiki development timeline and context |
| [docs/VISION.md](docs/VISION.md) | Architecture plan and future direction |
| [todo.md](todo.md) | Prioritized list of open tasks |
| [queue.md](queue.md) | Active-session work queue (bounds scope) |
| [DEVLOG.md](DEVLOG.md) | Running log of all significant operations |
