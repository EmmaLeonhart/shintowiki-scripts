# Scripts catalog

Status codes:
- **ACTIVE** — currently maintained, runs in the automated pipeline
- **MANUAL** — exists and works, but requires human judgment to run
- **DEPRECATED** — runs weekly (Sundays) as safety net, likely complete
- **LEGACY** — old/superseded, kept for reference
- **COMPLETE** — ran to completion, no longer needed

---

## Workflow chain (.github/workflows/)

The pipeline is a chain of reusable workflows orchestrated by `cleanup-loop.yml`:

| Workflow | Role | Timeout |
|----------|------|---------|
| `cleanup-loop.yml` | Orchestrator — chains all others via `workflow_call` | — |
| `generate-quickstatements.yml` | Pre-flight: generates P958 and P13723 QuickStatements files | 15 min |
| `wiki-cleanup.yml` | Main: runs all `shinto_miraheze/` scripts with state commits between chunks | 330 min |
| `random-wait.yml` | Random 1–3600s delay (schedule-only, prevents thundering herd) | — |
| `submit-quickstatements.yml` | Submits atomic QS operations to the API, commits run report | 30 min |
| `test-wikidata-qualifier.yml` | Direct Wikidata API edits: applies P459 qualifiers to P13723 statements | 10 min |
| `build-run-history.yml` | Final: rebuilds run history page from all report JSONs | 10 min |
| `generate-pages.yml` | Separate: builds and deploys GitHub Pages site (daily 00:30 UTC) | 15 min |

---

## Shell scripts (shinto_miraheze/)

| Script | Status | Description |
|--------|--------|-------------|
| `run_step.sh` | ACTIVE | Wrapper for each cleanup loop step. Updates `User:EmmaBot` stage before/after execution. |
| `commit_state.sh` | ACTIVE | Commits changed `*.state`, `*.log`, `*.errors` files after each chunk. |
| `cleanup_loop.sh` | LEGACY | Original local orchestrator script. Superseded by the GitHub Actions workflow chain, but kept for reference. |

---

## shinto_miraheze/ — automated pipeline scripts

### Bookkeeping

| Script | Status | Description |
|--------|--------|-------------|
| `update_bot_userpage_status.py` | ACTIVE | Updates `User:EmmaBot` with pipeline run metadata, workflow active/inactive status, and current stage. |

### Chunk 1: Import & Categorization

| Script | Status | Description |
|--------|--------|-------------|
| `reimport_from_enwiki.py` | ACTIVE | Downloads XML from enwiki `Special:Export` (with templates) and reimports into shintowiki with mangled timestamps to force overwrite. Fixes erroneous transclusions. 10 pages/run from `erroneous_transclusion_pages.txt`. |
| `overwrite_deleted_enwiki_pages.py` | ACTIVE | Overwrites shintowiki pages with PLACEHOLDER content when the enwiki source page no longer exists. |
| `create_wanted_categories.py` | ACTIVE | Fetches Special:WantedCategories via API and creates stub pages tagged `[[Category:Categories autocreated by EmmaBot]]`. |
| `categorize_uncategorized_categories.py` | ACTIVE | Tags category pages from Special:UncategorizedCategories with `[[Category:Categories autocreated by EmmaBot]]`. |
| `triage_emmabot_categories.py` | ACTIVE | First-pass triage: checks EmmaBot-autocreated categories against enwiki. Sorts into with-enwiki / without-enwiki subcategories. 100/run. |
| `triage_emmabot_categories_jawiki.py` | ACTIVE | Second-pass triage: checks without-enwiki categories against jawiki. 100/run. |
| `triage_emmabot_categories_secondary.py` | ACTIVE | Third-pass triage: secondary heuristics for remaining uncategorized EmmaBot categories. 100/run. |
| `triage_secondary_single_member.py` | ACTIVE | Moves single-member categories from Secondary triage to `[[Category:Triaged categories with only one member]]`. |
| `create_shrine_ranking_pages.py` | ACTIVE (TEMPORARY) | Creates article pages for shrine ranking subcategories. Remove from workflow after all pages are created. |

### Chunk 2: Structural Fixes

| Script | Status | Description |
|--------|--------|-------------|
| `delete_unused_templates.py` | ACTIVE | Deletes template pages from Special:UnusedTemplates. |
| `fix_double_redirects.py` | ACTIVE | Fixes pages listed on Special:DoubleRedirects by pointing directly to final target. |
| `resolve_double_category_qids.py` | ACTIVE | Walks `[[Category:Double category qids]]` disambiguation pages. When all listed categories resolve to the same target, replaces with a simple redirect. 100/run. |

### Chunk 3: Wikidata (paused until May 2026)

> **Note:** All Wikidata steps are paused until May 2026 via a date check in the workflow. When active, they run at 50 edits/run.

