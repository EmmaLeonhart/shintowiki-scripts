# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

- **Pinned tail (keep last)**

  - [ ] Ensure the five session-local crons are running. Verified live, this session: work-loop
    `0a52da5c` :03, auto-flush `aa735a3c` :15, status-report `f371ceee` :42, briefing `ff8886e6`
    08:03, debrief `924d2b08` 23:57. Crons are session-local, so a recorded ID is only ever evidence
    about the session that made it.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
