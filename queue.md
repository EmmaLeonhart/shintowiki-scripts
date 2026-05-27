# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## sync_git_synced_pages deletes new-repo / not-yet-pushed pages (2026-05-27)

- [ ] **Fix the "wiki no longer has this file → delete locally" branch.**
  Commit `d8212c92` added `git_synced/Open questions.wiki` to the repo
  at 21:07 UTC. The CI sync (`49ee2434`) ran at 22:46 UTC and deleted
  the local file because the wiki page didn't exist yet — Emma had to
  manually recreate it on the wiki at 22:58 UTC. The sync's delete
  branch should require **either** (a) a prior `sync_commit` baseline
  showing the file used to be on the wiki, or (b) the file is older
  than N minutes since first commit. Currently it just sees
  `file in repo + page not in [[Category:Git synced pages]]` and
  deletes. Repro: add a new `.wiki` file under `git_synced/`, commit
  but don't push to wiki yet, run sync — it deletes the file. Same
  shape bug may exist in `sync_fandom_unique_pages.py`,
  `sync_miraheze_unique_pages.py`, `sync_need_translation.py`,
  `sync_duplicated_content.py`. Look at the deletion branch in each.

## Case-collision lowercase Template:Infobox pages (2026-05-27)

- [ ] **Run `delete_lowercase_template_collisions.py --apply` once the
  `canonicalize_template_case` sweep finishes.** Script lives at
  `shinto_miraheze/delete_lowercase_template_collisions.py`; per-page
  safeguard refuses to delete unless (a) lowercase variant exists,
  (b) canonical capitalised twin exists, (c) content is byte-identical
  OR lowercase is a `#REDIRECT` to canonical (relaxed 2026-05-27 — see
  DEVLOG), (d) `embeddedin` returns zero transclusions. Currently every
  page on both wikis still has live transclusions; re-run after another
  full orchestrator cycle or two.
## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
