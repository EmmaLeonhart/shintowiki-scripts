# Scripts catalog

Status codes:
- **ACTIVE** — currently maintained and used
- **COMPLETE** — ran to completion, no longer needed
- **LEGACY** — old/superseded, kept for reference
- **ARCHIVE** — should be moved to `archive/`

---

## Root directory — active / recent scripts

| Script | Status | Description |
|--------|--------|-------------|
| `create_category_qid_redirects.py` | ACTIVE | Creates `Q{QID}` mainspace redirects for all categories with `{{wikidata link}}`. Handles duplicates with disambiguation pages. |
| `fix_dup_cat_links.py` | COMPLETE | Fixed `[[Category:X]]` → `[[:Category:X]]` in dup-disambiguation pages after bad initial run. One-off. |
| `add_moved_templates.py` | ACTIVE | Adds `{{moved to}}` / `{{moved from}}` to pages after page moves. MOVES list is maintained here. |
| `remove_defaultsort_digits.py` | COMPLETE | Removed `{{DEFAULTSORT:...}}` from `Category:Wikidata generated shikinaisha pages`. Ran Feb 2026. |
| `fix_ill_destinations.py` | ACTIVE | Fixes broken ILL template link targets. |
| `run_claude.bat` | ACTIVE | Opens Windows Terminal in this directory and launches Claude Code. |

---

## shinto_miraheze/ — cleanup loop (runs automatically via GitHub Actions)

### Bookkeeping

| Script | Status | Description |
|--------|--------|-------------|
| `update_bot_userpage_status.py` | ACTIVE | Updates `User:EmmaBot` with current pipeline run metadata and workflow active/inactive status. |

### Core Loop — structural changes that later scripts depend on

| Script | Status | Description |
|--------|--------|-------------|
| `reimport_from_enwiki.py` | ACTIVE | Downloads XML export from enwiki (with templates, current revision) and reimports into shintowiki with mangled timestamps to force overwrite. Fixes erroneous transclusions by pulling the full dependency tree. Processes 1 page per run. Reads from `erroneous_transclusion_pages.txt`. See "Enwiki XML reimport workflow" below. |
| `create_wanted_categories.py` | ACTIVE | Fetches Special:WantedCategories via API and creates stub pages for each. |
| `categorize_uncategorized_categories.py` | ACTIVE | Adds `[[Category:Categories autocreated by EmmaBot]]` to uncategorized category pages. |
| `triage_emmabot_categories.py` | ACTIVE | Checks EmmaBot-autocreated categories against enwiki; sorts into with-enwiki / without-enwiki subcategories. |
| `triage_emmabot_categories_jawiki.py` | ACTIVE | Second pass: checks without-enwiki categories against jawiki; sorts into with-jawiki / without-either subcategories. |
| `triage_emmabot_categories_secondary.py` | ACTIVE | Third pass: secondary triage for remaining uncategorized EmmaBot categories using additional heuristics. |
| `delete_unused_templates.py` | ACTIVE | Deletes template pages from Special:UnusedTemplates. |
| `fix_double_redirects.py` | ACTIVE | Fixes pages listed on Special:DoubleRedirects. |

### Cleanup Loop — category cleanup + talk pages

| Script | Status | Description |
|--------|--------|-------------|
| `delete_unused_categories.py` | ACTIVE | Deletes Special:UnusedCategories pages; skips those with `{{Possibly empty category}}`. |
| `delete_orphaned_talk_pages.py` | ACTIVE | Deletes talk pages from Special:OrphanedTalkPages whose subject page does not exist. |
| `migrate_talk_pages.py` | ACTIVE | Rebuilds talk pages and seeds discussion content from ja/en/simple Wikipedia. |
| `remove_crud_categories.py` | ACTIVE | Strips `[[Category:X]]` tags from members of all Crud_categories subcategories. |

### Deprecated — likely complete, kept as safety net

| Script | Status | Description |
|--------|--------|-------------|
| `normalize_category_pages.py` | DEPRECATED | Enforces canonical category page layout. State file unchanged since Mar 1. |
| `tag_shikinaisha_talk_pages.py` | DEPRECATED | Adds "generated from Wikidata" notice to shikinaisha talk pages. State file unchanged since Feb 26. |
| `fix_erroneous_qid_category_links.py` | DEPRECATED | Fixes category/QID mismatches. Category fully cleared as of Mar 12. |
| `remove_legacy_cat_templates.py` | DEPRECATED | Removes legacy template artifacts from category pages. State file unchanged since Mar 1. |
| `move_categories.py` | DEPRECATED | Moves/renames categories per configured move list. Likely all moves complete. |
| `create_japanese_category_qid_redirects.py` | DEPRECATED | Creates QID redirects for Japanese-named categories. Likely all redirects created. |

## shinto_miraheze/ — manual-use / not in loop

These exist but require human review or have been superseded. They are not run automatically.

