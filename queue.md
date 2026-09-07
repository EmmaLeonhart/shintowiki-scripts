# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today
＊ I have decided that instead of removing katakana, any improper name in kana things should have the katakana replaced with hiragana, although wait that might not work based on citations and qualifiers so look over the presence of them before making a decision


- **Weekly sweep: analyse [[Open questions]] into queue.md (<!-- weekly-oq-sweep --> 2026-09-07)**
  Auto-added by `.github/workflows/weekly-open-questions-sweep.yml`. Read `git_synced/Open questions.wiki` (the wiki version is authoritative — pull/confirm the live page, don't clobber Emma's edits). For every actionable item or Emma disposition not yet handled: either decompose it into concrete steps lower in this queue, or act on it now and prune the resolved bullet from the page. Then delete THIS block.

- [ ] Orphan descriptions: read the residue count on `orphan-label-fixes.html` after the next `generate-pages.yml` run (it now reports orphans with NO generated label separately). If the fixable set has gone to ~0, the rest is removal-or-rewrite — `audit_orphan_descriptions.py --emit` stages `orphan_description_removals.txt`.
  ⚠ Registering that file in `ATOMIC_FILES` puts it in the emergency batch. Blocks 2+ run after block 1 on the page, but `ALL.txt` is a random draw in run order, so a removal line can be drawn without its matching label line. Sequence it, or keep it out of the sample.

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
