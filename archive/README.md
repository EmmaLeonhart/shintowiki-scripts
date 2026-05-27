# archive/

Retired / one-off scripts kept for reference only. **Nothing here is wired
into CI** — no workflow invokes these, and they are not part of any active
pipeline. Do not assume they still run against current APIs or schemas.

- `import_to_fandom.py` — local manual single-page miraheze→fandom history
  import (superseded by the `fandom_mirror` op + `fandom/` import workflows).
- `test_fandom_login.py` — local smoke test for fandom mwclient auth.
- `process_dupl.py` — local duplicated-content section merger (superseded by
  the claude.ai remote routine that consumes `remote_queue.json`).
- `wikidata_scripts/` — older Wikidata-side scripts (interwiki restore,
  category tidy, infobox sync, label patches, Streamlit proposal viewer).
  All Wikidata writes now go through the QuickStatements pipeline only
  (see `CLAUDE.md`), so these are not used.
- `fix_ill_destinations.py` — old "fix `{{ill|...|WD=Q...}}` destinations"
  sweep. Superseded by `shinto_miraheze/orchestrators/ops/normalize_ill_wikidata.py`
  which handles the same job (and the missing-`qid=` case) per-page on every
  orchestrator sweep. Also carries one of the hardcoded historical secrets
  flagged for `git filter-repo --replace-text` rewrite — do not re-run.
- `create_category_qid_redirects.py` — created `Q{QID}` redirects for category
  pages with `{{wikidata link|Q...}}`. Per `todo.md` (2026-05-08), no longer
  wired into any active workflow; superseded by `normalize_category_page` +
  category-side wikidata-lookup orchestrator ops.
- `resolve_category_wikidata_from_interwiki.py` — resolved Wikidata for
  category pages via interwiki links. Per `todo.md` (2026-05-08), no longer
  wired; superseded by orchestrator-side wikidata lookup.
- `generate_shikinaisha_pages_v25_with_redirects.py` — V25 historical
  Shikinaisha page generator (regular + Wikidata-redirect cases). One-shot;
  the pages have long since been generated.
- `strip_mediawiki_banners.py` — one-shot sweep over ns=8 MediaWiki pages
  to strip `<!-- History offloaded: ... -->` banners that `history_offload`
  left behind. ns=8 is excluded from every recurring orchestrator, so no
  new banners are being produced — the cleanup is done.
- `unstick_duplicated_content_conflicts.py` — one-shot unstick for ~135
  duplicated-content pages that `sync_duplicated_content.py` was
  permanently skipping with `CONFLICT`. The sync's wiki-wins policy
  (2026-05-23) plus the revision-aware refactor (2026-05-27) make this
  recovery unnecessary going forward.
- `fix_sexagenary_mt_entropy.py` — cleaned machine-translation entropy
  from the 60 `git_synced/` Sexagenary cycle pages. One-shot; the pages
  have been standardised.

If you resurrect something here, move it back out of `archive/` into the
appropriate directory rather than running it in place.
