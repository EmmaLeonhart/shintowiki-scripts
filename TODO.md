# TODO

Consolidated list of known tasks. See [VISION.md](VISION.md) for the broader architecture plan.

---

## Immediate / in progress

- [ ] **Full history import** — the wiki was restored from Archive.org XML with only the most recent revision per page. The full edit history XML still needs to be imported.
- [ ] **History merges** — pages that need `{{moved to}}` / `{{moved from}}` templates to preserve attribution after page moves. Two separate waves of moves means some pages need both.

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
- [ ] **Move legacy scripts to `archive/`** — the root and `shinto_miraheze/` still contain superseded scripts. Move them rather than delete so history is preserved.
- [ ] **Consolidate active root scripts into `shinto_miraheze/`** — active scripts currently spread across root and `shinto_miraheze/`; consolidate into one canonical location.

---

## Longer term (architecture)

These are tracked in detail in [VISION.md](VISION.md). Listed here for completeness.

- [ ] **Namespace restructure** — introduce `Data:`, `Meta:`, `Export:` namespaces per the VISION.md plan
- [ ] **Move `{{ill}}` export data to `Export:` namespace** — simplify mainspace to plain `[[links]]`; keep the ILL/QID data in `Export:` pages only
- [ ] **Category name standardization** — establish canonical English names for all categories; categories handled via Wikidata rather than translation
- [ ] **Pramana integration** — connect `Data:` pages to pramana.dev as the canonical ID backend
- [ ] **Automated translation pipeline** — take any Japanese Wikipedia page and produce a consistent translated page with proper ILL/Wikidata connections
- [ ] **Change-tracking bot** — monitor wiki changes and propagate them across namespace layers
