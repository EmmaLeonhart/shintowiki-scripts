# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **The general case: proper kana for every shrine, derived, not read.**
  Emma 2026-09-09: *"Realistically, all of the shrines should have proper Kana names derived from
  the Japanese put in them."* Existing pieces to connect rather than rebuild:
  `shinto-label-generator/translit_common.py`, `modern-quickstatements/kana_english.py`,
  `shinto_miraheze/build_name_in_kana_queue.py`. Note the builder's own rule excludes en-labelled
  items from its LLM queue — that exclusion is about *reading* an article, not about *deriving*
  from the label, so it does not block this.

- **Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-09-07)**
  Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-08-31**: `b4aa17da` :03, `6e16d378` :15, `967f61ee` :42,
    `38b1693a` 08:03, verified via `CronList`. The `:15` changed ID mid-session (`8ba189b9` →
    `6e16d378`) because its prompt still carried a rule Emma revoked that day. **The four listed
    before these were the 2026-08-30 session's and were dead** — the third such stale set in this
    file, which is exactly the cost the previous note described and then repeated. Trust `CronList`,
    not this line.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
