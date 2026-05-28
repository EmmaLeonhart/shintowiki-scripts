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

  **Separate fix needed:** the `miraheze_unique/` sync needs to run the
  canonicalization on local `.wiki` files BEFORE pushing — otherwise
  the sync's repo-wins overwrites any wiki-side canonicalization done
  by the orchestrator. Cleanest implementation: a one-shot script that
  walks all `miraheze_unique/*.wiki`, `fandom_unique/*.wiki`,
  `git_synced/*.wiki`, `need_translation/*.wiki`, `duplicated_content/*.wiki`
  and applies the same `canonicalize_template_case` regexes. Once the
  local files are canonical, the syncs stop reverting.

- [ ] **Then re-run `delete_lowercase_template_collisions.py --apply`**
  once the above investigation drains the surviving transclusions.
  Currently 20 of 20 templates still gated per the 2026-05-28 dry-run.
## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
