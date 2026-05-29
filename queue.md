# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## Lowercase Template:Infobox case-collision cleanup — IN PROGRESS, no human action (2026-05-28)

- [ ] **Wait for transclusions to drain naturally; deletion is auto-wired.**
  Status as of 04:50Z 2026-05-28: `Template:Infobox noble` cleared
  on miraheze (0 transclusions; the next cleanup-loop fire will delete
  the lowercase variant). The other 9 templates still have
  transclusions (counts dropping ~1-3/hour as
  `canonicalize_template_case` op grinds through mainspace), so the
  deletion script is a no-op for them until they hit 0. Auto-fire is
  wired into `wiki-cleanup.yml` after `remove_crud_categories`
  (`256cee7d`), so deletions happen on the cleanup-loop schedule
  without further work. **No human action needed; just wait.**

- [ ] **Prune the 26 inert lowercase `.wiki` files from a case-sensitive checkout.**
  The recreation ping-pong is fixed (2026-05-28): both unique-sync
  scripts now skip `LOWERCASE_COLLISION_TITLES`, so the deleter can
  remove the lowercase wiki pages and the sync never recreates them.
  The matching repo files (`miraheze_unique/` + `fandom_unique/`
  `Template%3AInfobox <lowercase>.wiki`, 13 each) are now sync-ignored
  and harmless, but still tracked — and they can't be `git rm`'d from
  the Windows case-insensitive dev checkout (every path op folds to the
  on-disk capital twin). Remove them from a Linux/case-sensitive
  checkout and commit. Non-urgent (they're inert).

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
