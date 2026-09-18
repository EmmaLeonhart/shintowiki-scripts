# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- [ ] `category_translation` is wiki-bound and is being treated as Wikidata-bound.
  Its RAG answers land in `category_moves.csv`, whose ONLY consumer is `move_categories.py` —
  lockout-gated, and it performs wiki page moves. The wiki is formally abandoned, so **328
  work-files, 18% of the drainer's queue, are picks that cannot land.** Emma's 2026-09-15 rule
  (*"forget about them"*) already covers this; `tests/test_remote_queue_skips_dead_wikis.py` lists
  it under `WIKIDATA_BOUND` because it *"writes rows to category_moves.csv"*, and a CSV row is not
  a Wikidata edit.
  - Needs Emma's word first: dropping it frees 18% of the daily picks for label/kana work, but
    stops accumulating answers that would be ready if the wiki ever returns.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-17**: `83b0a8e7` :03, `ce4a2a9e` :15, `c1304ac0` :42,
    `747bc950` 08:03 — created and re-verified with `CronList`. It again reported **no jobs at all**
    at the start of this session, as it has at the start of every session that has checked. Every
    recorded set this file has carried has been dead by the time the next session read it. Trust
    `CronList`, not this line.
    ⚠ `durable: true` does nothing — `CronCreate` says so in its own parameter description ("Has no
    effect — durable persistence is not available"). So the recreate-every-session step is the only
    mechanism there is, not a workaround for one that keeps failing.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