| Script | Status | Description |
|--------|--------|-------------|
| `generate_p11250_quickstatements.py` | ACTIVE | Walks `[[Category:Pages linked to Wikidata]]`, checks Wikidata P11250, and adds QuickStatements lines for items missing the property. Stateful, 100/run. |
| `clean_p11250_quickstatements.py` | ACTIVE | Reads `[[QuickStatements/P11250]]`, checks each line against Wikidata, removes lines where P11250 is now correct. 100 checks/run. |
| `tag_pages_without_wikidata.py` | ACTIVE | Walks mainspace, category, and template pages; tags those lacking `{{wikidata link}}` with `[[Category:Pages without wikidata]]`. 100 pages checked/run (bounds runtime regardless of hit rate). |
| `clean_wikidata_cat_redirects.py` | ACTIVE | Removes wikidata-related category tags from redirect pages. |

### Chunk 4: Final Core

| Script | Status | Description |
|--------|--------|-------------|
| `fix_template_noinclude.py` | DISABLED | Finds templates with `[[Category:` or `{{wikidata link` outside `<noinclude>` and wraps them properly. Disabled in workflow — one-time fix completed. |
| `categorize_uncategorized_pages.py` | ACTIVE | Tags mainspace pages from Special:UncategorizedPages with `[[Category:Uncategorized pages]]`. 100/run. |
| `tag_untranslated_japanese.py` | ACTIVE | Detects significant Japanese text outside expected contexts (templates, interwikis, refs). Tags with bucketed categories (50+ through 5000+). 100 pages checked/run. Supports `--category` for targeted re-bucketing. |

### Cleanup Loop

| Script | Status | Description |
|--------|--------|-------------|
| `delete_unused_categories.py` | ACTIVE | Deletes Special:UnusedCategories pages, skipping those with `{{Possibly empty category}}`. |
| `migrate_talk_pages.py` | ACTIVE | Rebuilds talk pages and seeds them with discussion content from ja/en/simple Wikipedia. |
| `delete_orphaned_talk_pages.py` | ACTIVE | Deletes talk pages from Special:OrphanedTalkPages whose subject page does not exist. |
| `delete_broken_redirects.py` | ACTIVE | Deletes redirects from Special:BrokenRedirects whose target page does not exist. |
| `remove_crud_categories.py` | ACTIVE | Strips `[[Category:X]]` tags from member pages across all subcategories of Category:Crud_categories. |

### Deprecated (Sunday + monthly)

| Script | Status | Schedule | Description |
|--------|--------|----------|-------------|
| `normalize_category_pages.py` | DEPRECATED | Sunday | Enforces canonical category page layout (templates / interwikis / categories). State file unchanged since Mar 1. |
| `tag_shikinaisha_talk_pages.py` | DEPRECATED | Sunday | Adds "generated from Wikidata" notice to shikinaisha talk pages. State file unchanged since Feb 26. |
| `fix_erroneous_qid_category_links.py` | DEPRECATED | 1st of month | Fixes category/QID mismatches. Category fully cleared as of Mar 12. |
| `remove_legacy_cat_templates.py` | DEPRECATED | 1st of month | Removes `{{デフォルトソート}}` and `{{citation needed}}` artifacts from category pages. State file unchanged since Mar 1. |
| `move_categories.py` | DEPRECATED | 1st of month | Moves/renames categories per `category_moves.csv`. Likely all moves complete. |
| `create_japanese_category_qid_redirects.py` | DEPRECATED | 1st of month | Creates QID redirects for Japanese-named categories. Likely all redirects created. |

---

## shinto_miraheze/ — manual-use / not in pipeline

| Script | Status | Description |
|--------|--------|-------------|
| `resolve_category_wikidata_from_interwiki.py` | LEGACY | Full pass Feb 2026. Remaining gaps require human judgment. |
| `resolve_wikidata_from_interwiki.py` | LEGACY | Main-namespace equivalent. Full pass complete. |
| `resolve_duplicated_qid_categories.py` | MANUAL | Merges CJK/Latin duplicate QID pairs. Needs human review per case. |
| `merge_japanese_named_categories.py` | MANUAL | Merges Japanese-named categories into English equivalents. Remaining entries are ambiguous. |
| `fix_ill_destinations.py` | MANUAL | Fixes broken ILL destinations. Must not be run blindly — check local context per page. |
| `resolve_missing_wikidata_categories.py` | MANUAL | Resolves Wikidata for categories missing it. Source category was cleaned out; prereq work needed. |
| `tag_missing_wikidata_with_ja_interwiki.py` | MANUAL | Tags categories missing Wikidata that have a `ja:` interwiki. Source category needs recreation. |
| `generate_shikinaisha_pages_v25_with_redirects.py` | MANUAL | Latest shikinaisha page generator. Run only when new shikinaisha data is available. |
| `populate_namespace_layers.py` | MANUAL | Copies pages to Data: and Export: namespace layers. Gated behind `--enable-namespace-layers` flag. |
| `debug_pairs.py` | MANUAL | Debug script for checking move starting points and targets. |
| `manual_import_local.py` | MANUAL | One-shot local import of pre-downloaded XML files. |
| `create_category_qid_redirects.py` | LEGACY | Creates `Q{QID}` mainspace redirects for Wikidata-linked categories. Full pass complete. |
| `fix_dup_cat_links.py` | LEGACY | Fixes duplicate category links in page wikitext. |
| `merge_by_ja_interwiki.py` | COMPLETE | Merged Japanese-named categories with English equivalents via jawiki interwiki resolution. 22 linked, 40 merged. |
| `merge_move_histories.py` | COMPLETE | Merged revision histories for matched wiki move pairs. |

