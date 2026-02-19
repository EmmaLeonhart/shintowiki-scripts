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

## shinto_miraheze/ — active scripts

| Script | Status | Description |
|--------|--------|-------------|
| `resolve_category_wikidata_from_interwiki.py` | ACTIVE | Resolves Wikidata QIDs for category pages via interwiki links. Accepts optional start-title CLI arg. Ran full pass Feb 2026. |
| `resolve_wikidata_from_interwiki.py` | ACTIVE | Same as above but for main-namespace pages. |
| `resolve_template_wikidata_from_interwiki_v2.py` | ACTIVE | Resolves Wikidata for template pages. |
| `generate_shikinaisha_pages_v24_from_t.py` | ACTIVE | Latest version of the shikinaisha page generator. |

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

## Planned cleanup

1. Move all legacy/completed scripts to `archive/`
2. Move log files out of git tracking
3. Create `shinto_miraheze/` as the canonical home for all shintowiki scripts
4. Consolidate root-level active scripts into `shinto_miraheze/` or a `common/` module
5. Replace hardcoded credentials with `.env` / environment variables
