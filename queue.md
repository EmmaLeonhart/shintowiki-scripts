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


## Monthly delete-orphaned-pages script (first run 2026-06-01) (2026-05-27)

- [ ] **Build `delete_orphans.py` standalone script + monthly workflow,
  first run 2026-06-01.** Emma 2026-05-27: "it wouldn't be an
  orchestrator. It would just be a regular thing that would delete all
  orphaned pages. We can have it so that it runs every month on the
  first." We have `delete_orphaned_talk_pages.py` already (talk pages
  with no subject) — this new script handles the OTHER orphan
  definition: subject-side pages.
  - **Script** `shinto_miraheze/delete_orphans.py`: walks
    `Special:LonelyPages` via `list=querypage&qppage=LonelyPages`,
    deletes each member via `site.api("delete", title=..., reason=...,
    token=...)`. Standard CLI: `--apply`, `--max-deletes`, `--run-tag`.
    Throttle 2.5 s between deletes. mwclient + `WIKI_USERNAME` /
    `WIKI_PASSWORD` env vars. Pattern: mirror
    `delete_orphaned_talk_pages.py`.
  - **Workflow** `.github/workflows/delete-orphans.yml`:
    `workflow_dispatch` + `schedule: - cron: "7 5 1 * *"` (07:05 UTC
    on the 1st of every month — off-:00 minute per CLAUDE.md cron
    guidance). First fire: 2026-06-01 05:07 UTC. Not wired into
    cleanup-loop — its own monthly schedule.
  - **Definition (needs Emma's call):** what counts as "orphaned"?
    Default: members of `Special:LonelyPages` (zero incoming
    wikilinks). Tighter alternatives if she wants more conservatism:
    (a) LonelyPages AND not in any category; (b) LonelyPages AND
    not transcluded; (c) LonelyPages AND older than N days.
  - **Safeguards:** never delete Main Page; respect a
    `[[Category:Do not delete]]` opt-out (skip any page tagged); skip
    redirects (Special:LonelyPages already filters those but
    double-check).
  - **Per-run cap:** ~50 deletes default — bounds wall-clock and bot
    edit volume on miraheze.
  - **Verification path:** dry-run default; log every candidate with
    its (skipped vs deleted) reason; on `--apply`, post a run summary
    to a tracking wiki page so deletions are auditable.

## Refactor configure-wikidata-link-grok-categories to be repo-side (2026-05-27)

- [ ] **Rewrite `configure_wikidata_link_grok_categories.py` to edit the
  REPO file, not the live wiki.** Current shape: workflow runs script,
  script logs into miraheze via mwclient, script edits
  `Template:Wikidata link` on the wiki directly. Problem: that template
  is in `[[Category:Independently git synced pages]]` which is
  repo-wins for conflicts, so any wiki-side edit gets clobbered by the
  next `sync_miraheze_unique_pages.py` run. The repo file
  `miraheze_unique/Template%3AWikidata link.wiki` is the source of
  truth. Correct shape: script edits the repo file (replace-or-append
  the GROK_BLOCK using the existing `_replace_or_append` helper),
  commits with a `[skip ci]`-able message, pushes, and lets the next
  sync cycle propagate to the wiki. Also: drop the workflow's wiki
  authentication step entirely — no `WIKI_USERNAME` / `WIKI_PASSWORD`
  needed. Today's emergency fix (commit `bd4b937d`) brought the repo
  + wiki into sync manually; this refactor closes the window where the
  shape itself was wrong.

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
