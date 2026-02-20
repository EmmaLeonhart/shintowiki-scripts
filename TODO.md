# TODO

Consolidated list of known tasks. See [VISION.md](VISION.md) for the broader architecture plan.

---

## Immediate / in progress

- [ ] **History merges** — pages that need `{{moved to}}` / `{{moved from}}` templates to preserve attribution after page moves. Two separate waves of moves means some pages need both. (The actual history import is handled by Miraheze, not by us — the templates just ensure the import will be coherent when it happens.)
- [ ] **Re-run `resolve_duplicated_qid_categories.py`** — 146/221 Q pages resolved; crashed at Q8976949 (edit conflict with concurrent crud run). Re-run after crud finishes to resolve remaining ~75 pages.
- [x] **Crud category cleanup** — `remove_crud_categories.py` running in background; stripping all subcategories of Category:Crud_categories from member pages.
- [x] **`[[sn:...]]` interwiki removal** — complete (1 page, 3 links).
- [x] **Wanted categories created** — 153 pages created.
- [x] **`Category:Generated_x-no-miya_lists` deleted** — 67 User namespace pages deleted.

---

## Wiki content tasks (on shintowiki)

### High priority

- [ ] **Fix template categories outside `<noinclude>`** — some templates have `[[Category:…]]` and `{{wikidata link}}` placed outside `<noinclude>`, causing every page that transcludes the template to inherit those categories. Move stray tags into `<noinclude>`.
- [ ] **ILLs without `WD=`** — ILL templates missing a `WD=` parameter are broken by design. Run `fix_ill_destinations.py` or a new script to identify and fill in missing `WD=` values. Do not blindly overwrite — check the local context of each.
- [ ] **Category:Q* pages in category namespace** — ~77 pages exist as `Category:Q{QID}` (wrong namespace). These should either be deleted or moved to mainspace as `Q{QID}` redirects.
- [ ] **Duplicate QID disambiguation pages** — 621 `Q{QID}` mainspace pages point to 2+ categories. Needs human review to decide which category correctly holds the QID.
- [ ] **Category pages with spaghetti wikitext** — category pages have accumulated Japanese text, stray category links, redundant `{{wikidata link}}` placements, and auto-generated junk from old passes. Goal: strip to clean English description + `{{wikidata link}}` + parent category links only.
- [ ] **[Category:Pages with duplicated content](https://shinto.miraheze.org/wiki/Category:Pages_with_duplicated_content)** — pages where the same content exists under multiple titles. Needs human review per page: which title is canonical, whether a history merge is appropriate.
- [ ] **Audit category pages for race-condition artifacts** — some categories may have inconsistent state from the `resolve_category_wikidata` and `create_category_qid_redirects` scripts running concurrently. Scope unknown; needs an audit script.

### Lower priority

- [ ] **Categories missing Wikidata** — categories with interwikis but no `{{wikidata link}}`. Many are Japan-only or internal maintenance categories with no real Wikidata item; assess per-category.
- [ ] **Categories with interwikis but no Wikidata link added** — older script passes added interwiki links without adding the `{{wikidata link}}` template. Re-run the wikidata link script on these.
- [ ] **Multiple `{{wikidata link}}` on one page** — usually indicates a Wikidata disambiguation issue. Needs per-case review.
- [ ] **Talk pages** — currently contain junk (Wikipedia AFC notices, old bot messages). Plan: overwrite with imported talk page content from Japanese Wikipedia and English Wikipedia per article, with a section for any local discussion and a comment noting the import date.
- [ ] **Shikinaisha pages with broken ILL destinations** — ILLs pointing to "Unknown" as target from early workflow. Most are identifiable from context; fix with `fix_ill_destinations.py` pass.

---

## Repository / script tasks

- [ ] **Move hardcoded credentials to environment variables** — all scripts use hardcoded `USERNAME`/`PASSWORD`. Must be done before repo can be made public. Use `.env` + `python-dotenv` or environment variables directly.
- [x] **Consolidate active root scripts into `shinto_miraheze/`** — done.

---

## Known external issues

- [ ] **Wikidata item deletions** — a batch of Wikidata items created by an earlier script (for interlanguage link targets) were deleted by another editor on Wikidata. The deletions happened without opportunity to contest or add supplementary content that might have justified keeping them. Need to assess scope (which items were deleted, whether they can be re-created with stronger sourcing) and develop a strategy for re-creation or working around the missing QIDs.

---

## Longer term (architecture)

These are tracked in detail in [VISION.md](VISION.md). Listed here for completeness.

- [ ] **Namespace restructure** — introduce `Data:`, `Meta:`, `Export:` namespaces per the VISION.md plan
- [ ] **Move `{{ill}}` export data to `Export:` namespace** — simplify mainspace to plain `[[links]]`; keep the ILL/QID data in `Export:` pages only
- [ ] **Category name standardization** — establish canonical English names for all categories; categories handled via Wikidata rather than translation
- [ ] **Pramana integration** — connect `Data:` pages to pramana.dev as the canonical ID backend
- [ ] **Automated translation pipeline** — take any Japanese Wikipedia page and produce a consistent translated page with proper ILL/Wikidata connections
- [ ] **Change-tracking bot** — monitor wiki changes and propagate them across namespace layers
