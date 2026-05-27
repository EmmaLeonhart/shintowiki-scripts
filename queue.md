# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. Do not add summary sections, progress checkmarks, or status indicators — if an item is still here, it is not done.

The purpose of this file is to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup, shrine-disambig content strip) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.


## Duplicated-content pipeline — remaining follow-ups (2026-05-23)

Big fixes shipped this session (see DEVLOG 2026-05-23): consumer instruction
rewritten (macro paragraph-merge, NOT param dedup), sync conflict policy set to
**wiki-wins** for duplicated_content + need_translation, queue builder now
shuffles + only queues files that still carry the category, 134 dup pages
re-pulled from the wiki, cursor reset. Still open:

- [ ] **The cloud consumer still uses a cursor.** The claude.ai scheduled
  routine walks `consume_remote_queue.state` through `remote_queue.json`. Emma
  wants statefulness to be purely file-presence + category (no cursor): each run
  should scan `duplicated_content/` for files still tagged
  `[[Category:Pages with duplicated content]]` and pick at RANDOM. The routine's
  PROMPT defines this — it can't be edited from the repo. Reword the routine
  (via claude.ai schedules) to drop the cursor and pick category-tagged files at
  random. (Repo-side mitigations already in place: `remote_queue.py` shuffles +
  category-filters, cursor reset to 0.)
## Wikidata: カミノヤシロ kana — manual stragglers (bot request 2026-02-26)

Both bot jobs shipped (see DEVLOG 2026-05-23). The "18 leftovers" earlier were a
false alarm: part 2 now defers to part 1 whenever the ojp-hani P1448 already has
a katakana qualifier (part 1 appends カミノヤシロ to it; the top-level modern
hiragana reading is normal and left alone). Emma fixed the original 3
ambiguous items by hand on the wiki. Only genuinely-manual cases remain:

- [ ] **Items with 0 or >1 ojp-hani P1448 official name** (rare; surface in the
  `seed_kana_qualifier.py --dry-run` "AMBIGUOUS" report, e.g. Q135040786
  with no ojp-hani name). Emma handles these directly on the wiki as they appear
  — no bot action.


## Bot ping-pong / never-settling pages (2026-05-26)

- [ ] **Optional follow-up (strict-literal reading): move Translation Sync +
  Duplicated Content Sync to BEFORE the wiki-write steps inside
  `wiki-cleanup.yml`.** The 2026-05-26 fix moved `git-synced-sync` +
  `fandom-sync` to before the `cleanup` job in `cleanup-loop.yml`, which
  resolves the specific git_synced page-churn Emma flagged. The literal
  reading of "all sync_* steps" also includes the
  `sync_need_translation` and `sync_duplicated_content` steps sequenced
  partway through `wiki-cleanup.yml` itself. Whether those need reordering
  is unclear — those syncs touch `need_translation/` and
  `duplicated_content/` (specific directories the orchestrators don't
  edit), so the churn risk is different. Decide whether to move them
  before doing the larger YAML reshuffle.
- [ ] **Make sync conflict-resolution revision-aware (not static policy).**
  Currently per `feedback_sync_conflict_policy.md`: wiki-wins for
  duplicated_content/need_translation, repo-wins for
  git_synced/fandom_unique/miraheze_unique. Emma's stated rule: whichever
  side is further ahead in revisions wins, with per-directory tie-break
  rules (TBD). See todo.md "Bot ping-pong" for the full theory.
- [ ] **Diagnose and fix the page-churn loops Emma flagged.** Some pages are
  being edited in rapid succession by two competing processes ("the git sync
  and the other thing") and never settle — each bot's edit gets reverted by
  the other. **Don't guess at the fix; diagnose first.** First step: pull
  recent page history for a sample of affected pages from
  shinto.miraheze.org, find pages where two bot accounts (or the same bot
  via two different scripts/ops) are alternating, group by the
  script/op pair driving the loop. THEN decide which side's view of the
  canonical form is correct and align the other to it. See the matching
  todo.md "Bot ping-pong" section for likely suspects (git_synced sync vs.
  orchestrator ops, two orchestrator ops disagreeing, etc.). High priority —
  these pages are net churn for zero progress.

## Pinned notes

1. **`[[Category:Need translation]]` removal is destructive.** The sync in `shinto_miraheze/sync_need_translation.py` (run by `.github/workflows/wiki-cleanup.yml`) DELETES the file from `need_translation/` when the wiki page loses the category. Never bulk-strip based on filename heuristics. Verify the actual body (CJK outside `{{ill}}`/`{{jalink}}`/`{{nihongo}}` template params).
2. **Script-template invariants.** All scripts must support `--apply`, `--max-edits`, `--run-tag` flags; use `mwclient`; apply `time.sleep(THROTTLE)` with `THROTTLE = 2.5` between edits (bumped from 1.5 on 2026-04-18 for server load); set `User-Agent`; `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`; state file alongside the script. See `check_wikidata_labels.py` as a reference implementation. Do not innovate on this scaffolding.
3. **429 policy.** Wikidata/SPARQL scripts bail immediately on HTTP 429 — no retries.
