# Devlog — shintowiki bot operations

Running log of all significant bot operations and wiki changes. Most recent first.

---

## 2026-04-04

### Fix GitHub Pages reverting to weeks-old content on pipeline failures
**Workflows:** `generate-pages.yml`, `generate-quickstatements.yml`
**Status:** Complete

**The bug:** When `generate-quickstatements` failed (usually SPARQL timeouts), no artifact was uploaded. The `generate-pages` workflow would then fall back to *regenerating everything from SPARQL*, which also tended to time out (10-minute limit). When that fallback also failed, no pages deployed — but when it *partially* succeeded, it deployed with incomplete data. Either way the site got stuck showing whatever last succeeded, which could be weeks old.

The subtle part: `_site/` was in `.gitignore`, so the repo never had a copy of the built pages. Every deployment had to generate them from scratch. If SPARQL was having a bad day (which was frequent — the pipeline makes 20+ queries), the pages simply couldn't be built at all.

**The fix (three parts):**
1. **Committed `_site/` to the repo** after running all generators locally. Removed `_site/` from `.gitignore`. The repo now always has a known-good copy of every page.
2. **CI commits `_site/` after each successful build.** Both `generate-quickstatements.yml` (commits generated `.txt` files, only non-empty ones so partial failures don't overwrite good data) and `generate-pages.yml` (commits the built `_site/`) push back to the repo with `[skip ci]`.
3. **Replaced the SPARQL fallback with the committed repo files.** When the artifact isn't available, `generate-pages` now just uses whatever's already checked out — no more re-querying SPARQL. Timeout increased from 10 to 30 minutes as a safety margin.

The net effect: pages can never go stale. Worst case, a failed run leaves the previously-committed version in place. Each successful run (even partial) ratchets forward.

### Add Shikinaisha removal from Shikinai Ronsha items
**Script:** `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

New generator: removes P31=Q134917286 (Shikinaisha) from items that have P31=Q135022904 (Shikinai Ronsha). Shikinai Ronsha is more specific and replaces the generic Shikinaisha class. Found 2,329 items needing cleanup. Output: `remove_shikinaisha.txt`, added to both `submit_daily_batch.py` and `direct_daily_edits.py`.

### Include P11250 Miraheze article ID in daily operations page
**Script:** `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

P11250 lines were being submitted via the daily batch but weren't shown on the HTML dashboard or daily operations page. Now included in both, with a dedicated section on the shrine ranking dashboard. Also moved the `fetch_p11250_from_wiki.py` step to run before the main generator in the workflow so the file exists when the HTML is built.

### Fix migration progress bar showing 100% with thousands of lines remaining
**Script:** `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

The Engishiki ranking migration showed "100% complete" while still generating 4,359 add lines. Root cause: the `total` SPARQL query counts old P31 statements still present, but as migration progresses and old P31 values get removed, `total` shrinks below `remaining`. This gave `completed = total - remaining = -931`, which the progress bar clamped to 100%. Fixed by using `corrected_total = max(total - remaining, 0) + remaining` so the bar always reflects actual work remaining.

---

## 2026-03-29

### Re-add retry with exponential backoff for SPARQL 429s
**Scripts:** `generate_modern_shrine_ranking_qualifiers.py`, `generate_p958_qualifiers.py`
**Status:** Complete

The bail-immediately-on-429 policy (2026-03-28) turned out to be too aggressive for the QS generators. The `generate-quickstatements` job makes 20+ SPARQL queries across all phases/migrations; by the Ritsuryō migration phase, the endpoint reliably returns 429. A single transient 429 would kill the entire pipeline.

Reverted these two scripts to retry with exponential backoff (30/60/120/240s waits, 4 retries max) and increased the base throttle from 5s to 10s between SPARQL requests. `test_wikidata_qualifier.py` still bails immediately on 429 since it hits the Wikidata API (not SPARQL) and retrying API writes is riskier.

The fix (355582e) hasn't been tested in CI yet — the run that used it (23704115295) was cancelled before reaching the SPARQL-heavy phases. The prior failure (23703150061) ran on the pre-fix commit.

### Fix stale artifact in pages build
**Workflow:** `generate-pages.yml`
**Status:** Complete

The pages build was downloading a stale artifact from the generate job instead of regenerating QS files fresh. Fixed to always regenerate in the pages build step.

---

## 2026-03-28

### Stop submit-quickstatements from regenerating SPARQL queries
The submit job was re-running all SPARQL generators (22+ queries) even though the generate job already produced the `.txt` files. This doubled SPARQL load and caused a `ReadTimeout` on the second run. Fixed by uploading generated files as artifacts from the generate job and downloading them in the submit job. No more redundant SPARQL queries.

### Submit P11250 QuickStatements via daily batch
**Script:** `fetch_p11250_from_wiki.py`
**Status:** Complete

P11250 (Miraheze article ID) QuickStatements were previously only written to a wiki page (`QuickStatements/P11250`) but never submitted automatically. Added `fetch_p11250_from_wiki.py` which reads the wiki page (public, no auth) and writes a local `p11250_miraheze_links.txt` for `submit_daily_batch.py` to pick up. Added to both the pre-flight generation and submission workflows.

### Bail-on-429 for all Wikidata scripts
**Scripts:** `test_wikidata_qualifier.py`, `generate_p958_qualifiers.py`, `generate_modern_shrine_ranking_qualifiers.py`
**Status:** Complete

We've been seeing 429 Too Many Requests from Wikidata. The root cause is unclear — may be cumulative load from multiple scripts hitting the SPARQL endpoint and Wikidata API in the same pipeline run, or external factors.

Previously, `generate_p958_qualifiers.py` and `generate_modern_shrine_ranking_qualifiers.py` would retry on 429 with backoff (30-90s waits), and `test_wikidata_qualifier.py` had **no** 429 handling at all. Retrying 429s can worsen rate-limit situations.

Changed all three scripts to match the `generate_p11250_quickstatements.py` pattern: on any 429, raise `RateLimitError` and terminate immediately. This lets us see the failure cleanly in CI logs and do diagnostics, rather than burning through retry budgets and potentially deepening the rate limit.

Wikidata chunk steps are already at 50 edits/run and paused until May, so the main exposure is `test_wikidata_qualifier.py` (100 direct API edits) and the QS generators (`generate_p958_qualifiers.py`, `generate_modern_shrine_ranking_qualifiers.py`) which query SPARQL.

---

## 2026-03-26

### Increase Wikidata step edit limits to 300
**Workflow:** `wiki-cleanup.yml`
**Status:** Complete

Raised the per-run edit limit for all four Wikidata steps from 100 to 300: `generate_p11250_quickstatements`, `clean_p11250_quickstatements`, `tag_pages_without_wikidata`, and `clean_wikidata_cat_redirects`. The global `WIKI_EDIT_LIMIT` (used by all other steps) remains at 100. This speeds up Wikidata convergence without increasing load on the wiki itself.

### Regenerate P459 missing qualifier quickstatements
**File:** `p459_missing_qualifiers.txt`
**Status:** Complete

Regenerated the P459 qualifier quickstatements from a live SPARQL query. Down to 244 remaining unqualified P13723 statements (from 382 when the file was first created on 2026-03-25).

### Fix case-sensitive TODO.md path for Linux CI
**Script:** `update_bot_userpage_status.py`
**Status:** Complete

The bookkeeping step was failing on CI (Linux) because the script defaulted to `TODO.md` but git tracks the file as `todo.md`. Windows is case-insensitive so this worked locally but broke in CI. Fixed the default path to match what git tracks.

---

## 2026-03-22

### TEMPORARY: Create shrine ranking article pages
**Script:** `create_shrine_ranking_pages.py`
**Status:** Added to workflow — remove after all pages are created

Creates article pages for all 21 subcategories of [[Category:Shrine rankings needing pages]] that don't already have articles. Uses the Gō-sha page as a template.

- 5 articles already exist: Gō-sha, Myōjin Taisha, Shikinai Shōsha, Shikinai Taisha, Son-sha
- 16 articles to create across three types:
  - **Modern system ranks** (Bekkaku Kanpeisha, Kanpei Taisha/Chūsha/Shōsha, Kokuhei Taisha/Chūsha/Shōsha, Fu-sha, Ken-sha, Fuken-sha, Unranked shrines)
  - **Engishiki offering classifications** (Hoe and Quiver, Hoe offering, Quiver offering, Tsukinami-sai+Niiname-sai, Tsukinami-sai+Niiname-sai+Ainame-sai)
- For categories with a `{{wikidata link}}`, queries Wikidata P301 (category's main topic) to get the article's QID
- 9 of 21 categories have Wikidata links; the other 12 get articles without wikidata
- Each article gets: nihongo template (where applicable), system link, See Also with category link, wikidata link (if available), and [[Category:Shrine rankings]]

**To remove after completion:** Delete the workflow step marked `(TEMPORARY)` in `cleanup-loop.yml` and optionally delete the script.

### Triage single-member categories from Secondary category triage
**Script:** `triage_secondary_single_member.py`
**Status:** Added to workflow

Walks [[Category:Secondary category triage]] and moves categories that have exactly one member into [[Category:Triaged categories with only one member]]. Early-exits member counting after 2 to avoid scanning large categories unnecessarily.

---

## 2026-03-21

### Extended untranslated Japanese character thresholds + translation pipeline plan
**Script:** `tag_untranslated_japanese.py`
**Status:** Thresholds updated; translation pipeline planned

The bucketed thresholds for tagging untranslated Japanese content previously capped at 300+, meaning pages with 500, 1000, or even 5000+ untranslated characters were all lumped into the same "300+" bucket. Extended the thresholds to: 50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000.

**Next steps (blocked on pipeline cycle completing):**
1. Let the tagging script run through the pipeline to re-bucket pages with the new thresholds
2. Triage pages starting from [[Category:Secondary category triage]] and the highest untranslated character buckets (300+, 500+, etc.)
3. Run an AI translation agent against the heavily-untranslated pages to properly translate them
4. Feed translated pages back through the pipeline for re-categorization

Added `--category` flag to `tag_untranslated_japanese.py` so it can target a specific category's members instead of walking all mainspace pages. This enables quick re-bucketing runs like:
```
python tag_untranslated_japanese.py --category "Pages with 300+ untranslated japanese characters" --apply --run-tag "..."
```
Category mode ignores the state file (always processes all members) and doesn't clear state on completion, so it won't interfere with the normal full-scan pipeline runs.

The goal is to identify the pages with the most untranslated Japanese content, translate them, and then verify via re-tagging that the translations stuck. Pages in the 300+ range and above are the priority targets since they represent substantially untranslated articles rather than minor leftover fragments.

---

## 2026-03-16

### Workflow reliability: chunked state commits and bounded runtime
**Scripts:** `cleanup_loop.sh`, `.github/workflows/cleanup-loop.yml`, `tag_pages_without_wikidata.py`
**Status:** Complete

The pipeline was failing and losing all state progress because it only committed state files once at the very end. If any script crashed midway (which was happening due to 502s and timeouts — see 2026-03-15 entry), every earlier script's state progress was thrown away.

**Chunked state commits:** The workflow now commits state/log/error files after each logical chunk instead of once at the end. Six commit points:
1. Import & Categorization
2. Structural Fixes
3. Wikidata
4. Final Core
5. Cleanup Loop
6. Deprecated (weekly)

A `commit_state()` helper in `cleanup_loop.sh` handles this — finds all `*.state`, `*.log`, `*.errors` files, stages them with `git add -f`, and commits if there are changes. Git config is now set up before the cleanup loop runs (moved out of the final push step). The final workflow step is now a fallback commit + push for anything the chunks missed.

**Bounded runtime for tag_pages_without_wikidata:** Previously `--max-edits 100` counted only pages that were actually *tagged*, meaning the script could scan thousands of pages (each with an API call) just to find 100 that needed tagging. Most pages already have `{{wikidata link}}`, so the hit rate was low and the runtime was unbounded. Changed to count pages *checked* instead of pages *edited*, so the script now stops after examining 100 pages regardless of how many needed tagging. This keeps the runtime predictable and prevents the pipeline from timing out on this single script.

Also fixed `.gitignore` which was blocking `*.log` files from being committed (the state commit step needs to track these), and added `Help:Link color` to `erroneous_transclusion_pages.txt` for reimport.

---

## 2026-03-15

### Pipeline failures: 3 consecutive CI failures diagnosed and fixed
**Script:** `shinto_miraheze/generate_p11250_quickstatements.py`, `.github/workflows/cleanup-loop.yml`
**Status:** Fixed

The pipeline failed 3 times in a row between 2026-03-14 and 2026-03-15. Root causes:

1. **Run 23081580192 (Mar 14, 05:40):** `git push` rejected — the remote had newer state file commits that the runner didn't have locally. The workflow was doing `git push` without pulling first, so when two runs produced state commits close together, the second one failed.

2. **Run 23081942775 (Mar 14, 06:02):** `502 Bad Gateway` from `shinto.miraheze.org` during recursive category traversal. The script was deep inside `get_category_pages_recursive` fetching subcategories of `天白区の歴史` (history of Tenpaku ward) when the Miraheze server returned a 502. No retry logic existed, so the entire run crashed.

3. **Run 23100572874 (Mar 15, 01:24):** `ReadTimeoutError` — same recursive category traversal, this time the server took longer than 15 seconds to respond. Again, no retry logic, immediate crash.

**Fixes applied:**

- Added `requests.Session` with automatic retry (5 retries, exponential backoff) for 500/502/503/504 errors. Timeout increased from 15s to 30s.
- Added `git pull --rebase` before `git push` in the workflow to handle state file divergence.
- 429 (Too Many Requests) is deliberately **not** retried — it triggers immediate termination with a FATAL log entry to avoid worsening rate-limit situations.
- Added `error.log` file (`shinto_miraheze/error.log`) where all errors are logged with timestamps and severity. The workflow now commits log files alongside state files, and runs the commit step with `if: always()` so logs are preserved even on failure.
- Added `*.log` to `paths-ignore` in the push trigger to avoid re-triggering the pipeline from log commits.

### ⚠️ Open concern: recursive category traversal depth
**Script:** `shinto_miraheze/generate_p11250_quickstatements.py`
**Status:** Under review

The `get_category_pages_recursive` function traverses the full subcategory tree of `[[Category:Pages linked to Wikidata]]` with no depth limit. The stack traces from the failures showed 12+ levels of recursion, reaching into deeply nested Japanese geographic/historical categories like `天白区の歴史`.

This is potentially problematic because:
- **No depth limit:** The recursion goes as deep as the category tree allows. A single deeply-nested branch can generate dozens of sequential API calls before returning.
- **No throttling on category API calls:** The script sleeps 0.3s between Wikidata checks in the main loop, but the category traversal itself makes rapid-fire requests with zero delay between them.
- **Multiplicative API load:** Each category level spawns N subcategory fetches, each of which spawns N more. A category tree 12+ levels deep with branching at each level means hundreds of API calls just to build the page list.
- **The function was part of the original script design** (commit 9d75771, 2026-03-13) — it was not added later. But the category tree has likely grown since then.

The retry logic added above makes the script more resilient to individual request failures, but does not address the underlying load pattern. If the category tree continues to grow, this could become a recurring source of 502s and timeouts — or worse, trigger rate limiting.

Possible mitigations (not yet implemented):
- Add a `max_depth` parameter to cap recursion depth
- Add throttling (e.g. `time.sleep(0.5)`) between category API calls
- Cache the page list between runs instead of rebuilding it from scratch every time
- Switch to a flat category member query if deep subcategories aren't actually needed for P11250 coverage

---

## 2026-03-13

### Orphaned talk page deletion added to cleanup loop
**Script:** `shinto_miraheze/delete_orphaned_talk_pages.py`
**Status:** Complete (pipeline integration)

Added `delete_orphaned_talk_pages.py` to the cleanup loop. Queries `Special:OrphanedTalkPages` via the querypage API and deletes talk pages whose corresponding subject page does not exist. 500+ orphaned talk pages identified at time of addition. Runs after `delete_unused_categories.py` and before `remove_crud_categories.py`.

### Enwiki XML reimport workflow automated
**Script:** `shinto_miraheze/reimport_from_enwiki.py`
**Status:** Complete (pipeline integration, bug fixed)

Automated the long-standing manual workflow of reimporting pages from enwiki to fix erroneous transclusions. The script:
1. Reads page titles from `erroneous_transclusion_pages.txt` (129 pages extracted from `[[Category:Erroneous transclusions of X]]` categories)
2. Downloads XML via enwiki `Special:Export` with `templates=1` and `curonly=1` (pulls full dependency tree)
3. Replaces `timestamp` with `timestam` in the XML to force overwrite regardless of local revision age
4. Imports into shintowiki via `action=import` with `interwikiprefix=en`

Processes 1 page per pipeline run (low priority, high cost operation). Runs as the first step of the Core Loop. Auto-retries non-namespaced titles with `Template:` prefix (e.g., "Country data X" → "Template:Country data X").

**Bug fix:** First pipeline run failed on all 129 pages — MediaWiki requires the `interwikiprefix` parameter for XML imports. Also fixed the loop to count attempts (not just successes) against `--max-imports` so it stops after 1 attempt per run.

**Historical context:** This workflow was originally performed manually and was one of the most important maintenance operations. Shintowiki was built by mass-importing templates/modules from enwiki. Categories were manually added to imported pages because of a Miraheze indexing quirk (imported pages had non-functioning categories until one was added manually). This caused crud categories to leak onto templates, modules, and structural pages, breaking template dependency chains in hard-to-diagnose ways. The indexing quirk has since been fixed on Miraheze, but the damage remains and needs cleanup.

### Secondary category triage added to core loop
**Script:** `shinto_miraheze/triage_emmabot_categories_secondary.py`
**Status:** Complete (pipeline integration)

Added `triage_emmabot_categories_secondary.py` as a third pass in the category triage pipeline, after the enwiki and jawiki passes. Handles remaining categories in `[[Category:EmmaBot categories without enwiki or jawiki match]]` using additional heuristics.

---

## 2026-03-12

### Uncategorized category fixer added to core loop
**Script:** `shinto_miraheze/categorize_uncategorized_categories.py`
**Status:** Complete (pipeline integration)

Added `categorize_uncategorized_categories.py` to the core loop. Fetches `Special:UncategorizedCategories` via the querypage API and appends `[[Category:Categories autocreated by EmmaBot]]` to each page that has no category membership.

Many category pages were created in earlier bulk workflows (consolidation, QID redirects, etc.) without any categorization. This retroactively fixes that by bringing them under the `Categories autocreated by EmmaBot` umbrella — the same category used by `create_wanted_categories.py` for newly created stubs.

### Erroneous QID category link fixes completed
**Script:** `shinto_miraheze/fix_erroneous_qid_category_links.py`
**Status:** Complete (task finished)

`Category:Erroneous qid category links` has been fully cleared. Removed from the active tasks list on `User:EmmaBot`.

### EmmaBot category triage script added to core loop
**Script:** `shinto_miraheze/triage_emmabot_categories.py`
**Status:** Complete (pipeline integration)

Added `triage_emmabot_categories.py` to the core loop. Processes up to 100 subcategories of `[[Category:Categories autocreated by EmmaBot]]` per run:
- Batch-checks English Wikipedia for a category with the same name
- If enwiki match exists: recategorizes to `[[Category:Emmabot categories with enwiki]]`
- If no match: recategorizes to `[[Category:Emmabot categories without enwiki]]`
- Removes the original `[[Category:Categories autocreated by EmmaBot]]` tag in both cases

This is the first step in a larger normalization pipeline for the many categories that were bulk-created in earlier workflows without proper documentation or categorization.

### Per-script stage declarations on User:EmmaBot
**Scripts:** `shinto_miraheze/cleanup_loop.sh`, `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete

Added `--stage` flag to `update_bot_userpage_status.py`. When used alone (without `--status`), it performs a lightweight in-place edit of the status block on `User:EmmaBot` to update only the "Current stage" line — no full page rebuild from template.

The cleanup loop now calls `declare_stage` before every script invocation, so `User:EmmaBot` always shows exactly which script is currently running (e.g. "Core Loop: create_wanted_categories", "Cleanup Loop: migrate_talk_pages"). This makes it trivial to identify where the pipeline stalls.

### Uncategorized category fixer added to core loop
**Script:** `shinto_miraheze/categorize_uncategorized_categories.py`
**Status:** Complete (pipeline integration)

Added `categorize_uncategorized_categories.py` to the core loop. Fetches `Special:UncategorizedCategories` via the querypage API and appends `[[Category:Categories autocreated by EmmaBot]]` to each page that has no category membership. Many category pages were created in earlier bulk workflows without proper categorization — this retroactively fixes them under the same umbrella category used by `create_wanted_categories.py`.

### Run tag interwiki prefix fixed
**Script:** `shinto_miraheze/cleanup_loop.sh`
**Status:** Complete

Changed edit summary run tags from `[[git:...]]` to `[[github:...]]` to match the wiki's actual interwiki prefix configuration.

### Cleanup loop restructured into Core Loop + Cleanup Loop
**Scripts/Workflow:** `shinto_miraheze/cleanup_loop.sh`, `shinto_miraheze/create_wanted_categories.py`, `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete

Restructured the flat cleanup loop into clearly separated phases with echo banners:

1. **Bookkeeping: START** — `update_bot_userpage_status.py --status active` marks the workflow as active on `User:EmmaBot`.
2. **Core Loop** — structural changes that later scripts depend on:
   - `create_wanted_categories.py` (new to loop) — dynamically fetches Special:WantedCategories and creates stub pages
   - `fix_double_redirects.py`
   - `move_categories.py`
   - `create_japanese_category_qid_redirects.py`
3. **Cleanup Loop** — category cleanup + talk pages (all 7 existing scripts, unchanged order).
4. **Bookkeeping: END** — `update_bot_userpage_status.py --status inactive` marks the workflow as done.

### create_wanted_categories.py rewritten to use dynamic API query
**Script:** `shinto_miraheze/create_wanted_categories.py`
**Status:** Complete

Replaced the hardcoded list of ~150 category names with a live query to `Special:WantedCategories` using the `querypage` API (same pattern as `delete_unused_categories.py` uses for `Unusedcategories`). Added standard CLI args: `--apply`, `--max-edits`, `--run-tag`.

The parent category was changed from `[[Category:Categories made during git consolidation]]` to `[[Category:Categories autocreated by EmmaBot]]`. These are effectively the same thing — the "git consolidation" category was an earlier iteration of the same concept (auto-creating wanted categories), just with a name tied to a specific cleanup phase. The new name is permanent and self-describing.

### update_bot_userpage_status.py gains --status flag
**Script:** `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete

Added `--status active|inactive` flag. When set, the status block on `User:EmmaBot` includes a `Workflow status: '''active'''` or `'''inactive'''` line. Called at both start and end of the cleanup loop to show whether the bot is currently running.

---

## 2026-03-01

### Double redirect fixer added to cleanup loop
**Script:** `shinto_miraheze/fix_double_redirects.py`
**Status:** Complete (pipeline integration)

Added `fix_double_redirects.py` to the cleanup loop as the first cleanup step. Queries `Special:DoubleRedirects` and updates each redirect to point directly to the final target, eliminating intermediate hops. Runs before all other cleanup scripts so downstream steps see correct redirect targets.

---

## 2026-02-28

### Category move script and Japanese→English translations
**Scripts:** `shinto_miraheze/move_categories.py`, `shinto_miraheze/category_moves.csv`
**Status:** Complete (pipeline integration)

Added `move_categories.py` which reads a CSV of (source, destination) category pairs and performs moves: recategorizes all members then moves the category page. Skips sources that are already redirects or have `{{category move error}}`; tags conflicts where both source and destination already exist.

Added `category_moves.csv` with ~295 Japanese→English category translations covering:
- Building and history categories for various Japanese municipalities
- Japanese cultural and historical categories (shrines, temples, ancient relations)
- Taiwan-related historical and cultural categories
- Year/century-based categories, regional categories, template categories, WikiProject categories

### Japanese category QID redirect script added to cleanup loop
**Script:** `shinto_miraheze/create_japanese_category_qid_redirects.py`
**Status:** Complete (pipeline integration)

Added `create_japanese_category_qid_redirects.py` to handle a race condition where Japanese-named categories may not have proper QID redirects. For every category in `[[Category:Japanese language category names]]` with `{{wikidata link|Q...}}`: creates `Q{QID}` mainspace redirects, and handles duplicate QIDs by creating disambiguation pages tagged with `[[Category:double category qids]]`. Runs in the cleanup loop immediately after `move_categories.py`.

---

## 2026-02-27

### Legacy category template remover added to cleanup loop
**Script:** `shinto_miraheze/remove_legacy_cat_templates.py`
**Status:** Complete (pipeline integration)

Added `remove_legacy_cat_templates.py` to the cleanup loop. Strips `{{デフォルトソート:…}}` and `{{citation needed|…}}` artifacts from Category: namespace pages, with state file resumability and standard `--apply`/`--max-edits`/`--run-tag` interface.

Also fixed run-tag format in the same commit: switched from external link syntax `[https://... text]` to interwiki syntax `[[git:path|text]]` so edit summary links render correctly on the wiki.

---

## 2026-02-27

### CI-first operating policy declared
**Status:** Active policy

Operational policy is now explicit across docs and bot-page content:
- Emma Leonhart will not run normal mass-edit jobs from a local machine.
- Routine and major bot operations are to be executed via GitHub Actions by editing repository code/workflows.
- Local manual script execution is reserved for emergency intervention only.

### GitHub Actions bot-password pipeline rollout
**Scripts/Workflow:** `.github/workflows/cleanup-loop.yml`, `shinto_miraheze/cleanup_loop.sh`, `shinto_miraheze/update_bot_userpage_status.py`
**Status:** Complete (pipeline implementation)

Implemented full Ubuntu GitHub Actions execution for the active cleanup loop with bot-password credentials:
- Trigger modes: push, daily schedule (`00:00 UTC`), and manual dispatch
- Authentication model: `WIKI_USERNAME` variable (`MainUser@BotName`) + `WIKI_PASSWORD` secret
- Persistent state: `*.state` files are committed back to the branch after successful runs
- Loop protection: state-only commits do not retrigger the workflow (`paths-ignore: **/*.state`)

Added run-start status reporting:
- Bot updates `[[User:EmmaBot]]` at run start
- Uses `EmmaBot.wiki` as baseline content and appends/replaces a machine-managed status block
- Records UTC start time, trigger cause (push/schedule/manual), and workflow run URL

Added run-size limiting for timeout control:
- `WIKI_EDIT_LIMIT=1000` configured in workflow
- Active cleanup scripts now support `--max-edits` and stop after reaching the cap
- Cap is passed by `cleanup_loop.sh` into:
  - `normalize_category_pages.py`
  - `migrate_talk_pages.py`
  - `tag_shikinaisha_talk_pages.py`
  - `remove_crud_categories.py`
  - `fix_erroneous_qid_category_links.py`

Operational note:
- `remove_crud_categories.py` and `migrate_talk_pages.py` are expected to require multiple daily runs over several days due to scale.

### Unused category deletion added to active loop
**Script:** `shinto_miraheze/delete_unused_categories.py`
**Status:** Complete (pipeline integration)

Added automatic deletion of categories from Special:UnusedCategories as the first cleanup task in the CI loop.

Safeguard:
- If a category page contains `{{Possibly empty category}}`, the bot skips deletion.

Rationale:
- With crud categories being trimmed, unused category pages now need active cleanup to complete the consolidation phase.

### Active script credential override migration
**Scripts:** `shinto_miraheze/*.py` (active scripts)
**Status:** Complete for active scripts

Migrated active scripts from fixed credentials to environment-variable override pattern:
- `USERNAME = os.getenv("WIKI_USERNAME", ...)`
- `PASSWORD = os.getenv("WIKI_PASSWORD", ...)`

This keeps legacy fallback behavior locally while enabling secure CI credential injection.

### Local cleanup loop orchestration baseline
**Scripts:** `shinto_miraheze/cleanup loop.bat`, `shinto_miraheze/fix_erroneous_qid_category_links.py`
**Status:** Complete

Added a Windows launcher (`cleanup loop.bat`) that opens separate command sessions for the active cleanup jobs and now serves as the local orchestration baseline for the later bot CI/CD pipeline.

Also added `fix_erroneous_qid_category_links.py`, which processes pages in `Category:Erroneous_qid_category_links` and converts pages to simple redirects when all listed category targets are the same.

### Category:Q{QID} pages in wrong namespace resolved
**Status:** Complete — ~77 pages

Approximately 77 pages existed in the Category namespace as `Category:Q{QID}` (wrong namespace). These were resolved by deleting or moving them to mainspace as `Q{QID}` redirects pointing to the correct category.

---
## 2026-02-26

### Category page wikitext normalization
**Script:** `shinto_miraheze/normalize_category_pages.py` (new)
**Status:** Complete â€” **23,571 edited, 474 skipped, 0 errors**

Normalized all 24,045 non-redirect category pages to a clean three-section structure:

```
<!--templates-->
{{wikidata link|Qâ€¦}} etc.
<!--interwikis-->
[[ja:â€¦]] [[en:â€¦]] etc.
<!--categories-->
[[Category:â€¦]]
```

Strips all free text, stray headings, Japanese prose, and any other content accumulated from previous automated passes. Added state file (`normalize_category_pages.state`) and JSONL log (`normalize_category_pages.log`) so the script is safe to re-run without re-processing completed pages.

### Deletion of Category:Jawiki_resolution_pages
**Script:** `shinto_miraheze/delete_jawiki_resolution_pages.py`
**Status:** Complete â€” **10,239 pages deleted**

Deleted all pages in `Category:Jawiki_resolution_pages`. These were stub pages created during earlier jawiki import passes that served no ongoing purpose. Deletion was performed in bulk via the bot account. Category is now empty.

### Imported Kuni no Miyatsuko pages
I imported all of the Kuni no Miyatsuko pages from jawiki, this is something that needed to be complete, and leaving it partway filled was causing issues. They still need to be translated and normalized and deduplicated.

---

## 2026-02-23

### History merge â€” `{{moved to}}` / `{{moved from}}` pairs
**Scripts:** `shinto_miraheze/merge_move_histories.py` (new), `shinto_miraheze/tag_move_link_quality.py` (new), `shinto_miraheze/tag_move_intersection.py` (new)
**Status:** Complete â€” **184 pairs merged, 0 errors**

Completed the full-history merge for all matched move pairs. For each pair (A = old name, B = new name):
1. B's content saved (with `{{moved from}}` stripped)
2. B deleted â†’ revisions enter the deleted archive
3. A moved to B's title â†’ B's title now holds A's revision history
4. B's content pasted onto the page at B's title
5. B's archived revisions undeleted â†’ histories merge chronologically at B's title

Also introduced three maintenance categories populated by bot:
- `Category:moved from a redlink` â€” `{{moved from|X}}` where X doesn't exist
- `Category:moved to a redlink` â€” `{{moved to|X}}` where X doesn't exist
- `Category:moved from a non-redirect` â€” `{{moved from|X}}` where X exists but is not a redirect
- `Category:Move targets âˆ© destinations` â€” pages with both templates (edge cases needing manual resolution)
- `Category:move templates that do not link to each other` â€” pages whose templates form a contradictory/mismatched pair (7 pages; needs manual review)

History fully preserved for all 184 merged pages. Marginal exceptions: the 7 pages in the error category, plus the pre-existing âˆ© cases that were cleared manually.

---

## 2026-02-20

### ja: interwiki category merge and QID linking
**Script:** `shinto_miraheze/merge_by_ja_interwiki.py` (new)
**Status:** Complete â€” **22 linked, 40 merged, 0 errors**
Scans all 834 categories in [Category:Categories missing Wikidata with Japanese interwikis](https://shinto.miraheze.org/wiki/Category:Categories_missing_Wikidata_with_Japanese_interwikis). Builds a map of jawiki target â†’ shintowiki categories, then:

- **Single match** â€” queries jawiki API for the QID, creates a `Q{QID}` redirect page and adds `{{wikidata link|Q...}}` to the category (same flow as `resolve_missing_wikidata_categories.py`)
- **One CJK + one Latin sharing same jawiki target** â€” merges: recategorizes all members from the CJK category into the Latin one, redirects the CJK category, then adds the wikidata link to the Latin category
- **Two or more Latin sharing same jawiki target** â€” tags all with `[[Category:jawiki categories with multiple enwiki]]` for manual review

Results: 754 singles (22 linked, 732 skipped â€” no jawiki QID), 40 shared-target groups (all clean CJK+Latin pairs, all merged). 0 tagged-multi cases, 0 errors.

---

## 2026-02-19

### Tagging categories missing Wikidata but with Japanese interwikis
**Script:** `shinto_miraheze/tag_missing_wikidata_with_ja_interwiki.py` (new)
**Status:** Complete â€” **834 categories tagged**, 4209 skipped (no ja: interwiki), 0 errors
Scans all members of Category:Categories_missing_wikidata for `[[ja:...]]` interwiki links in their wikitext. Tags any that have one with `[[Category:Categories missing Wikidata with Japanese interwikis]]`. This intermediate categorization step makes it easy to later batch-process that subset: the ja: link provides a direct path to the jawiki category, from which the QID can be retrieved.

### Missing Wikidata link resolution
**Script:** `shinto_miraheze/resolve_missing_wikidata_categories.py` (new)
**Status:** Complete
For every category in [Category:Categories_missing_wikidata](https://shinto.miraheze.org/wiki/Category:Categories_missing_wikidata): queries the English or Japanese Wikipedia API (enwiki for Latin names, jawiki for CJK names, with fallback to the other) for `Category:{name}` and retrieves the `wikibase_item` QID from pageprops. If found:

- **Q page doesn't exist on shintowiki** â†’ create `Q{QID}` as `#REDIRECT [[Category:Name]]` and add `{{wikidata link|Q...}}` to the category page
- **Q page redirects to this same category** â†’ just add `{{wikidata link|Q...}}` to the category page
- **Q page redirects to a different English category** â†’ merge (recategorize members + redirect this category), same logic as `merge_japanese_named_categories.py`
- **Q page is a disambiguation list** â†’ skip

Result: **2425 actionable** out of 5054 checked â€” 2410 Q pages created + wikidata links added, 4 wikidata links added to existing Q-linked categories, 11 merges into English equivalents. 2629 skipped (no Wikipedia equivalent found). 0 errors.

### Japanese-named category merges
**Script:** `shinto_miraheze/merge_japanese_named_categories.py` (new)
**Status:** Complete
For every category in [Category:Japanese_language_category_names](https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names): finds the `{{wikidata link|Q...}}` on the category page, looks up the Q{QID} mainspace page, and if that Q page is a simple `#REDIRECT [[Category:EnglishName]]` to a non-CJK category, recategorizes all members from the Japanese-named category to the English one and redirects the Japanese category page.

Skips if: no wikidata link, Q page doesn't exist, Q page redirects back to a CJK name (no English equivalent on this wiki yet), or Q page is a disambiguation list (handled separately by `resolve_duplicated_qid_categories.py`).

Result: **1274 categories merged** out of 2417 checked (ran in two passes â€” first pass crashed at 84 on edit conflict with concurrent crud script; second pass completed remaining 1190 cleanly with 0 errors).

### [[sn:...]] interwiki link removal
**Script:** `shinto_miraheze/remove_sn_interwikis.py` (new)
**Status:** Complete
Strips all `[[sn:...]]` links from every page on the wiki. These were accidentally used as a note-storage mechanism during earlier bot passes â€” e.g. `[[sn:This category was created from JAâ†’Wikidata links on Fuse Shrine (Sanuki, Kagawa)]]`. The `sn` language code produces meaningless interwiki links and serves no purpose. Uses `insource:"[[sn:"` full-text search to find affected pages (the `list=alllanglinks` API module is not available on Miraheze), then strips the pattern from each.

Result: 1 page affected ([Help:Searching](https://shinto.miraheze.org/wiki/Help:Searching)), 3 links removed. The minimal footprint confirms these were all added during a single earlier pass.

### Crud category cleanup
**Script:** `shinto_miraheze/remove_crud_categories.py` (new)
**Status:** Running (two instances â€” original + second pass for subcategories added during runtime)
Fetches all subcategories of [Category:Crud_categories](https://shinto.miraheze.org/wiki/Category:Crud_categories) and strips those category tags from every member page. Goal is to leave all the crud subcategories empty. These were leftover maintenance/tracking categories accumulated from various automated passes that serve no ongoing purpose.

21 subcategories identified in the original run. The script caches the subcategory list at start and fetches members live per subcategory. A second instance was started to catch any new subcategories added to Category:Crud_categories during the first run's execution. By far the slowest script this session â€” the first subcategory alone (Category:11) had 1568 members. The individual-edit-per-page approach is suboptimal for bulk cleanup but is intentional and generative; the slow pace is not considered an error.

### Duplicate QID category resolution
**Script:** `shinto_miraheze/resolve_duplicated_qid_categories.py` (new)
**Status:** Partially complete â€” 146/221 processed; needs re-run for remainder
Processes all Q{QID} pages in [Category:Duplicated qid category redirects](https://shinto.miraheze.org/wiki/Category:Duplicated_qid_category_redirects). These are QID redirect pages where two categories â€” one with a Japanese name and one with an English name â€” share the same Wikidata QID, meaning they are the same category under two names.

Logic:
- **CJK name + Latin name pair** (e.g. `Category:ä¸Šé‡Žå›½` + `Category:KÅzuke Province`): recategorizes all members from the CJK category to the Latin/English one, redirects the CJK category page to the Latin one, and converts the Q page to a simple `#REDIRECT [[Category:LatinName]]`.
- **Both Latin names**: cannot auto-resolve â€” tags the Q page with `[[Category:Erroneous qid category links]]` for manual review.

Run crashed at Q8976949 (Category:ä¸€å®® â†’ Category:Ichinomiya, 36 members) with an edit conflict â€” concurrent editing with the crud cleanup script. 146 Q pages were fully resolved before the crash. Re-run will skip already-resolved pages since they no longer appear in the category.

### Wanted categories created
**Script:** `shinto_miraheze/create_wanted_categories.py` (new, ran this session)
**Status:** Complete
Created 153 category pages that had members but no page (showed up in Special:WantedCategories). Each got `[[Category:categories made during git consolidation]]`. [Category:Duplicated qid category redirects](https://shinto.miraheze.org/wiki/Category:Duplicated_qid_category_redirects) got special documentation explaining the Q-page format and how to resolve entries. Parent category [Category:categories made during git consolidation](https://shinto.miraheze.org/wiki/Category:Categories_made_during_git_consolidation) also created.

### Repository consolidation
- Moved all root-level scripts into `shinto_miraheze/`
- Deleted `aelaki_miraheze/` (project abandoned)
- Deleted `archive/` directory (544 files; all preserved in git history)
- Added `todo.md`, `HISTORY.md`, `DEVLOG.md` to repo
- Cleaned up README (removed speech-to-text dump, replaced with proper docs)

---

## 2026-02-19 (earlier â€” previous Claude session, interrupted by system crash)

### DEFAULTSORT removal from shikinaisha pages
**Script:** `shinto_miraheze/remove_defaultsort_digits.py`
**Status:** Complete
Removed `{{DEFAULTSORT:â€¦}}` from all pages in `Category:Wikidata generated shikinaisha pages`. These were auto-generated by an earlier script and served no purpose.

### Category Wikidata link addition
**Script:** `shinto_miraheze/resolve_category_wikidata_from_interwiki.py`
**Status:** Complete (full pass Feb 2026)
Added `{{wikidata link|Qâ€¦}}` to all category pages that had interwiki links but no Wikidata connection. Used interwiki links to look up QIDs.

### QID redirect creation for categories
**Script:** `shinto_miraheze/create_category_qid_redirects.py`
**Status:** Complete (ran concurrently with above â€” possible race condition artifacts, scope unknown)
Created `Q{QID}` mainspace redirect pages for all categories with `{{wikidata link}}`. Where two categories shared a QID, created a numbered disambiguation list and tagged with `[[Category:Duplicated qid category redirects]]`.

### Duplicate category link fix
**Script:** `shinto_miraheze/fix_dup_cat_links.py`
**Status:** Complete (one-off)
Fixed `[[Category:X]]` â†’ `[[:Category:X]]` in the dup-disambiguation Q pages. An earlier run of the QID redirect script had accidentally created category tags instead of category links in those pages.

---

## 2025 â€” Shikinaisha project

### Mass shikinaisha page generation
**Script:** `shinto_miraheze/generate_shikinaisha_pages_v24_from_t.py` (and earlier versions)
Generated wiki pages for shikinaisha (å¼å†…ç¤¾ â€” shrines listed in the Engishiki) from Wikidata. Earlier versions used ChatGPT translation; later versions used Claude. Pages were generated with Japanese Wikipedia content imported and translated.

### Shikinaisha data upload to Wikidata
Multiple scripts (now in git history) ran in Juneâ€“July 2025 to:
- Import shrine ranks from Japanese Wikipedia categorization into Wikidata
- Import shikinaisha entries from Japanese Wikipedia list pages (via Excel intermediary)
- Import from Kokugakuin University shrine database (caused many duplicate entries â€” significant WikiProject Shinto backlash, but data was not removed)

### ILL destination fixing
**Script:** `shinto_miraheze/fix_ill_destinations.py`
Multiple passes to fix `{{ill}}` template `1=` destinations using the QID redirect chain. See `SHINTOWIKI_STRUCTURE.md` for the resolution priority order.

---

## 2024â€“2025 â€” Category and interwiki passes

Various scripts (archived in git history) ran to:
- Add interwiki links to categories and main namespace pages from Wikidata
- Add Wikidata labels in multiple languages (Dutch, French, German, Indonesian, Turkish, etc.)
- Sync category interwiki links across Wikipedia editions (ja, de, zh, en)
- Add P31 (instance of) categories in bulk
- Generate and update shrine descriptions

---

## 2024 â€” Wiki restoration

Wiki was suspended by Miraheze and then reinstated. Restored from XML export obtained via Archive.org. Only most recent revision of each page was imported (not full history). Full history import is pending on Miraheze's side.

`{{moved to}}` and `{{moved from}}` templates introduced to preserve attribution across the two waves of page moves that occurred around this time.

---

## 2023â€“2024 â€” Wiki founding and initial imports

Wiki founded at shinto.miraheze.org. Initial pages imported from:
- English Wikipedia drafts (user was permanently blocked from enwiki December 2023)
- Simple English Wikipedia user pages (used as temporary holding space)
- Everybody Wiki

Early content workflow: ChatGPT translation of Japanese Wikipedia pages, with `{{ill}}` templates added for all links. All links on the wiki use `{{ill}}` â€” no bare wikilinks to other wikis.

Repository initially created for Wikidata edits. First major project: documenting Beppu shrines and Association of Shrines special-designation shrines.


