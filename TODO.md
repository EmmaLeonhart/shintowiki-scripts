# TODO

Consolidated list of open tasks. Historical/completed work is tracked in [DEVLOG.md](DEVLOG.md). See [VISION.md](VISION.md) for the broader architecture plan.

---

## Automation boundary

The GitHub Actions cleanup loop (`shinto_miraheze/cleanup_loop.sh`, runs daily) handles everything that can be scripted safely and repeatably. State files are committed incrementally after each chunk (Import & Categorization, Structural Fixes, Wikidata, Final Core, Cleanup Loop, Deprecated) so progress is not lost if a later chunk fails. **Everything outside the loop requires manual intervention.** The remaining open tasks all require human judgment, prereq work, or infrastructure that does not yet exist.

### Currently automated (cleanup loop)

These run automatically every 24 hours via GitHub Actions. No manual action needed unless something breaks.

**Bookkeeping** (start & end of loop):
- **Bot userpage status** — `update_bot_userpage_status.py`: marks workflow active at start, inactive at end, and updates `User:EmmaBot` with run metadata.

**Core Loop** (structural changes that later scripts depend on):
- **Enwiki XML reimport** — `reimport_from_enwiki.py`: downloads XML export from enwiki (with templates, current revision) and reimports into shintowiki with mangled timestamps to force overwrite. Fixes erroneous transclusions by pulling the full dependency tree. Processes 10 pages per run from `erroneous_transclusion_pages.txt`. Failed imports are logged to `reimport_from_enwiki.errors`. **Known issue (2026-03-20):** This step hangs indefinitely on large Module doc page exports, blocking the entire workflow for hours. All 17 current pages were manually downloaded and imported locally. The automated import needs to either be fixed (add timeout to the Miraheze import call) or run locally instead of in CI.
- **Wanted category creation** — `create_wanted_categories.py`: fetches Special:WantedCategories via API and creates stub pages tagged `[[Category:Categories autocreated by EmmaBot]]`.
- **Uncategorized category fix** — `categorize_uncategorized_categories.py`: adds `[[Category:Categories autocreated by EmmaBot]]` to category pages from Special:UncategorizedCategories that were created in earlier bulk workflows without proper categorization.
- **EmmaBot category triage (enwiki)** — `triage_emmabot_categories.py`: checks autocreated categories against enwiki; moves to `[[Category:Emmabot categories with enwiki]]` or `[[Category:Emmabot categories without enwiki]]` (100 per run).
- **EmmaBot category triage (jawiki)** — `triage_emmabot_categories_jawiki.py`: second pass on without-enwiki categories; checks jawiki; moves to `[[Category:Emmabot categories with jawiki]]` or `[[Category:Emmabot categories without enwiki or jawiki]]` (100 per run).
- **EmmaBot category triage (secondary)** — `triage_emmabot_categories_secondary.py`: third pass on remaining categories using additional heuristics.
- **Unused template deletion** — `delete_unused_templates.py`: deletes template pages from Special:UnusedTemplates.
- **Double redirect fixes** — `fix_double_redirects.py`: fixes pages listed on Special:DoubleRedirects.
- **Resolve double category QIDs** — `resolve_double_category_qids.py`: walks `[[Category:Double category qids]]` disambiguation pages; when all listed categories resolve to the same final target (one is a redirect to the other), replaces the disambiguation page with a simple redirect. Part of a multi-step cleanup of duplicate QID disambiguation pages. 100 per run.
- **P11250 QuickStatements** — `generate_p11250_quickstatements.py`: walks direct members of `[[Category:Pages linked to Wikidata]]`, checks Wikidata P11250, and adds QuickStatements lines to `[[QuickStatements/P11250]]` for items missing the property. Stateful, 100 per run. Has retry logic with automatic 429 termination and error logging to `error.log`.
- **Tag pages without wikidata** — `tag_pages_without_wikidata.py`: walks all pages in mainspace, category space, and template space; tags pages lacking `{{wikidata link}}` with `[[Category:Pages without wikidata]]`. Stateful, 100 pages *checked* per run (not 100 edited — bounds runtime regardless of hit rate).
- **Clean P11250 QuickStatements** — `clean_p11250_quickstatements.py`: reads `[[QuickStatements/P11250]]`, checks each line against Wikidata, and removes lines where the item now has the correct P11250 value. 100 checks per run.
- **Clean wikidata category redirects** — `clean_wikidata_cat_redirects.py`: cleans up wikidata-related category redirects.
- **Fix noinclude on templates** — `fix_template_noinclude.py`: finds templates with `[[Category:` or `{{wikidata link` outside `<noinclude>` blocks and wraps them properly. Tags fixed templates with `[[Category:Templates fixed with noinclude]]`. 100 per run.
- **Categorize uncategorized pages** — `categorize_uncategorized_pages.py`: fetches `Special:UncategorizedPages` and tags them with `[[Category:Uncategorized pages]]`. 100 per run.
- **Tag untranslated Japanese content** — `tag_untranslated_japanese.py`: walks all mainspace pages and detects significant Japanese text (hiragana, katakana, CJK ideographs) outside of templates, interwiki links, refs, and other expected contexts. Tags pages with `[[Category:Pages with untranslated japanese content]]`. 100 pages checked per run. Prerequisite for the namespace layer work.

