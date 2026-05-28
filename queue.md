# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## Case-collision lowercase Template:Infobox pages — actual blocker (2026-05-28 investigation)

- [ ] **`canonicalize_template_case` op is NOT clearing the transclusions
  despite the mainspace orchestrator sweep completing.** Investigation
  on 2026-05-28 (commit `112a92b0` showed `mainspace_orchestrator.state`
  rolling over from 46,274 lines to 0 — full sweep complete since the
  op shipped on 2026-05-26 in `f27ea68c`):

  Sampled 5 mainspace pages still transcluding the lowercase templates:
  Kumano Kodō, Japanese New Year, Aizu-hime-no-Kami, Ikeda Tsuneoki,
  Chausuyama Kofun (Osaka). All have lowercase `{{Infobox X}}` or
  `{{infobox X}}` calls. The op REWRITES all 5 correctly when tested
  directly on the live wiki content (verified via local
  `apply(title, content)` call — returns `(new_text, summary)` with the
  canonical form). But the most recent bot edit on these mainspace pages
  is 2026-05-15 / 17 — BEFORE the op shipped on 2026-05-26.

  So either (a) the recent sweep visited these pages but the pre-heavy
  save was rejected/failed silently and the page got `_mark_done`-ed
  anyway via the error path, (b) the iteration cap
  (`MAX_STATE_GROWTH_PER_RUN`) made the sweep declare "exhausted"
  prematurely without actually visiting every page, or (c) some sibling
  pre-heavy op is throwing an exception on these specific pages that
  aborts the whole batch.

  Plus `Aizu-hime-no-Kami` is in `miraheze_unique/` — its history shows
  Emma's manual canonicalization at 20:13Z was immediately overwritten
  by `sync_miraheze_unique` (push from repo, repo had the lowercase form)
  at 20:56Z. Same pattern as the page-churn issue today's verification
  said was solved (`736d0383`) — but the verification was about
  alternation streaks (≥3 toggles), not single overwrites.

  **Next diagnostic step:** spot-check what
  `mainspace_orchestrator.state` accumulated during the just-finished
  sweep — was Kumano Kodō ever in it? Look at the orchestrator's
  cleanup-loop step logs (`gh run view --log` filtered to mainspace
  orchestrator step) for the `[N] Kumano Kodō ...` line in any recent
  run, to see what outcome was logged. If no log line ever mentioned
  it, the iteration didn't reach it. If a log line exists but no edit
  followed, the pre-heavy save failed and we need to find the
  underlying error.

  **Sync-dir local-files canonicalization DONE** (2026-05-28,
  see DEVLOG). Wrote `shinto_miraheze/canonicalize_sync_dir_files.py`
  — a one-shot script that walks all five sync dirs and applies the
  same `canonicalize_template_case` op to local `.wiki` files. Apply
  pass edited 8 files (3 in `miraheze_unique/`, 3 in `fandom_unique/`,
  2 in `need_translation/`). Re-run is a no-op (idempotent). Next
  sync cycle will push the canonicalization to the wiki, removing the
  repo-wins-overwrite cycle that was reverting Emma's manual fixes.

- [ ] **Then re-run `delete_lowercase_template_collisions.py --apply`**
  once the surviving transclusions drain. **Progress update 2026-05-28
  03:50Z:** the local-files canonicalization commit `02a194ba` is
  propagating to the wiki via the active sync. Verified
  `Aizu-hime-no-Kami` was pushed canonical at 03:39:43Z (was lowercase
  before). Result: **`Template:Infobox noble` is now at 0 transclusions
  on miraheze** (was 1). The other 9 templates still have transclusions
  on miraheze; all 10 still have transclusions on fandom (fandom side
  is way further behind — needs separate work). Next: wire the deletion
  script into a workflow (probably `workflow_dispatch` for on-demand
  trigger, since the script's per-template safety gate makes it safe to
  auto-fire whenever any template hits 0).

  Miraheze counts as of 03:50Z (uncapped, from `embeddedin?eilimit=100`):
  * chinese 1, film 3, historic site 7, holiday 16, kofun 3,
    mountain 18, museum 10, **noble 0**, officeholder 21, organization 26.

  Fandom counts: chinese 1, film 2, historic site 6, holiday 14,
  kofun 3, mountain 17, museum 7, noble 55, officeholder 18,
  organization 25. (Fandom doesn't get the orchestrator
  canonicalization pass — it's a mirror; fandom side needs a
  separate canonicalization strategy.)
## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
