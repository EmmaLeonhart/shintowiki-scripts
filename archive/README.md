# archive/

Retired / one-off scripts kept for reference only. **Nothing here is wired
into CI** — no workflow invokes these, and they are not part of any active
pipeline. Do not assume they still run against current APIs or schemas.

- `import_to_fandom.py` — local manual single-page miraheze→fandom history
  import (superseded by the `fandom_mirror` op + `fandom/` import workflows).
- `test_fandom_login.py` — local smoke test for fandom mwclient auth.
- `process_dupl.py` — local duplicated-content section merger (superseded by
  the claude.ai remote routine that consumes `remote_queue.json`).
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

## 2026-05-28: 12 retired scripts deleted (not just archived)

Per Emma's directive, the following 12 retired scripts that contained the
`[REDACTED_SECRET_*]` / `[REDACTED_USER_*]` placeholder literals were
deleted from the working tree rather than kept in archive. The placeholders
are a workflow hazard — they trip readers (human or AI) into thinking
they're live-secret redactions when they're actually sentinel strings.
The scripts themselves were already dead (superseded by orchestrator ops
or one-shot work that's done). They remain in git history; the eventual
`git filter-repo --replace-text` rewrite (per todo.md "Secret removal")
will remove the literals from history.

Deleted (root-level archive):
- `fix_ill_destinations.py` — superseded by `normalize_ill_wikidata` op.
- `create_category_qid_redirects.py` — superseded by orchestrator-side
  category wikidata lookup (per 2026-05-08 todo note).
- `resolve_category_wikidata_from_interwiki.py` — same as above.
- `generate_shikinaisha_pages_v25_with_redirects.py` — V25 one-shot
  historical generator; the pages exist.

Deleted (`archive/wikidata_scripts/` — entire directory removed):
- `sync_person_infobox.py`, `tidy_categories.py`,
  `tier3_ja_to_enwiki_updater.py`, `patch_ill_english_labels_v9.py`,
  `proposed_entries_streamlit.py`, `add_enwiki_interwiki.py`,
  `category_interwiki_restore_bot.py`, `jawiki_cat_restore_bot.py` —
  all retired Wikidata-side scripts. All Wikidata writes now go through
  the QuickStatements pipeline only (see `CLAUDE.md`).
