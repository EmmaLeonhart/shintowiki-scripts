# Wikibot Repository Structure

## Overview

**Purpose:** Comprehensive collection of MediaWiki automation scripts for maintaining Shinto Wiki (shinto.miraheze.org)

**Primary Functions:**
- Synchronization with Wikidata and other Wikipedia editions
- Category management and validation
- Interwiki link creation and maintenance
- Template/infobox synchronization
- Content import and migration

---

## Quick Reference: Script Categories

### 1. **Wikidata Integration & Linking** (12 scripts)
Scripts that synchronize content with Wikidata and extract/add wikidata identifiers.

| Script | Purpose |
|--------|---------|
| `resolve_wikidata_from_interwiki.py` | **[PRIORITY]** Finds wikidata for pages with interwiki links; tags orphaned references with "Foreign language page not connected to wikidata" |
| `resolve_wikidata_from_translated_page.py` | Extracts wikidata from translated pages |
| `add_wikidata_links.py` | Adds Wikidata links to pages |
| `add_wikidata_from_id_interwiki.py` | Adds wikidata links from ID interwikis |
| `add_wikidata_from_id_interwiki_category.py` | Category variant of above |
| `add_wikidata_from_id_interwiki_category_ar.py` | Arabic language variant |
| `add_wikidata_from_id_interwiki_category_ms.py` | Malay language variant |
| `ill_wikidata_fix_bot.py` | Fixes ILL (interlanguage link) templates to point to wikidata |
| `tag_missing_wikidata_all_pages.py` | Tags pages without wikidata |
| `tag_missing_wikidata_category.py` | Category-specific wikidata tagging |
| `interwiki_wikidata_sync_bot.py` | Syncs interwiki links with wikidata |
| `de_interwiki_wikidata_sync_bot.py` | German language variant |
| `fa_interwiki_wikidata_sync_bot.py` | Persian language variant |

---

### 2. **Interwiki Link Management** (16 scripts)
Creates and maintains interlanguage links between wiki pages.

**Basic Adding:**
- `add_en_interwiki.py` - Adds English interwiki links
- `add_enwiki_interwiki.py` - Advanced English Wikipedia interwiki from Wikidata
- `add_enwiki_link_to_category.py` - Adds English category interwiki links (NEW)
- `add_month_template_interwikis.py` - Adds interwikis for month templates
- `add_persian_month_interwikis.py` - Persian month template interwikis

**Language-Specific Labels:**
- `add_dutch_labels.py` - Adds Dutch labels to Wikidata
- `add_french_labels.py` - Adds French labels to Wikidata
- `add_german_labels.py` - Adds German labels to Wikidata
- `add_indonesian_labels.py` - Adds Indonesian labels to Wikidata
- `add_turkish_labels.py` - Adds Turkish labels to Wikidata

**Cleanup & Validation:**
- `clean_enwiki_interwiki.py` - Cleans up and validates English Wikipedia interwiki links
- `ill_backlink_ja_adder.py` - Adds Japanese interwiki backlinks
- `ill_to_enwiki_cleanup.py` - Converts interlanguage links to English Wikipedia links
- `interwiki_redirect_bot.py` - Handles interwiki redirects
- `remove_sn_interwiki.py` - Removes specific interwiki references

---

### 3. **Category Management & Restoration** (15 scripts)
Manages MediaWiki category hierarchies and syncs with external sources.

**Restoration (from other wiki editions):**
- `jawiki_cat_restore_bot.py` - Syncs categories from Japanese Wikipedia
- `jawiki_cat_restore_bot_tier_4.py` - Tier 4 variant
- `dewiki_cat_restore_bot.py` - Syncs categories from German Wikipedia
- `dewiki_cat_restore_bot_tier_4.py` - Tier 4 variant
- `zhwiki_cat_restore_bot.py` - Syncs categories from Chinese Wikipedia
- `category_interwiki_restore_bot.py` - Restores interwiki category links

**Category Operations:**
- `create_wanted_categories.py` - Creates all wanted (red-link) categories from Special:WantedCategories
- `create_log_categories.py` - Creates log-related categories
- `create_categories_from_list.py` - Creates categories from a text list

**Cleanup & Organization:**
- `category_cleanup_bot.py` - General category cleanup
- `category_sweep_single_bot.py` - Removes categories with only 1 member
- `category_enwiki_sync_bot.py` - Syncs with English Wikipedia categories
- `cat_jawiki_cleanup.py` - Japanese category cleanup
- `cat_clean_float_z.py` - Cleans up floating 'z' characters in categories
- `cat_relocate_bottom.py` - Moves categories to bottom of pages
- `cat_wikidata_prepender.py` - Adds wikidata to category content
- `cat_move_scanner.py` - Tracks category moves/renames
- `cat_enwiki_overwrite.py` - Overwrites categories from English Wikipedia

---

### 4. **Infobox & Template Synchronization** (9 scripts)
Synchronizes infobox parameters with Wikidata properties.