| Script | Status | Description |
|--------|--------|-------------|
| `resolve_category_wikidata_from_interwiki.py` | LEGACY | Ran a full pass Feb 2026. Remaining gaps require human judgment; not safe to re-run automatically. |
| `resolve_wikidata_from_interwiki.py` | LEGACY | Main-namespace equivalent of the above. Full pass complete. |
| `resolve_duplicated_qid_categories.py` | MANUAL | Merges CJK/Latin duplicate QID pairs. Needs human review per case. |
| `merge_japanese_named_categories.py` | MANUAL | Merges Japanese-named categories into English equivalents. Remaining entries are ambiguous. |
| `fix_ill_destinations.py` | MANUAL | Fixes broken ILL destinations. Must not be run blindly — check local context per page. |
| `resolve_missing_wikidata_categories.py` | MANUAL | Resolves Wikidata for categories missing it. Source category was cleaned out; prereq work needed. |
| `tag_missing_wikidata_with_ja_interwiki.py` | MANUAL | Tags categories missing Wikidata that have a ja: interwiki. Source category needs recreation. |
| `create_category_qid_redirects.py` | MANUAL | Creates `Q{QID}` mainspace redirects. Full pass complete; run only when new categories are added. |
| `generate_shikinaisha_pages_v25_with_redirects.py` | MANUAL | Latest shikinaisha page generator. Run only when new shikinaisha data is available. |

---

## Root directory — legacy / archive candidates

These were generated iteratively with ChatGPT and have been superseded or are one-off runs that completed.

| Script / File | Notes |
|---------------|-------|
| `add_all_p31_categories*.py` | Category P31 adding — completed runs |
| `add_dummy_category*.py` | Various dummy category additions — completed |
| `add_*_labels.py` (dutch, french, german, etc.) | Wikidata label additions — completed |
| `add_interwikis_from_wikidata_fresh.py` | Interwiki addition — superseded |
| `add_p31_categories_*.py` (multiple versions) | Superseded by later versions |
| `bot.py`, `bot (1).py`, `auto.py`, `attempt.py` | Generic scratch/test scripts |
| `create_qid_redirects.py`, `create_qid_redirects_to_pages.py` | Superseded by `create_category_qid_redirects.py` |
| `generate_shikinaisha_pages_v3.py` through `v23` | Superseded by v24 |
| `patch_ill_english_labels_v2.py` through `v9.py` | All superseded by latest version |
| `tier0_enwiki_fix_bot.py` through `tier5_*.py` | Enwiki tier fix series — completed |
| `undo_wikidata_edits_v2.py` through `v5.py` | Undo scripts — completed |
| `*.log` files (all) | Log files, should be gitignored |
| `*.txt` files (most) | One-off data dumps |

---

## Files to gitignore going forward

```
*.log
__pycache__/
*.pyc
.env
tmpclaude-*/
desktop.ini
```

---

## Enwiki XML reimport workflow

A long-standing workflow for fixing broken templates, modules, and pages on shintowiki by reimporting them from enwiki. This was historically one of the most important maintenance operations.

**How it works:**
1. Download the XML export of a page from enwiki via `Special:Export` with "include templates" enabled and "current revision only".
2. Replace `timestamp` with `timestam` in the XML — this breaks the timestamp field so MediaWiki treats the import as having no timestamp. The import time becomes the revision timestamp, which forces an overwrite of the local revision even if it is newer than enwiki's.
3. Import the modified XML into shintowiki via `action=import`.

**Why this exists:**
Shintowiki was originally built by mass-importing templates and modules from enwiki. During those imports, categories were manually added to imported pages because imported pages used to not have functioning categories until at least one category was added (due to a Miraheze indexing quirk that has since been fixed). This category-adding had unforeseen consequences: crud categories ended up on templates, modules, and other structural pages, and some template dependency chains broke in ways that were hard to diagnose. The reimport workflow fixes this by pulling the entire dependency tree of a page (the page itself plus all transcluded templates) fresh from enwiki and overwriting the local copies.

**Why mangle timestamps:**
Often the local shintowiki revision is technically "newer" than enwiki's (because of the manual category edits made after import). Without timestamp mangling, MediaWiki would refuse to overwrite the local revision. By breaking the timestamp field, the import always overwrites.

**Current implementation:** `reimport_from_enwiki.py` reads from `erroneous_transclusion_pages.txt`, processes 1 page per pipeline run (low priority, high cost), and tracks completed pages in `reimport_from_enwiki.state`. It runs as the first step of the Core Loop.

---

## Category triage workflow

EmmaBot-autocreated categories go through a multi-pass triage to determine their origin and relevance:

1. **`triage_emmabot_categories.py`** — First pass: checks each category against enwiki. Categories that exist on enwiki are sorted into `[[Category:EmmaBot categories with enwiki match]]`; those without are sorted into `[[Category:EmmaBot categories without enwiki match]]`.
2. **`triage_emmabot_categories_jawiki.py`** — Second pass: checks the "without enwiki match" categories against jawiki. Matches go to `[[Category:EmmaBot categories with jawiki match]]`; remaining go to `[[Category:EmmaBot categories without enwiki or jawiki match]]`.
3. **`triage_emmabot_categories_secondary.py`** — Third pass: secondary triage for remaining categories using additional heuristics.

This triage feeds into downstream cleanup decisions (e.g., whether to keep, merge, or delete a category).

---

## Planned cleanup

1. Move all legacy/completed scripts to `archive/`
2. Move log files out of git tracking
3. Create `shinto_miraheze/` as the canonical home for all shintowiki scripts
4. Consolidate root-level active scripts into `shinto_miraheze/` or a `common/` module
5. Replace hardcoded credentials with `.env` / environment variables
