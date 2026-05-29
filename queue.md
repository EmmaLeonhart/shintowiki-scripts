# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## Sync `.state`-file removal — SAFE REDESIGN (Emma approved 2026-05-28, "do it now")

Emma chose the safe-redesign path (not the naive git-history derivation,
which is unsafe — see DEVLOG 2026-05-28 / todo.md). Goal: drop
`sync_git_synced_pages.state`, `sync_need_translation.state`,
`sync_miraheze_unique_pages.state`, `sync_fandom_unique_pages.state`,
`sync_duplicated_content.state` by reconstructing the per-page baseline
`(base_revid, base_sha, base_commit)` durably instead of from a committed
file. **Safety-critical, and NOT locally dry-runnable (no wiki creds on
the dev box) — implement in a focused, attended, CI-verified pass; do NOT
let the unattended hourly cron ship this.**

Design to implement + verify:
- [ ] **Embed the baseline in the push edit summary.** On every PUSH, append a machine-readable marker to the summary, e.g. `[sync-base:<sha1-of-pushed-content>]`. The pushed content == the repo file content, so the marker records base_sha; base_revid = that push's revid (recoverable by walking page history for the most recent EmmaBot edit whose summary carries the marker). This covers the PUSH baseline with zero new state.
- [ ] **Reconstruct the PULL baseline from content.** PULLs make no wiki edit, so no marker. After a pull, repo content == the pulled revision's content, so `base_sha = sha1(current repo file)` is trivially correct, and the no-op fast-path (`local_sha == wiki_sha`) already needs no baseline. Only when wiki ≠ repo do we need direction: derive `wiki_changed` by checking whether the wiki's current top revision content-sha equals the repo sha (unchanged) vs differs (changed); avoid full content-history walks (server-load budget).
- [ ] **Preserve the load-bearing `base_sha is None` anti-deletion gate.** The orphan branch must still distinguish "new repo file never synced → PUSH-CREATE" from "was synced, wiki dropped category → DELETE local". Reconstruct "ever synced?" from: presence of a prior EmmaBot `[sync-base:...]` edit in the page's wiki history. If none AND no merge-base content match → treat as never-synced (PUSH-CREATE, never DELETE). Bias hard toward never-deleting on ambiguity (the 2026-05-10 / 2026-05-27 incidents were both spurious deletions).
- [ ] **Keep revision-aware conflict resolution working** (sync_revision_aware.py) — feed it the reconstructed baselines.
- [ ] **Test before wiring:** add a `--dry-run`-only verification mode and run it on CI (workflow_dispatch) against the live wiki for each of the 5 dirs; diff its decisions against the current `.state`-based decisions on the same data. Only delete the `.state` files + remove `load_state`/`save_state` once the dry-run decisions match for a full cycle. Roll out one script at a time.

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

## From [[Open questions]] — Emma's 2026-05-28 dispositions

Emma answered the whole Open Questions backlog on the wiki (pulled to
the repo at commit 4738295d / origin). Her answers are the "**" sub-bullets
on that page. Acting on them (the page itself is wiki-wins — prune the
bullets ON THE WIKI, not in the repo copy; no local wiki creds, so bullet
removal is Emma's or a CI edit). Read latest via
`git show origin/main:"git_synced/Open questions.wiki"`.

- [ ] **`[[Category:Categories missing wikidata]]` / blank-`{{wikidata link}}` — build spec (verified 2026-05-28, much already exists).** Investigation result:
  - **Already exists:** `ops/wikidata_link.py` (runs in the mainspace/category/template orchestrators, ns 0/10/14) already TAGS pages with no `{{wikidata link|…}}`: mainspace+category → append `[[Category:Pages without wikidata]]`; template → `[[Category:Templates missing wikidata]]` inside `<noinclude>` (deliberately, to avoid transclusion cascade). Legacy `tag_pages_without_wikidata.py` is the standalone twin. The `{{wikidata link}}` template lives in `miraheze_unique/` + `fandom_unique/` (repo-wins sync).
  - **Gap vs Emma's design** ("every page has the template at the bottom, blank for these; the template self-categorizes"): today the op appends a *category*, not a blank *template*. To do it Emma's way: (1) edit `{{wikidata link}}` to add a no-QID branch — `{{#if:{{{1|}}}|<current render+interwikis>|<render nothing>[[Category:Pages without wikidata]]}}` so a blank invocation self-categorizes and shows nothing (current body renders `{{q|}}` + empty `[[da:]]` interwikis when arg 1 is absent — broken, must be guarded); (2) change the op to APPEND a blank `{{wikidata link}}` to pages with neither link nor template; (3) make `[[Category:Pages without wikidata]]` a crud category; (4) "wikidata link present but QID doesn't resolve" → tie in `ops/wikidata_lookup.py` (already validates QIDs).
  - **⚠ Design blocker to resolve before building:** a self-categorizing template via `<includeonly>` re-introduces exactly the **transclusion-cascade bug** `wikidata_link.py` was written to avoid (a category emitted by the template body lands on every page that transcludes it). `{{wikidata link}}` is normally placed directly on content pages, but on *template* pages a blank one would cascade. Need a cascade-safe mechanism (e.g. only self-categorize in ns 0/14, or keep the noinclude split) before the template edit is safe. **Also a wiki-wide mass edit** (blank template appended to thousands of pages) — must respect the editing-pace philosophy + orchestrator budgets; arguably an attended rollout. Resolve the cascade approach with Emma, then build template-edit + op-change behind a dry-run.
- [ ] **Verify "already done" items, then prune their Open-Questions bullets (on the wiki).** Emma marked these done/no-longer-concerning — confirm via code/log/SPARQL, record disposition, leave the bullet for Emma/CI to strike on the wiki: (a) Kana ojp-hani stragglers — "check the SPARQL and remove if done" (read-only `seed_kana_qualifier.py --dry-run` is freeze-safe; edits are not, freeze to 2026-06-06); (b) AI translation pipeline — Emma: "this does in fact exist" → find it, correct `todo.md`'s "doesn't exist yet"; (c) Enrich autocreated categories — Emma: category is empty / work already done → confirm `Category:Categories autocreated by EmmaBot` membership, drop the todo item; (d) Secret-removal history rewrite — Emma: "already done" → grep history for the redacted literals, drop if clean. (Done this pass: (b) translation pipeline confirmed to exist via the `need_translation/` cloud-queue worker; (e) race-condition audit dropped per Emma.)

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
