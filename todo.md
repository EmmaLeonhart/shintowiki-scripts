# Todo

Consolidated list of open tasks. Historical/completed work is tracked in [DEVLOG.md](DEVLOG.md). See [VISION.md](VISION.md) for the broader architecture plan.

---

## Current session work

Active work queue lives in [status.md](status.md) (Sutra-style queue — items are deleted when done). This file (`todo.md`) is the long-horizon backlog.

## Scheduled review — July 2026

- [ ] **Audit terminating cleanup scripts** — all per-page "cycling" operations have been moved into the three namespace orchestrators (`mainspace_orchestrator.py`, `category_orchestrator.py`, `template_orchestrator.py`). The following scripts in `wiki-cleanup.yml` are **terminating** — they have state files but don't reset at the end of a sweep, so once their state covers every eligible page they simply do nothing on subsequent runs. In July 2026, check each one's state/log to confirm it has stopped producing edits; if so, remove the step from `wiki-cleanup.yml` and delete the script:
  - `reimport_from_enwiki.py` (input-file driven; state shows it is already effectively complete)
  - `migrate_talk_pages.py`
  - `normalize_category_pages.py` (Sunday only)
  - `remove_legacy_cat_templates.py` (monthly)

## Server load (emerging concern — 2026-04-18)

Miraheze has raised server-load concerns. All scripts should minimize read/write volume against `shinto.miraheze.org`:
- Prefer running stateful scripts at their existing `--max-edits` caps; do not bump caps without reason.
- Do not add new loops that walk full namespaces unless there is a dedicated reason and a state file to bound per-run work.
- SPARQL/Wikidata-side bail-on-429 policy (2026-03-28) remains in force; some generators use exponential backoff (2026-03-29) only when strictly necessary.
- Before adding a new automated step to `wiki-cleanup.yml`, justify it against this constraint.

## Automation boundary

The GitHub Actions pipeline (8 reusable workflows orchestrated by `.github/workflows/cleanup-loop.yml`, runs daily + on push) handles everything that can be scripted safely and repeatably. State files are committed incrementally after each chunk (Import & Categorization, Structural Fixes, Wikidata, Final Core, Cleanup Loop, Deprecated) so progress is not lost if a later chunk fails. After the wiki cleanup, QuickStatements are submitted to Wikidata, P459 qualifiers are applied via direct API, and a run history page is rebuilt. **Everything outside the loop requires manual intervention.** The remaining open tasks all require human judgment, prereq work, or infrastructure that does not yet exist.

