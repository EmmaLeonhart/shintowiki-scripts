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

## From [[Open questions]] — Emma's 2026-05-28 dispositions

Emma answered the whole Open Questions backlog on the wiki (pulled to
the repo at commit 4738295d / origin). Her answers are the "**" sub-bullets
on that page. Acting on them (the page itself is wiki-wins — prune the
bullets ON THE WIKI, not in the repo copy; no local wiki creds, so bullet
removal is Emma's or a CI edit). Read latest via
`git show origin/main:"git_synced/Open questions.wiki"`.

- [ ] **Recreate `[[Category:Categories missing wikidata]]` via the orchestrator — Emma's design.** Emma: "just recreate it… every single page should have the `{{wikidata link}}` template at the bottom; blank for these." Concrete steps: (1) the mainspace + category orchestrators add a BLANK `{{wikidata link}}` to any page (ns 0 + 14) that has none; (2) tag pages whose wikidata link is missing OR present-but-not-actually-linking-Wikidata into a CRUD category (`[[Category:Categories missing wikidata]]` for cats; the page-level equivalent for mainspace — reconcile with existing `tag_pages_without_wikidata.py` / `[[Category:Pages without wikidata]]`); (3) "pages without wikidata" becomes a crud category. Slight edit to the `{{wikidata link}}` template + an orchestrator op. Verify against existing ops (`tag_pages_without_wikidata`, the wikidata-link template) before building — much may already exist.
- [ ] **Verify "already done" items, then prune their Open-Questions bullets (on the wiki).** Emma marked these done/no-longer-concerning — confirm via code/log/SPARQL, record disposition, leave the bullet for Emma/CI to strike on the wiki: (a) Kana ojp-hani stragglers — "check the SPARQL and remove if done" (read-only `seed_kana_qualifier.py --dry-run` is freeze-safe; edits are not, freeze to 2026-06-06); (b) AI translation pipeline — Emma: "this does in fact exist" → find it, correct `todo.md`'s "doesn't exist yet"; (c) Enrich autocreated categories — Emma: category is empty / work already done → confirm `Category:Categories autocreated by EmmaBot` membership, drop the todo item; (d) Secret-removal history rewrite — Emma: "already done" → grep history for the redacted literals, drop if clean; (e) Category race-condition audit — Emma: "no longer concerning" → drop the todo item.
- [ ] **Drop the dead todo/VISION items Emma killed.** Emma: fandom Infobox→Portable conversion "no AI does this" (drop); VISION architecture (namespace restructure, Pramana, change-tracking bot) "no longer happening" — drop all except the automated translation pipeline, which "exists right now" (note it as shipped). Remove these from `todo.md`.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
