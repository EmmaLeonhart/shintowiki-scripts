# TODO

Consolidated list of known tasks. See [VISION.md](VISION.md) for the broader architecture plan.

---

URGENT

check notes.txt and get rid of it if it is clear here

OK so basically what is going on the Claude ended up attempting to make a script to fix some of the Japanese categories stuff particularly ones that have a Japanese category name but no wiki data and it didn't really complete it it ended up getting stuck basically there it might end up just starting running again on its own but I'm not really sure but this is just an urgent thing that it has to fix something I am potentially interested in is making a thing that generates quick statement so that I can have these categories on wiki data but I am not 100% confident on it like there's a lot of Japanese like Japanese only categories that probably need wiki data items but whether it's wise for me to do so it's kind of questionable

edit: notes.txt is covered here so deleting it

desktop.ini is another thing to look over

look over settings.local.json to make sure there's no secret leakage

## Immediate / in progress

- [ ] **Crud category cleanup** — `remove_crud_categories.py` running (2026-02-25); stripping [[Category:X]] tags from all member pages across 112 subcategories of Category:Crud_categories. No state file; safe to re-run (skips already-empty categories automatically).

- [x] **Delete `Category:Jawiki_resolution_pages`** — complete (2026-02-26). 10,239 pages deleted by `delete_jawiki_resolution_pages.py`.
- [x] **Category page wikitext normalization** — complete (2026-02-26). 23,571 of 24,045 category pages edited by `normalize_category_pages.py`. State file preserved for safe re-runs.

- [ ] **Talk page migration** — `migrate_talk_pages.py --apply` running (2026-02-25); rebuilds every talk page into a clean structure and imports discussion seeds from ja/en/simple Wikipedia via QID sitelinks. State file: `shinto_miraheze/migrate_talk_pages.state` (201+ pages done). Log: `shinto_miraheze/migrate_talk_pages.log`.

- [x] **History merges** — 184 pairs merged (2026-02-23). Combined revision histories of old-name and new-name pages for all matched `{{moved to}}`/`{{moved from}}` pairs. 7 edge cases left unresolved; tagged in `Category:move templates that do not link to each other` for manual review. History fully preserved except for those marginal pages.
- [x] **Re-run `resolve_duplicated_qid_categories.py`** — complete (2026-02-23). Only 3 pages remained; all were duplicate Latin-name pairs tagged as erroneous. The ~75 expected remainder had already been resolved by intervening script passes.
- [x] **`[[sn:...]]` interwiki removal** — complete (1 page, 3 links).
- [x] **Wanted categories created** — 153 pages created.
- [x] **`Category:Generated_x-no-miya_lists` deleted** — 67 User namespace pages deleted.
- [ ] **Template:Talk page header** Edit this template so that it fits all of our requirements for our new migrated/transformed talk pages.
---

## Wiki content tasks (on shintowiki)

### High priority

- [ ] **Fix template categories outside `<noinclude>`** — some templates have `[[Category:…]]` and `{{wikidata link}}` placed outside `<noinclude>`, causing every page that transcludes the template to inherit those categories. Move stray tags into `<noinclude>`.
- [ ] **ILLs without `WD=`** — ILL templates missing a `WD=` parameter are broken by design. Run `fix_ill_destinations.py` or a new script to identify and fill in missing `WD=` values. Do not blindly overwrite — check the local context of each.
- [ ] **Category:Q* pages in category namespace** — ~77 pages exist as `Category:Q{QID}` (wrong namespace). These should either be deleted or moved to mainspace as `Q{QID}` redirects.
- [ ] **Duplicate QID disambiguation pages** — 621 `Q{QID}` mainspace pages point to 2+ categories. Needs human review to decide which category correctly holds the QID.
- [ ] **Category pages with spaghetti wikitext** — category pages have accumulated Japanese text, stray category links, redundant `{{wikidata link}}` placements, and auto-generated junk from old passes. Goal: strip to clean English description + `{{wikidata link}}` + parent category links only.
- [ ] **Translate all category names in [Category:Japanese language category names](https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names)** — ensure every category in this tracking set is migrated to a canonical English category title.
- [ ] **Resolve migration issues in [Category:Erroneous qid category links](https://shinto.miraheze.org/wiki/Category:Erroneous_qid_category_links)** — fix category/QID mismatches and complete any blocked merges or redirect corrections.
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