**Cleanup Loop** (category cleanup + talk pages):
- **Unused category deletion** — `delete_unused_categories.py`: deletes Special:UnusedCategories pages, skipping any with `{{Possibly empty category}}`.
- **Orphaned talk page deletion** — `delete_orphaned_talk_pages.py`: deletes talk pages from Special:OrphanedTalkPages whose subject page does not exist.
- **Talk page migration** — `migrate_talk_pages.py`: rebuilds talk pages and seeds them with discussion content from ja/en/simple Wikipedia. State file: `shinto_miraheze/migrate_talk_pages.state`.
- **Broken redirect deletion** — `delete_broken_redirects.py`: deletes redirects from Special:BrokenRedirects whose target page does not exist.
- **Crud category cleanup** — `remove_crud_categories.py`: strips `[[Category:X]]` tags from member pages across all subcategories of Category:Crud_categories.

### Temporary / one-off re-bucketing tasks

- [ ] **Re-bucket 300+ untranslated pages with extended thresholds** — The original thresholds capped at 300, so all pages with 300+ untranslated Japanese characters were lumped together. Thresholds now extend to 5000 (50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000). Run `tag_untranslated_japanese.py --category "Pages with 300+ untranslated japanese characters" --apply --run-tag "..."` to re-bucket existing 300+ pages into finer-grained categories. This is a smaller targeted run since it only hits category members, not all mainspace. Can be re-run as needed to introduce more granular tiers later.
- [ ] **AI translation pipeline on high-bucket pages** — Once re-bucketing is done, use the highest buckets (1000+, 2000+, etc.) to identify pages that are essentially untranslated. Run an AI translation agent against these. Also cross-reference with [[Category:Secondary category triage]] for prioritization. Blocked on re-bucketing completing first.

### Requires manual intervention

- [ ] **Template:Talk page header** — Edit this template so that it fits all requirements for migrated/transformed talk pages.
- [ ] **Figure out what to do with `[[Category:Need translation]]`** — assess scope, decide whether to automate or manually review members.
- [ ] **Enrich autocreated categories** — Write a script to add meaningful content (interwikis, wikidata links, parent categories) to pages in `Category:Categories autocreated by EmmaBot` that were created as stubs.
- [ ] **Special:WantedPages and Special:WantedTemplates** — Planning to do something with these eventually, but not sure what yet. Waiting until the category pipeline is solid before tackling.

---

## Wiki content tasks (on shintowiki)

All items below require manual editing or human review. None have a safe automated path right now.

### High priority

