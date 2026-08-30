# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

The remaining duplicate-pair items are all the same operation now: add a `CARRIES` entry to
`shinto_miraheze/carry_missing_sections.py` naming the source sections and the target heading each
goes before, dispatch `carry-missing-sections.yml`, then dispatch `redirect-translated-duplicates.yml`
and let its own gates decide the redirect. Read both live pages before writing the entry — the byte
counts recorded below were carried, not measured, and 建稲種命's was wrong by 386b.

The carry tool now also carries a LEAD (`lead = {heading, anchor, append?}`). Use it: the
correspondence gate compares HEADINGS and never looks at a lead, so a source lead that outweighs the
target's passes the gate invisibly. Check the lead byte counts on every remaining pair before
redirecting, not just the headings.

- [ ] **建比良鳥命 is NOT a duplicate-translation pair — hand it to the translation pipeline.**
  Emma's call, 2026-08-30, asked with the measurements. Every other pair in this workstream was two
  ENGLISH translations, one sitting at a Japanese title. This source is raw untranslated Japanese:
  **2,169 CJK characters** of body prose, headings 概要 / 記述 / 系譜 / 祀る神社, nine
  `Pages with N+ untranslated japanese characters` categories and `[[Category:Need translation]]`,
  and no `{{translated page}}`. Both it and [[Takehi-Nateru]] are already in `need_translation/`.
  - **No carry and no redirect.** Carrying would put untranslated Japanese into a clean English
    article; redirecting would delete a page the translation pipeline is queued to work on.
  - The duplicate QID **Q11065428 stays open** for this one pair until the translation lands. That
    is the correct state, not an unfinished job — record it rather than re-deriving it next time.
  - The concrete next step is translation, which `need_translation/` and the remote-queue routine
    already own. Do not re-open it here.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running. Verified live via `CronList`, session of
    2026-08-28: work-loop `aeb3d7cb` :03, auto-flush `fa3787f8` :15, status-report `8f65f73a` :42,
    briefing `25b7500a` 08:03. Crons are session-local, so a recorded ID is only ever evidence
    about the session that made it.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* It was created earlier the same session, fired once, and she killed it on
    the first prompt. Do not recreate it from any doc that still says five.
    ⚠ This session ran with only THREE for ~24 ticks — the briefing and debrief gates were never
    created, despite the hub's CLAUDE.md carrying a standing "Session start" instruction to
    establish them. Nothing was lost (no 08:03 or 23:57 elapsed while a session was live), but the
    check is worth doing EARLY rather than on whatever tick happens to re-read this file.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