| Script | Template Type |
|--------|---------------|
| `sync_person_infobox.py` | Person (P18, P569, P570, P19-20, P21, P27, P106, P39, P26, P40, P22-25, P3373, P53, P166, P800, P140, P149, P361, P1559, P735, P119) |
| `sync_deity_infobox.py` | Deity |
| `sync_buddhist_temple_infobox.py` | Buddhist temple |
| `sync_kofun_infobox.py` | Kofun (ancient burial mound) |
| `add_hokora_descriptions.py` | Hokora (small shrine) descriptions |
| `add_shrine_descriptions.py` | Shrine descriptions |
| `update_hokora_descriptions_v5.py` | V5 hokora description update |
| `update_shrine_descriptions_v5.py` | V5 shrine description update |
| `template_sync_or_cleanup.py` | Generic template sync/cleanup |

---

### 5. **Tier-Based Category Validation** (7 scripts)
Implements a tiered system for validating category quality across Wikipedia editions.

- `tier0_enwiki_fix_bot.py` - Verifies Tier 0 categories on English Wikipedia with resume capability
- `tier1_enwiki_check_bot.py` - Checks Tier 1 categories
- `tier2_enwiki_adder.py` - Adds English Wikipedia links to Tier 2
- `tier2_enwiki_check_bot.py` - Validates Tier 2 categories
- `tier3_ja_to_enwiki_updater.py` - Updates Tier 3 from Japanese to English
- `tier3_redirect_and_enwiki_check.py` - Checks Tier 3 redirects
- `tier4_redirect_fix_bot.py` - Fixes Tier 4 redirects
- `tier5_redirect_fix_bot.py` - Fixes Tier 5 redirects

---

### 6. **Redirect Management** (6 scripts)
Creates, fixes, validates, and cleans up redirects.

- `bulk_redirect_to_enwiki.py` - Creates bulk redirects to English Wikipedia
- `fix_redirect_links_bot.py` - Fixes broken redirect links
- `fix_double_redirects.py` - Resolves double redirects (A→B→C to A→C)
- `make_jalink_redirects.py` - Creates redirects for Japanese links
- `enwiki_redirect_cleanup.py` - Cleans up English Wikipedia redirects
- `redirect_category_fixer.py` - Fixes category redirects
- `redirects.py` - Generic redirect utility

---

### 7. **English Language/Label Patching** (9 scripts)
Iterative versions for patching ILL templates with English labels from Wikidata.

- `patch_ill_english_labels.py` - Base version
- `patch_ill_english_labels_v2.py` through `v9.py` - Incremental improvements
- `german_ill.py` - German ILL-specific patching
- `undo_faulty_ill_fix_bot.py` - Reverts faulty ILL fixes

---

### 8. **Special Property Management** (4 scripts)
Handles specific Wikidata properties.

- `remove_kokugakuin_p1343.py` - Removes P1343 (described at URL) references to Kokugakuin Encyclopedia
- `remove_kokugakuin_p1343_v2.py` and `v3.py` - Improved variants
- `RemoveP1343Kokugakuin.py` - Alternative implementation

---

### 9. **Content Import & Migration** (6 scripts)
Imports and migrates content from external sources.

- `import_japanese_revisions.py` - Imports Japanese Wikipedia revision history
- `import.py`, `import 2.py` - Generic import tools
- `import jawiki pages.py` - Imports pages from Japanese Wikipedia
- `attempted.py`, `de_attempt.py`, `ru_attempt.py`, `zh_attempt.py` - Experimental variants

---

### 10. **Specialized Bots** (8 scripts)
Domain-specific maintenance and date operations.

- `islamic_day_bot.py` - Manages Islamic calendar dates
- `fix_islamic_template_ills.py`, `v4.py` - Fixes Islamic date template interwikis
- `translated_page_check_bot.py` - Validates translated pages
- `jawiki_category_redirects_bot.py` - Handles Japanese category redirects
- `jawiki_resolution_pages_fix.py` - Fixes Japanese resolution/disambiguation pages
- `split_erroneous_history_bot.py` - Splits pages with merged history
- `commons_cat_rename_bot.py` - Renames Wikimedia Commons categories

---

### 11. **General Maintenance & Utilities** (20+ scripts)
Miscellaneous tools for page manipulation, analysis, and cleanup.

**Core Bots:**
- `bot.py`, `bot (1).py` - Main bot implementations
- `auto.py` - Automated operations
- `refresh_bot.py` - Content refresh

**Page Operations:**
- `delete.py`, `delete_pages.py` - Page deletion
- `undelete_or_create.py` - Undeletes or creates pages
- `rename.py` - Renames pages
- `merge.py`, `merge_duplicates.py` - Merges duplicate content

**Analysis & Cleanup:**
- `archive_external_links.py` - Archives external references
- `backlinks.py` - Analyzes backlinks
- `fix_categories.py`, `fix_log_categories.py` - Category fixes
- `purge_tier0_categories.py` - Removes Tier 0 category tags
- `mark_pages.py` - Marks pages with specific tags
- `endo.py`, `undo_pages.txt` - Reverts changes