---

## modern-quickstatements/ — Wikidata QuickStatements

| Script | Status | Description |
|--------|--------|-------------|
| `generate_p958_qualifiers.py` | ACTIVE | Generates P958 (section) qualifiers for P13677 (Kokugakuin Museum entry ID) statements. |
| `generate_modern_shrine_ranking_qualifiers.py` | ACTIVE | Generates P459 (determination method) qualifiers for P13723 (shrine ranking). Also handles Phase 3 migration of P31/P1552 to P13723. |
| `submit_daily_batch.py` | ACTIVE | Submits atomic QS operation files via QuickStatements API. Writes JSON run reports to `reports/`. Never exits non-zero — logs outcome and continues. |
| `test_wikidata_qualifier.py` | ACTIVE | Applies P459 qualifiers to P13723 statements via the Wikidata API directly (bypasses QuickStatements). Up to 10 edits per run. |
| `direct_daily_edits.py` | ACTIVE | Fallback: applies edits via Wikidata API directly when QuickStatements API fails. |
| `fetch_p11250_from_wiki.py` | ACTIVE | Fetches P11250 QuickStatements lines from `[[QuickStatements/P11250]]` wiki page and writes to `p11250_miraheze_links.txt` for daily batch submission. |
| `generate_run_history.py` | ACTIVE | Reads all `reports/*.json` and builds `_site/runs.html` with outcome badges and batch details. |

---

## Root directory

| Script / File | Status | Description |
|---------------|--------|-------------|
| `generate_pages.py` | ACTIVE | Generates the main GitHub Pages site (`_site/`): project overview, P11250 QuickStatements page. |
| `EmmaBot.wiki` | ACTIVE | Wiki template for `User:EmmaBot` status block. Used by `update_bot_userpage_status.py`. |

---

## Enwiki XML reimport workflow

A long-standing workflow for fixing broken templates, modules, and pages on shintowiki by reimporting them from enwiki.

**How it works:**
1. Download the XML export of a page from enwiki via `Special:Export` with "include templates" enabled and "current revision only".
2. Replace `timestamp` with `timestam` in the XML — this breaks the timestamp field so MediaWiki treats the import as having no timestamp. The import time becomes the revision timestamp, which forces an overwrite of the local revision even if it is newer than enwiki's.
3. Import the modified XML into shintowiki via `action=import`.

**Why this exists:** Shintowiki was built by mass-importing templates/modules from enwiki. Categories were manually added to imported pages because of a Miraheze indexing quirk (imported pages had non-functioning categories until one was added). This caused crud categories to leak onto templates and structural pages, breaking dependency chains. The reimport workflow pulls the entire dependency tree fresh from enwiki and overwrites local copies.

**Current implementation:** `reimport_from_enwiki.py` reads from `erroneous_transclusion_pages.txt`, processes 10 pages per pipeline run, and tracks completed pages in `reimport_from_enwiki.state`.

---

## Category triage workflow

EmmaBot-autocreated categories go through a multi-pass triage:

1. **`triage_emmabot_categories.py`** — Checks each category against enwiki. Matches → `EmmaBot categories with enwiki match`; no match → `EmmaBot categories without enwiki match`.
2. **`triage_emmabot_categories_jawiki.py`** — Checks the "without enwiki match" set against jawiki. Matches → `with jawiki match`; no match → `without enwiki or jawiki match`.
3. **`triage_emmabot_categories_secondary.py`** — Secondary heuristics for remaining categories.
4. **`triage_secondary_single_member.py`** — Single-member categories moved to `Triaged categories with only one member`.

This triage feeds into downstream cleanup decisions (keep, merge, or delete).

---

## State files and error tracking

Scripts that process large page sets use `.state` files (JSON or line-based) to track progress and resume across runs. These are committed to git after each chunk.

- `*.state` — per-script progress tracking
- `*.log` — execution logs (JSONL format)
- `*.errors` — error tracking with timestamps
- `error.log` — shared error log for all scripts

All standard scripts support `--apply`, `--max-edits`, and `--run-tag` flags to match the workflow pattern.
