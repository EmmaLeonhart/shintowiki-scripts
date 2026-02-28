# TODO

Consolidated list of open tasks. Historical/completed work is tracked in [DEVLOG.md](DEVLOG.md). See [VISION.md](VISION.md) for the broader architecture plan.

---

## Automation boundary

The GitHub Actions cleanup loop (`shinto_miraheze/cleanup_loop.sh`, runs daily) handles everything that can be scripted safely and repeatably. **Everything outside the loop requires manual intervention — there are no easy script additions left.** The remaining open tasks all require human judgment, prereq work, or infrastructure that does not yet exist.

### Currently automated (cleanup loop)

These run automatically every 24 hours via GitHub Actions. No manual action needed unless something breaks.

- **Unused category deletion** — `delete_unused_categories.py`: deletes Special:UnusedCategories pages, skipping any with `{{Possibly empty category}}`.
- **Category page normalization** — `normalize_category_pages.py`: enforces the canonical templates / interwikis / categories layout on every category page.
- **Talk page migration** — `migrate_talk_pages.py`: rebuilds talk pages and seeds them with discussion content from ja/en/simple Wikipedia. State file: `shinto_miraheze/migrate_talk_pages.state`.
- **Shikinaisha talk page tagging** — `tag_shikinaisha_talk_pages.py`: adds a “generated from Wikidata” notice to talk pages of Wikidata-generated shikinaisha pages.
- **Crud category cleanup** — `remove_crud_categories.py`: strips `[[Category:X]]` tags from member pages across all subcategories of Category:Crud_categories.
- **Erroneous QID category link fixes** — `fix_erroneous_qid_category_links.py`: corrects category/QID mismatches flagged in Category:Erroneous_qid_category_links.
- **Legacy template removal** — `remove_legacy_cat_templates.py`: removes `{{デフォルトソート:…}}` and `{{citation needed}}` artifacts from category pages.

### Requires manual intervention

- [ ] **Template:Talk page header** — Edit this template so that it fits all requirements for migrated/transformed talk pages.

---

## Wiki content tasks (on shintowiki)

All items below require manual editing or human review. None have a safe automated path right now.

### High priority

- [ ] **Fix template categories outside `<noinclude>`** — some templates have `[[Category:…]]` and `{{wikidata link}}` placed outside `<noinclude>`, causing every page that transcludes the template to inherit those categories. Move stray tags into `<noinclude>`. **Manual edit required per template.**
- [ ] **ILLs without `WD=`** â€” ILL templates missing a `WD=` parameter are broken by design. Run `fix_ill_destinations.py` or a new script to identify and fill in missing `WD=` values. Do not blindly overwrite â€” check the local context of each.
- [ ] **Duplicate QID disambiguation pages** â€” 621 `Q{QID}` mainspace pages point to 2+ categories. Needs human review to decide which category correctly holds the QID.
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

- [ ] **Namespace restructure** â€” introduce `Data:`, `Meta:`, `Export:` namespaces per the VISION.md plan
- [ ] **Move `{{ill}}` export data to `Export:` namespace** â€” simplify mainspace to plain `[[links]]`; keep the ILL/QID data in `Export:` pages only
- [ ] **Category name standardization** â€” establish canonical English names for all categories; categories handled via Wikidata rather than translation
- [ ] **Pramana integration** â€” connect `Data:` pages to pramana.dev as the canonical ID backend
- [ ] **Automated translation pipeline** â€” take any Japanese Wikipedia page and produce a consistent translated page with proper ILL/Wikidata connections
- [ ] **Change-tracking bot** â€” monitor wiki changes and propagate them across namespace layers