Dashboard: [emmaleonhart.github.io/shintowiki-scripts](https://emmaleonhart.github.io/shintowiki-scripts/) — includes [run history](https://emmaleonhart.github.io/shintowiki-scripts/runs.html) for QS submissions.

**429 policy (as of 2026-03-28):** All scripts that hit Wikidata (SPARQL or API) bail immediately on HTTP 429 — no retries. This avoids worsening rate-limit situations. Check CI logs for `RateLimitError` if a step fails unexpectedly.

### Currently automated (cleanup loop)

These run automatically every 24 hours via GitHub Actions. No manual action needed unless something breaks.

**Bookkeeping** (start & end of loop):
- **Bot userpage status** — `update_bot_userpage_status.py`: marks workflow active at start, inactive at end, and updates `User:EmmaBot` with run metadata.

**Core Loop** (structural changes that later scripts depend on):
- **Enwiki XML reimport** — `reimport_from_enwiki.py`: downloads XML export from enwiki (with templates, current revision) and reimports into shintowiki with mangled timestamps to force overwrite. Fixes erroneous transclusions by pulling the full dependency tree. Processes 10 pages per run from `erroneous_transclusion_pages.txt`. Failed imports are logged to `reimport_from_enwiki.errors`. **Current state:** all 17 pages in the current list have been processed (state file complete). Remaining pages are all Module doc pages that cause CI hangs — these were manually imported locally. The script will idle until new pages are added to the list.
- **Wanted category creation** — `create_wanted_categories.py`: fetches Special:WantedCategories via API and creates stub pages tagged `[[Category:Categories autocreated by EmmaBot]]`.
- **Uncategorized category fix** — `categorize_uncategorized_categories.py`: adds `[[Category:Categories autocreated by EmmaBot]]` to category pages from Special:UncategorizedCategories that were created in earlier bulk workflows without proper categorization.
- **EmmaBot category triage (enwiki)** — `triage_emmabot_categories.py`: checks autocreated categories against enwiki; moves to `[[Category:Emmabot categories with enwiki]]` or `[[Category:Emmabot categories without enwiki]]` (100 per run).
- **EmmaBot category triage (jawiki)** — `triage_emmabot_categories_jawiki.py`: second pass on without-enwiki categories; checks jawiki; moves to `[[Category:Emmabot categories with jawiki]]` or `[[Category:Emmabot categories without enwiki or jawiki]]` (100 per run).
- **EmmaBot category triage (secondary)** — `triage_emmabot_categories_secondary.py`: third pass on remaining categories using additional heuristics.
- **Triage single-member categories** — `triage_secondary_single_member.py`: walks `[[Category:Secondary category triage]]` and moves categories with exactly one member into `[[Category:Triaged categories with only one member]]`.
- **Unused template deletion** — `delete_unused_templates.py`: deletes template pages from Special:UnusedTemplates.
- **Double redirect fixes** — `fix_double_redirects.py`: fixes pages listed on Special:DoubleRedirects.
- **Resolve double category QIDs** — `resolve_double_category_qids.py`: walks `[[Category:Double category qids]]` disambiguation pages; when all listed categories resolve to the same final target (one is a redirect to the other), replaces the disambiguation page with a simple redirect. Part of a multi-step cleanup of duplicate QID disambiguation pages. 100 per run.
- **P11250 QuickStatements** — `generate_p11250_quickstatements.py`: walks direct members of `[[Category:Pages linked to Wikidata]]`, checks Wikidata P11250, and adds QuickStatements lines to `[[QuickStatements/P11250]]` for items missing the property. Stateful, 300 per run. Has retry logic with automatic 429 termination and error logging to `error.log`.
- **Tag pages without wikidata** — `tag_pages_without_wikidata.py`: walks all pages in mainspace, category space, and template space; tags pages lacking `{{wikidata link}}` with `[[Category:Pages without wikidata]]`. Stateful, 300 pages *checked* per run (not 300 edited — bounds runtime regardless of hit rate).
- **Clean P11250 QuickStatements** — `clean_p11250_quickstatements.py`: reads `[[QuickStatements/P11250]]`, checks each line against Wikidata, and removes lines where the item now has the correct P11250 value. 300 checks per run.
- **Clean wikidata category redirects** — `clean_wikidata_cat_redirects.py`: cleans up wikidata-related category redirects. 300 per run.
- **Fix noinclude on templates** — `fix_template_noinclude.py`: finds templates with `[[Category:` or `{{wikidata link` outside `<noinclude>` blocks and wraps them properly. Tags fixed templates with `[[Category:Templates fixed with noinclude]]`. 100 per run.
- **Categorize uncategorized pages** — `categorize_uncategorized_pages.py`: fetches `Special:UncategorizedPages` and tags them with `[[Category:Uncategorized pages]]`. 100 per run.
- **Tag untranslated Japanese content** — `tag_untranslated_japanese.py`: walks all mainspace pages and detects significant Japanese text (hiragana, katakana, CJK ideographs) outside of templates, interwiki links, refs, and other expected contexts. Tags pages with `[[Category:Pages with untranslated japanese content]]`. 100 pages checked per run. Prerequisite for the namespace layer work.

**Cleanup Loop** (category cleanup + talk pages):
- **Unused category deletion** — `delete_unused_categories.py`: deletes Special:UnusedCategories pages, skipping any with `{{Possibly empty category}}`.
- **Orphaned talk page deletion** — `delete_orphaned_talk_pages.py`: deletes talk pages from Special:OrphanedTalkPages whose subject page does not exist.
- **Talk page migration** — `migrate_talk_pages.py`: rebuilds talk pages and seeds them with discussion content from ja/en/simple Wikipedia. State file: `shinto_miraheze/migrate_talk_pages.state`.
- **Broken redirect deletion** — `delete_broken_redirects.py`: deletes redirects from Special:BrokenRedirects whose target page does not exist.
- **Crud category cleanup** — `remove_crud_categories.py`: strips `[[Category:X]]` tags from member pages across all subcategories of Category:Crud_categories.

**Wikidata (QuickStatements + direct API)**:
- **P11250 Miraheze links** — `fetch_p11250_from_wiki.py` + `submit_daily_batch.py`: fetches P11250 QS lines from `[[QuickStatements/P11250]]` wiki page and submits via QuickStatements API.
- **P958 qualifiers** — `generate_p958_qualifiers.py` + `submit_daily_batch.py`: generates and submits P958 (section) qualifiers for P13677 (Kokugakuin Museum entry ID) via QuickStatements API. Bails immediately on 429 (as of 2026-03-28).
- **P459 qualifiers** — `test_wikidata_qualifier.py`: applies P459 (determination method) qualifiers to P13723 (shrine ranking) statements via direct Wikidata API. 100 edits per run. ~244 remaining as of 2026-03-26 — should complete within a few days. Bails immediately on 429 (as of 2026-03-28).

**Temporary** (remove after completion):
- **Shrine ranking page creation** — `create_shrine_ranking_pages.py`: creates article pages for subcategories of `[[Category:Shrine rankings needing pages]]`. Remove from workflow after all 21 pages exist (5 already existed, 16 to create).

### Temporary / one-off re-bucketing tasks

- [x] **Re-bucket 300+ untranslated pages with extended thresholds** — Added as temporary step `rebucket_300plus_untranslated` in cleanup loop (2026-04-03). Runs `tag_untranslated_japanese.py --category "Pages with 300+ untranslated japanese characters"` to re-bucket 72 pages into finer-grained categories (up to 5000+). Remove step from workflow after all pages are re-bucketed.
- [ ] **Strip untranslated character-count categories from already-translated pages** — inverse of `tag_untranslated_japanese.py`. Tracked in `status.md` as task 1.
- [ ] **AI translation pipeline on high-bucket pages** — Once re-bucketing is done, use the highest buckets (1000+, 2000+, etc.) to identify pages that are essentially untranslated. Run an AI translation agent against these. Also cross-reference with [[Category:Secondary category triage]] for prioritization. Blocked on re-bucketing completing first.

### Requires manual intervention

- [ ] **Figure out `replace_p1027_with_p459.txt`** — This file exists in `modern-quickstatements/` but it's unclear what it does, whether it's still needed, or whether it was ever submitted. Investigate its origin and purpose; remove or integrate into the pipeline as appropriate.
- [ ] **Template:Talk page header** — Edit this template so that it fits all requirements for migrated/transformed talk pages.
- [ ] **Translate the remaining untranslated `need_translation/` pages.** ~290 files still carry `[[Category:Need translation]]`. Nine large kokuzo articles are the priority: `国造.wiki` (8669 CJK), `无邪志国造.wiki` (5141), `出雲国造.wiki` (4527), `千葉国造.wiki` (1763), `尾張国造.wiki` (1640), `倭国造.wiki` (1346), `廬原国造.wiki` (982), `斐陀国造.wiki` (854), `伊勢国造.wiki` (841). 83 files are shrine pages with `== Japanese Wikipedia content ==` sections (auto-generated English top + Japanese body). Translate using `{{ill|English|ja|Japanese|lt=Display|lt_ja=Japanese Display}}` per `feedback_translation_link_rules.md` in memory. Never remove `[[Category:Need translation]]` without verifying the body is actually English — CI deletes the file from the repo when the category is gone.
  - **Prerequisite — do NOT start this until history offloading is complete for these pages.** The `history_offload` op (running across all four orchestrators, gated on `ENABLE_HISTORY_OFFLOAD=1` in cleanup-loop.yml) needs to have archived and truncated the revision history of each candidate page before translation-driven edits pile new revisions on top. Translating first would force the archive + revdel step to re-archive a longer history than necessary and dilutes the "converge to one surviving revision" property described in `ops/history_offload.py`. Check `shinto_miraheze/orchestrators/duplicate_qids.state` and the archive repo to confirm coverage before unblocking this task.
- [ ] **Enrich autocreated categories** — Write a script to add meaningful content (interwikis, wikidata links, parent categories) to pages in `Category:Categories autocreated by EmmaBot` that were created as stubs.
- [ ] **Special:WantedPages and Special:WantedTemplates** — Planning to do something with these eventually, but not sure what yet. Waiting until the category pipeline is solid before tackling.

---

## Wiki content tasks (on shintowiki)

All items below require manual editing or human review. None have a safe automated path right now.

### High priority

- [x] **Fix template categories outside `<noinclude>`** — now automated via `fix_template_noinclude.py` in the cleanup loop.
- [x] **Resolve migration issues in Category:Erroneous qid category links** — fully cleared 2026-03-12.
- [ ] **ILLs without `WD=`** — ILL templates missing a `WD=` parameter are broken by design. Run `fix_ill_destinations.py` or a new script to identify and fill in missing `WD=` values. Do not blindly overwrite — check the local context of each.
- [ ] **Duplicate QID disambiguation pages** — 621 `Q{QID}` mainspace pages point to 2+ categories. Multi-step cleanup in progress: (1) `resolve_double_category_qids.py` now automates the easy cases where all listed categories resolve to the same target (now in cleanup loop). (2) Remaining pages where categories point to genuinely different targets still need human review. Also applies to `[[Category:duplicated qid category redirects]]`.
- [ ] **Translate all category names in [Category:Japanese language category names](https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names)** — ensure every category in this tracking set is migrated to a canonical English category title.
- [ ] **[Category:Pages with duplicated content](https://shinto.miraheze.org/wiki/Category:Pages_with_duplicated_content)** — pages where the same content exists under multiple titles. Needs human review per page: which title is canonical, whether a history merge is appropriate.
- [ ] **Audit category pages for race-condition artifacts** — some categories may have inconsistent state from the `resolve_category_wikidata` and `create_category_qid_redirects` scripts running concurrently. Scope unknown; needs an audit script.
- [ ] **Review post-audit leftovers** - many entries in https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names appear to be downstream artifacts; verify whether any automated cleanup is still needed.

### Lower priority

- [ ] **Recreate `Category:Categories_missing_wikidata`** — the original category was not accurately applied and was cleaned out as a crud category. Needs to be recreated with accurate membership, then split into two typed subcategories: (1) categories missing interwikis entirely, and (2) categories with valid interwikis but no Wikidata link yet.
- [ ] **Categories with interwikis but no Wikidata link added** — older script passes added interwiki links without adding the `{{wikidata link}}` template. Re-run the wikidata link script on these.
- [ ] **Multiple `{{wikidata link}}` on one page** — usually indicates a Wikidata disambiguation issue. Needs per-case review.
- [ ] **Shikinaisha pages with broken ILL destinations** — ILLs pointing to "Unknown" as target from early workflow. Most are identifiable from context; fix with `fix_ill_destinations.py` pass.
- [x] **Remove legacy category-page fix templates** — automated via `remove_legacy_cat_templates.py` in the deprecated loop. State unchanged since 2026-03-01 (effectively complete).

---

## Repository / script tasks

### Secret removal (run soon, before open-source release)

- [ ] **Rotate exposed credentials first** — treat any historical plaintext credentials as compromised and rotate them before/alongside history rewrite.
- [ ] **Rewrite git history to remove sensitive literals while preserving commit history structure** — use `git filter-repo --replace-text` (do not run yet until branch/backup plan is ready).
- [ ] **Target literals for replacement** — currently identified examples include:
  - `[REDACTED_SECRET_1]`
  - `[REDACTED_SECRET_2]`
  - `[REDACTED_USER_1]`
- [ ] **Prepare replacements file and perform dry planning review** — confirm exact replacement tokens and scope before execution.
- [ ] **Execute rewrite in one controlled maintenance window** — run once, verify with repo-wide search, then force-push branches/tags.
- [ ] **Coordinate downstream clone reset** — after rewrite, collaborators must re-clone or hard-reset because commit SHAs will change.
- [ ] **Post-rewrite verification** — search entire repo history and working tree to confirm sensitive literals are fully removed.
- [ ] **Open-source readiness gate** — do not make repo public until rewrite + rotation + verification are complete.

---

## Known external issues

- [ ] **Wikidata item deletions** — a batch of Wikidata items created by an earlier script (for interlanguage link targets) were deleted by another editor on Wikidata. The deletions happened without opportunity to contest or add supplementary content that might have justified keeping them. Need to assess scope (which items were deleted, whether they can be re-created with stronger sourcing) and develop a strategy for re-creation or working around the missing QIDs.

---

## Longer term (architecture)

These are tracked in detail in [VISION.md](VISION.md). Listed here for completeness.

- [ ] **Namespace restructure** — introduce `Data:`, `Meta:`, `Export:` namespaces per the VISION.md plan. Script `populate_namespace_layers.py` is ready but gated behind `--enable-namespace-layers` flag until namespaces are created on the wiki. Currently creates `Data:` (JSON with QID) and `Export:` (wikitext copy) pages from mainspace.
- [ ] **Move `{{ill}}` export data to `Export:` namespace** — simplify mainspace to plain `[[links]]`; keep the ILL/QID data in `Export:` pages only
- [ ] **Category name standardization** — establish canonical English names for all categories; categories handled via Wikidata rather than translation
- [ ] **Pramana integration** — connect `Data:` pages to pramana.dev as the canonical ID backend
- [ ] **Automated translation pipeline** — take any Japanese Wikipedia page and produce a consistent translated page with proper ILL/Wikidata connections
- [ ] **Change-tracking bot** — monitor wiki changes and propagate them across namespace layers
