# TODO

Consolidated list of open tasks. Historical/completed work is tracked in [DEVLOG.md](DEVLOG.md). See [VISION.md](VISION.md) for the broader architecture plan.

---

## Immediate / in progress

- [ ] **Crud category cleanup** â€” `remove_crud_categories.py` running (2026-02-25); stripping [[Category:X]] tags from all member pages across 112 subcategories of Category:Crud_categories. Now runs in GitHub Actions with `--max-edits` cap and is expected to take several days of automated runs.

- [ ] **Talk page migration** â€” `migrate_talk_pages.py --apply` running (2026-02-25); rebuilds every talk page into a clean structure and imports discussion seeds from ja/en/simple Wikipedia via QID sitelinks. State file: `shinto_miraheze/migrate_talk_pages.state`. Log: `shinto_miraheze/migrate_talk_pages.log`. Now runs in GitHub Actions with `--max-edits` cap and is expected to take several days of automated runs.

- [ ] **Template:Talk page header** - Edit this template so that it fits all requirements for migrated/transformed talk pages.
---

## Wiki content tasks (on shintowiki)

### High priority

- [ ] **Fix template categories outside `<noinclude>`** â€” some templates have `[[Category:â€¦]]` and `{{wikidata link}}` placed outside `<noinclude>`, causing every page that transcludes the template to inherit those categories. Move stray tags into `<noinclude>`.
- [ ] **ILLs without `WD=`** â€” ILL templates missing a `WD=` parameter are broken by design. Run `fix_ill_destinations.py` or a new script to identify and fill in missing `WD=` values. Do not blindly overwrite â€” check the local context of each.
- [ ] **Category:Q* pages in category namespace** â€” ~77 pages exist as `Category:Q{QID}` (wrong namespace). These should either be deleted or moved to mainspace as `Q{QID}` redirects.
- [ ] **Duplicate QID disambiguation pages** â€” 621 `Q{QID}` mainspace pages point to 2+ categories. Needs human review to decide which category correctly holds the QID.
- [ ] **Category pages with spaghetti wikitext** â€” category pages have accumulated Japanese text, stray category links, redundant `{{wikidata link}}` placements, and auto-generated junk from old passes. Goal: strip to clean English description + `{{wikidata link}}` + parent category links only.
- [ ] **Translate all category names in [Category:Japanese language category names](https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names)** â€” ensure every category in this tracking set is migrated to a canonical English category title.
- [ ] **Resolve migration issues in [Category:Erroneous qid category links](https://shinto.miraheze.org/wiki/Category:Erroneous_qid_category_links)** â€” fix category/QID mismatches and complete any blocked merges or redirect corrections.
- [ ] **[Category:Pages with duplicated content](https://shinto.miraheze.org/wiki/Category:Pages_with_duplicated_content)** â€” pages where the same content exists under multiple titles. Needs human review per page: which title is canonical, whether a history merge is appropriate.
- [ ] **Audit category pages for race-condition artifacts** â€” some categories may have inconsistent state from the `resolve_category_wikidata` and `create_category_qid_redirects` scripts running concurrently. Scope unknown; needs an audit script.
- [ ] **Review post-audit leftovers** - many entries in https://shinto.miraheze.org/wiki/Category:Japanese_language_category_names appear to be downstream artifacts; verify whether any automated cleanup is still needed.

### Lower priority

- [ ] **Categories missing Wikidata** â€” categories with interwikis but no `{{wikidata link}}`. Many are Japan-only or internal maintenance categories with no real Wikidata item; assess per-category.
- [ ] **Categories with interwikis but no Wikidata link added** â€” older script passes added interwiki links without adding the `{{wikidata link}}` template. Re-run the wikidata link script on these.
- [ ] **Multiple `{{wikidata link}}` on one page** â€” usually indicates a Wikidata disambiguation issue. Needs per-case review.
- [ ] **Talk pages** â€” currently contain junk (Wikipedia AFC notices, old bot messages). Plan: overwrite with imported talk page content from Japanese Wikipedia and English Wikipedia per article, with a section for any local discussion and a comment noting the import date.
- [ ] **Shikinaisha pages with broken ILL destinations** â€” ILLs pointing to "Unknown" as target from early workflow. Most are identifiable from context; fix with `fix_ill_destinations.py` pass.
- [ ] **Switch to [[User:EmmaBot]] for automation** - planned for CI/CD rollout so bot edits are clearly separated from human edits and easier to audit.
---

## Repository / script tasks

- [ ] **Move hardcoded credentials to environment variables** â€” complete for active `shinto_miraheze` scripts; remaining legacy/archive scripts still need migration before full open-source cleanup.

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





