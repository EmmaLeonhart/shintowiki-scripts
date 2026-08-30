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

- [ ] **Merge 尾張氏 into [[Owari clan]] section-wise, then redirect.** The only pair that is two
  genuinely different articles rather than two translations of one. The source's *"The Owari clan
  from the perspective of the Kinai regime"* (analysis) and *"Owari clan (Inaba Province)"* (a
  distinct branch) have no counterpart in the English page's History / Atsuta Shrine / Later history
  / Cultural influence. Both sections move across as one `CARRIES` entry with two section pairs.

- [ ] **Union-merge the three pairs where the Japanese page is fuller.** 健磐龍命 (19,798b vs
  13,510b), 建比良鳥命 (9,615b vs 8,387b), 神大根王 (5,710b vs 5,297b). `merge_duplicate_pairs.py`
  REPLACES the target body, and its 2.0x source gate correctly refuses all three — the sections are
  **complementary, not superset/subset**. 健磐龍命 is the clear case: the source holds Nihon Shoki,
  Fudoki, Engishiki and Kokuzo Hongi; the target holds the Kihachi legend and the U-no-matsuri
  festival, and a body-replacing merge would destroy those. The section-wise union they need now
  exists (`carry_missing_sections.py`) — do not lower the 2.0x gate to reach these. Note the
  redirect script's 1.0x gate will still refuse each one until the carry has made the target the
  larger page, which is the correct order and not a failure.

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