**Formatting & Conversion:**
- `reformat.py` - Content reformatting
- `trim.py` - Content trimming
- `convert.py` - Format conversion
- `generate.py` - Page generation

**Specialized:**
- `restore_translation_template.py` - Restores translation templates
- `simple_ill.py` - Simple interlanguage link handler
- `translated_page.py` - Handles translated pages
- `enwiki_validation_bot.py` - Validates English Wikipedia pages
- `mad_crowd.py` - Crowd-sourced operations
- `proposed_entries_streamlit.py` - Streamlit web interface for proposals

---

## Data Files

| File | Purpose | Size |
|------|---------|------|
| `pages.txt` | List of pages to process (one per line) | 139 KB |
| `categories.txt` | List of categories to manage | 167 KB |
| `commands.txt`, `commands_2.txt` | Command histories | Variable |
| `redirect_categories.txt` | Category redirects mapping | Variable |
| `undo_pages.txt` | Pages to revert on next run | Variable |
| `sexagenary.txt` | 60-year Chinese calendar cycle | Variable |

---

## Common Code Patterns & Conventions

### Authentication & Configuration
All scripts follow a consistent pattern:
```python
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_1]'

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
```

### Key Libraries
- **mwclient** - MediaWiki API client (primary)
- **requests** - HTTP requests
- **mwparserfromhell** - WikiText parsing
- **pymongo** - Data persistence
- **regex/re** - Pattern matching
- **streamlit** - Web interface

### Safe Save Pattern
```python
def safe_save(page, text, summary):
    """Attempt save; skip if unchanged or deleted."""
    if not page.exists:
        return False

    old_text = page.text()
    if old_text.rstrip() == text.rstrip():
        return False  # No change

    try:
        page.save(text, summary=summary)
        return True
    except APIError as e:
        print(f"Save failed: {e.code}")
        return False
```

### Rate Limiting
Most bots include delays between edits:
```python
time.sleep(0.1)  # to 0.5 seconds between edits
```

### Regex Patterns (Common)
- Interwiki: `r'\[\[([a-z]{2}):([^\]]+)\]\]'`
- Categories: `r'\[\[Category:([^\]]+)\]\]'`
- Templates: `r'{{(.*?)}}'`
- Wikidata: `r'{{wikidata link\|([Qq](\d+))}}'`
- ILL templates: `r'{{\s*ill\s*\|'`

---

## Recommended Improvements

### Structural Issues
1. **No unified framework** - Each script is standalone, making maintenance difficult
2. **Hardcoded credentials** - Should use environment variables or config files
3. **Flat file structure** - Should organize by function category
4. **Limited documentation** - Most scripts only have brief headers
5. **No version control** - Multiple versions of same script (v2, v3, v4, etc.)

### Suggested Reorganization
```
wikibot/
├── config/
│   ├── credentials.json (gitignored)
│   ├── site_config.json
│   └── logging.json
├── core/
│   ├── __init__.py
│   ├── wiki_client.py (shared mwclient wrapper)
│   ├── helpers.py (safe_save, common patterns)
│   └── patterns.py (regex definitions)
├── bots/
│   ├── wikidata/
│   │   ├── resolve_from_interwiki.py
│   │   ├── sync_wikidata.py
│   │   └── tag_missing_wikidata.py
│   ├── interwiki/
│   │   ├── add_interwiki_links.py
│   │   ├── cleanup_interwiki.py
│   │   └── add_language_labels.py
│   ├── categories/
│   │   ├── restore_from_jawiki.py
│   │   ├── create_wanted_categories.py
│   │   └── validate_tier_categories.py
│   ├── templates/
│   │   ├── sync_infobox_person.py
│   │   ├── sync_infobox_deity.py
│   │   └── sync_infobox_shrine.py
│   └── general/
│       ├── manage_redirects.py
│       ├── import_content.py
│       └── validate_pages.py
├── data/
│   ├── pages.txt
│   ├── categories.txt
│   └── ...
├── logs/
├── tests/
├── scripts/ (entry points with argument parsing)
└── README.md
```

---

## Statistics

- **Total Scripts**: 150+
- **Estimated Lines of Code**: 50,000+
- **Primary Language**: Python 3
- **Last Updated**: November 7, 2025
- **Total Data Files**: 8+ configuration/list files
- **Supported Languages**: Japanese, German, Chinese, Persian, Dutch, French, Indonesian, Turkish, Arabic, Malay

---

## Getting Started

1. Scripts work with `pages.txt` or `categories.txt` as input
2. Run with `python3 script_name.py`
3. Edit credentials in each script header (or migrate to config file)
4. Most scripts include `time.sleep()` for rate limiting - adjust if needed
5. Check wiki edits via edit history (bot username: Immanuelle)

---

## Notes

- Repository shows significant evolution with many versioning attempts (v1-v9)
- Heavy focus on maintaining consistency across multiple Wikipedia editions
- Strong emphasis on Wikidata synchronization
- Category tier system suggests structured approach to taxonomy
- Recent focus (Nov 2025) on wikidata integration and orphaned interwiki detection

