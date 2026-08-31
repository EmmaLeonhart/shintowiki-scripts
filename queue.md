# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

- **Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-08-31)**
  Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Started and verified via `CronList` in the session of **2026-08-30**: `7a2f68a3` :03,
    `7973144f` :15, `ec126e03` :42, `f7ed4ac5` 08:03. (The four IDs previously recorded here were
    the 2026-08-28 session's and had been dead for two days — a status report flagged them twice
    before anything removed them, which is the cost of leaving a spent record in a live file.)
  - [ ] Run the status-report action once more independently as an end-of-session summary.
