# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

- **Pinned tail (keep last)**

  - [ ] Ensure the five session-local crons are running. Verified live via `CronList`, session of
    2026-08-27: work-loop `0bcfcd0c` :03, auto-flush `fa3787f8` :15, status-report `8f65f73a` :42,
    briefing `25b7500a` 08:03, debrief `23235e0d` 23:57. Crons are session-local, so a recorded ID
    is only ever evidence about the session that made it.
    ⚠ This session ran with only THREE for ~24 ticks — the briefing and debrief gates were never
    created, despite the hub's CLAUDE.md carrying a standing "Session start" instruction to
    establish them. Nothing was lost (no 08:03 or 23:57 elapsed while a session was live), but the
    check is worth doing EARLY rather than on whatever tick happens to re-read this file.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
