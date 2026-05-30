# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

## Q4 — finish self-categorizing wikidata-link (steps 1-2 shipped 2026-05-30)

Core shipped (DEVLOG 2026-05-30): `{{wikidata link}}` self-categorizes on a blank invocation (ns 0/14, cascade-safe) and `ops/wikidata_link.py` appends a blank template instead of the literal category. Remaining:
- [ ] Make `[[Category:Pages without wikidata]]` a crud category (tag it into `Category:Crud categories`) so `remove_crud_categories` strips the LEGACY literal tags; the template-emitted category is transclusion-sourced and survives. (Wiki edit → needs CI/creds, or a small repo script that CI runs.)
- [ ] Recreate `[[Category:Categories missing wikidata]]` as a typed parent + wire orchestrators to add it to pages lacking the template / whose wikidata link doesn't resolve (`ops/wikidata_lookup.py` already validates QIDs — tie in there).

## Sync `.state`-file removal — SAFE REDESIGN (Emma approved 2026-05-28, "do it now") — ATTENDED ONLY

Drop `sync_git_synced_pages.state`, `sync_need_translation.state`, `sync_miraheze_unique_pages.state`, `sync_fandom_unique_pages.state`, `sync_duplicated_content.state` by reconstructing the per-page baseline durably instead of from a committed file. **Safety-critical, NOT locally dry-runnable (no wiki creds on the dev box) — attended, CI-verified pass only; never let the unattended hourly cron ship it** (a baseline-reconstruction bug mass-deletes synced pages — the 2026-05-10 / 05-27 incidents).
- [ ] **Embed the baseline in the push edit summary** (`[sync-base:<sha1-of-pushed-content>]`): records base_sha; base_revid = that push's revid (recover by walking page history for the most recent EmmaBot edit carrying the marker). Covers the PUSH baseline with zero new state.
- [ ] **Reconstruct the PULL baseline from content** (`base_sha = sha1(repo file)` after a pull; the no-op fast-path needs no baseline). Only when wiki ≠ repo, derive `wiki_changed` by comparing the wiki top-revision content-sha to the repo sha (no full content-history walks — server-load).
- [ ] **Preserve the load-bearing `base_sha is None` anti-deletion gate** (never-synced PUSH-CREATE vs synced-then-decategorized DELETE, via presence of a prior `[sync-base:...]` edit in page history); bias hard toward never-deleting on ambiguity.
- [ ] **Keep `sync_revision_aware.py` working** (now most-recent-edit-wins) with the reconstructed baselines.
- [ ] **Test before wiring:** `--dry-run`-only verification mode, run on CI vs the live wiki for each of the 5 dirs; diff its decisions against the current `.state`-based decisions; only delete the `.state` files once decisions match for a full cycle. Roll out one script at a time.

## Lowercase Template:Infobox case-collision — prune inert repo files

The case-collision cleanup is auto-wired + self-clearing on the wiki (no action there). Repo task left:
- [ ] **Prune the inert lowercase `.wiki` files from a case-sensitive checkout.** The `miraheze_unique/` + `fandom_unique/` `Template%3AInfobox <lowercase>.wiki` files (13 each) are sync-ignored + harmless but still tracked; they can't be `git rm`'d from the Windows case-insensitive dev checkout (path ops fold to the capital twin). Remove from a Linux/case-sensitive checkout and commit. Non-urgent.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits; set `User-Agent` (Miraheze enforces a UA policy — a generic UA gets 403; use e.g. `ShintoWikiBot/1.0 (…repo URL…; email)`); `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