- [x] **Fix template categories outside `<noinclude>`** — now automated via `fix_template_noinclude.py` in the cleanup loop.
- [ ] **ILLs without `WD=`** â€” ILL templates missing a `WD=` parameter are broken by design. Run `fix_ill_destinations.py` or a new script to identify and fill in missing `WD=` values. Do not blindly overwrite â€” check the local context of each.
- [ ] **Duplicate QID disambiguation pages** â€” 621 `Q{QID}` mainspace pages point to 2+ categories. Multi-step cleanup in progress: (1) `resolve_double_category_qids.py` now automates the easy cases where all listed categories resolve to the same target (now in cleanup loop). (2) Remaining pages where categories point to genuinely different targets still need human review. Also applies to `[[Category:duplicated qid category redirects]]`.
- [ ] **Translate all category names in [Category:Japanese language category names](https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names)** â€” ensure every category in this tracking set is migrated to a canonical English category title.
- [ ] **Resolve migration issues in [Category:Erroneous qid category links](https://shinto.miraheze.org/wiki/Category:Erroneous_qid_category_links)** â€” fix category/QID mismatches and complete any blocked merges or redirect corrections.
- [ ] **[Category:Pages with duplicated content](https://shinto.miraheze.org/wiki/Category:Pages_with_duplicated_content)** â€” pages where the same content exists under multiple titles. Needs human review per page: which title is canonical, whether a history merge is appropriate.
- [ ] **Audit category pages for race-condition artifacts** â€” some categories may have inconsistent state from the `resolve_category_wikidata` and `create_category_qid_redirects` scripts running concurrently. Scope unknown; needs an audit script.
- [ ] **Review post-audit leftovers** - many entries in https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names appear to be downstream artifacts; verify whether any automated cleanup is still needed.

### Lower priority

- [ ] **Categories missing Wikidata** â€” categories with interwikis but no `{{wikidata link}}`. Many are Japan-only or internal maintenance categories with no real Wikidata item; assess per-category.
- [ ] **Split `Category:Categories_missing_wikidata` into two typed subcategories** â€” create and maintain two `|*`-sorted subcategories under `Category:Categories_missing_wikidata`: (1) categories missing interwikis entirely, and (2) categories with valid interwikis but no Wikidata link yet. Keep this as a later structural cleanup task (not immediate implementation). -- update: We need to recreate that category because it was not accurately applied and thus was cleaned out as a crud category
- [ ] **Categories with interwikis but no Wikidata link added** â€” older script passes added interwiki links without adding the `{{wikidata link}}` template. Re-run the wikidata link script on these.
- [ ] **Multiple `{{wikidata link}}` on one page** â€” usually indicates a Wikidata disambiguation issue. Needs per-case review.
- [ ] **Shikinaisha pages with broken ILL destinations** â€” ILLs pointing to "Unknown" as target from early workflow. Most are identifiable from context; fix with `fix_ill_destinations.py` pass.
- [ ] **Remove legacy category-page fix templates** â€” remove remnants such as `{{デフォルトソート:...}}` and `{{citation needed|...}}` from category pages where they were introduced by old workaround passes.

---

## Repository / script tasks

### Secret removal (run soon, before open-source release)

- [ ] **Rotate exposed credentials first** â€” treat any historical plaintext credentials as compromised and rotate them before/alongside history rewrite.
- [ ] **Rewrite git history to remove sensitive literals while preserving commit history structure** â€” use `git filter-repo --replace-text` (do not run yet until branch/backup plan is ready).
- [ ] **Target literals for replacement** â€” currently identified examples include:
  - `[REDACTED_SECRET_1]`
  - `[REDACTED_SECRET_2]`
  - `[REDACTED_USER_1]`
- [ ] **Prepare replacements file and perform dry planning review** â€” confirm exact replacement tokens and scope before execution.
- [ ] **Execute rewrite in one controlled maintenance window** â€” run once, verify with repo-wide search, then force-push branches/tags.
- [ ] **Coordinate downstream clone reset** â€” after rewrite, collaborators must re-clone or hard-reset because commit SHAs will change.
- [ ] **Post-rewrite verification** â€” search entire repo history and working tree to confirm sensitive literals are fully removed.
- [ ] **Open-source readiness gate** â€” do not make repo public until rewrite + rotation + verification are complete.

---

## Known external issues

- [ ] **Wikidata item deletions** â€” a batch of Wikidata items created by an earlier script (for interlanguage link targets) were deleted by another editor on Wikidata. The deletions happened without opportunity to contest or add supplementary content that might have justified keeping them. Need to assess scope (which items were deleted, whether they can be re-created with stronger sourcing) and develop a strategy for re-creation or working around the missing QIDs.

---

## Longer term (architecture)

These are tracked in detail in [VISION.md](VISION.md). Listed here for completeness.

- [ ] **Namespace restructure** â€” introduce `Data:`, `Meta:`, `Export:` namespaces per the VISION.md plan. Script `populate_namespace_layers.py` is ready but gated behind `--enable-namespace-layers` flag until namespaces are created on the wiki. Currently creates `Data:` (JSON with QID) and `Export:` (wikitext copy) pages from mainspace.
- [ ] **Move `{{ill}}` export data to `Export:` namespace** â€” simplify mainspace to plain `[[links]]`; keep the ILL/QID data in `Export:` pages only
- [ ] **Category name standardization** â€” establish canonical English names for all categories; categories handled via Wikidata rather than translation
- [ ] **Pramana integration** â€” connect `Data:` pages to pramana.dev as the canonical ID backend
- [ ] **Automated translation pipeline** â€” take any Japanese Wikipedia page and produce a consistent translated page with proper ILL/Wikidata connections
- [ ] **Change-tracking bot** â€” monitor wiki changes and propagate them across namespace layers





