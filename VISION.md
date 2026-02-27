# Vision — wikibot pipeline architecture

This document distills the architectural vision for this project. It is a living document.

---

## Goal

Build a maintainable, multi-layer content pipeline for [shinto.miraheze.org](https://shinto.miraheze.org) that:

- Keeps human-readable content clean and editable
- Maintains machine-readable canonical data (QIDs, Pramana IDs) separately
- Exports content in formats suitable for deployment to Wikipedia-ecosystem wikis
- Syncs changes across all layers automatically
- Integrates with [pramana.dev](https://pramana.dev) as the canonical ID backend

---

## Phase 0: Complete legacy operations (in progress / mostly done)

- [x] Add `{{wikidata link|Q...}}` to all category pages via interwiki resolution
- [x] Create `Q{QID}` mainspace redirects for all wikidata-linked categories
- [x] Remove `{{DEFAULTSORT:...}}` from Wikidata-generated shikinaisha pages
- [x] Add `{{moved to}}` / `{{moved from}}` for recent page moves
- [x] Fix `[[:Category:X]]` colon prefix in dup-disambiguation pages
- [ ] Audit category pages for remaining race-condition artifacts (see postmortem below)
- [ ] Remove all hardcoded passwords → environment variables

---

## Phase 1: Namespace restructure

The wiki currently uses a flat mainspace + standard Talk:. The vision is a multi-layer namespace system:

```
Cat                  ← human-readable (editors touch this)
Talk:Cat             ← centralized, template-managed discussion
Data:Cat             ← machine-readable, Pramana IDs, canonical graph
Meta:Cat             ← per-page metadata, categories, auxiliary info
Export:Cat           ← QID-preserving, {{ill|X|WD=Q...}} format for Wikipedia export
```

### Layer responsibilities

| Layer | Who edits | Format | Purpose |
|-------|-----------|--------|---------|
| `Cat` | Humans | `[[like this]]` | Clean reading/editing surface |
| `Talk:Cat` | Humans + bot | Wikitext | Discussion, auto-archives, header template |
| `Data:Cat` | Bot only | Structured XML-ish + Pramana refs | Canonical ID graph, sync engine |
| `Meta:Cat` | Bot only | Wikitext | Category assignments, page-specific properties |
| `Export:Cat` | Bot only | `{{ill\|X\|WD=Q...}}` | Ready for import to other wikis |

### Move behavior

When `Cat` is moved to `NewName`, a bot should also move:
- `Talk:Cat` → `Talk:NewName`
- `Data:Cat` → `Data:NewName`
- `Meta:Cat` → `Meta:NewName`
- `Export:Cat` → `Export:NewName`

Standard MediaWiki cannot do this automatically for cross-namespace pages. A `PageMoveComplete` hook or a move-tracking bot is required.

### Talk page policy

- All layer-specific talk pages redirect to `Talk:Cat` (the single canonical discussion page)
- `Talk:Cat` has a header template explaining all layers and their purposes
- `Talk:Cat` has auto-archiving enabled
- Content from Japanese Wikipedia and English Wikipedia talk pages may be imported as a starting point
- Legacy random/junk talk page content is overwritten

---

## Phase 2: Category page cleanup

Category pages currently have messy spaghetti code from many automated passes. The plan:

- Strip everything from category pages except:
  - Categorization (`[[Category:Parent]]`)
  - A clean human-readable description
  - The `{{wikidata link|Q...}}` template
- Move all metadata into `Meta:Category:X` pages (or the `Meta:` layer equivalent)
- Category pages should be navigable and human-readable, not cluttered with automation artifacts

---

## Phase 3: Sentence-level tracking

To enable cross-language sync at fine granularity:

- Each sentence in `Data:` pages gets a stable ID (footnote-style marker in the `Cat` layer)
- Humans don't see IDs directly — they see familiar footnote markers (`[1]`, `[2]`) that map to stable IDs internally
- A bot converts footnote changes back into ID graph updates
- Deleting a sentence is a flagged event requiring confirmation

---

## Phase 4: Pramana integration

- `pramana.dev` serves as the canonical ID backend
- `Data:` pages reference Pramana IDs: `pra:123456789`
- QIDs (Wikidata) are one facet of the Pramana graph, not the primary key
- Redirect resolution: when a link targets a redirect, the bot resolves it to the canonical QID at ingestion time rather than storing the redirect as a node

---

## Phase 5: Cross-language sync engine

- Changes in any language layer propagate to all others via the canonical `Data:` graph
- Link corrections (e.g., fixing a disambiguation link) propagate to all language versions automatically
- Image translations handled for horizontal-text images only (vertical text excluded)

---

## Secrets

Move all credentials out of source code. Proposed approach:

```python
import os
USERNAME = os.environ["WIKI_USERNAME"]
PASSWORD = os.environ["WIKI_PASSWORD"]
```

Or use a `.env` file with `python-dotenv`:
```
WIKI_USERNAME=EmmaBot
WIKI_PASSWORD=...
```

Add `.env` to `.gitignore`. Provide `.env.example` with placeholder values.

---

## Known issues / postmortem

### Category run race condition

During the category Wikidata-link-adding runs, the `create_category_qid_redirects.py` script caught up with the `resolve_category_wikidata_from_interwiki.py` script. This may have resulted in some `Q{QID}` redirect pages being created before the target category had its Wikidata link added, or vice versa. The exact scope of this issue is unknown but believed to be minor. A future audit script should verify consistency.

### Category:Q* pages in category namespace

An early version of `create_category_qid_redirects.py` incorrectly created redirect pages as `Category:Q{QID}` instead of `Q{QID}` in mainspace. ~77 such pages were created and left in place (not deleted). These may need cleanup.

### Duplicate QID disambiguation pages

621 categories share a QID with another category. These have disambiguation pages at `Q{QID}` in mainspace with format:
```
# [[:Category:Foo]]
# [[:Category:Bar]]
[[Category:duplicated qid category redirects]]
```
These need human review to determine which category correctly holds the QID.

---

## Repository cleanup plan

The repo root and `shinto_miraheze/` contain ~300+ scripts, many of which are:
- One-off fixes that ran once and are no longer needed
- Superseded by newer versions (e.g., `generate_shikinaisha_pages_v3.py` through `v25`)
- Log files that should not be committed
- Data CSVs that may contain sensitive or large data

Proposed structure after cleanup:
```
wikibot/
  shinto_miraheze/        ← active scripts for shinto.miraheze.org
  archive/                ← preserved but inactive legacy scripts
  data/                   ← CSVs and data files (gitignored if large)
  docs/                   ← VISION.md, SCRIPTS.md, etc.
  .env.example
  README.md
```
