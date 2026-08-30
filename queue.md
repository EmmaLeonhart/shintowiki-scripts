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

- [ ] **Union-merge the two pairs left where the Japanese page is fuller.** 建比良鳥命 (9,615b vs
  8,387b) and 神大根王 (5,710b vs 5,297b). `merge_duplicate_pairs.py` REPLACES the target body and
  its 2.0x gate refuses both correctly — the sections are **complementary, not superset/subset** —
  so use `carry_missing_sections.py`, and do not lower that gate. The redirect script's 1.0x gate
  will keep refusing each until the carry has made the target the larger page; that is the correct
  order, not a failure.
  - **健磐龍命 is DONE** (2026-08-30, 13,510b → 31,572b, 0 cite errors, redirected at 1.59x) and it
    is the template for these two. What it needed beyond the sections: its LEAD, a `ref_defs` block
    for eight named refs whose definitions lived in the apparatus and the infobox, a RENAME of its
    bibliography (both pages called it `References`), and a `PAIR_HEADINGS` entry for the five
    subsections named after the texts they summarise.
  - **⭐ PREVIEW THE MERGED TEXT THROUGH `action=parse` BEFORE SAVING.** On 健磐龍命 the wikitext
    check said the page was clean and the renderer reported **30 cite errors**, three of them on the
    target's own refs. The remaining one after that was a definition landing inside a
    `{{Refnest|group="note"}}`, invisible to main-group uses. Neither was findable from the wikitext.
  - 建比良鳥命 is the odd one: its TARGET lead is 4,655b against the source's 1,165b, the reverse of
    every other pair. Read both before assuming the lead needs carrying.

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
