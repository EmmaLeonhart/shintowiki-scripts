# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

- [ ] **Move 建稲種命's Overview onto [[Takeinadane]], then redirect.** The English page has no
  Overview at all — only Genealogy / Notelist / References — while the source's is 1,923b. It is the
  one pair where the missing section is the article's whole opening.

- [ ] **Move 那須国造's Territory onto [[Nasu no Kuni no Miyatsuko]], then redirect.** The English
  page's `Headquarters` (952b) covers the source's `Base` (943b) and nothing else; the source's
  `Territory` (1,993b — Nasu Province, the Kenu-river boundary from the *Hitachi no Kuni Fudoki*,
  the absorption into Shimotsukenu) has no counterpart. Its `Base` and `Territory` are two real
  sections, which is why base and territory must stay separate concept classes.

- [ ] **Move 牟義都国造's Descendants onto [[Mukizu no Kuni no Miyatsuko]], then redirect.** 313b with
  nowhere to land — the English page stops at `Notable Figures`. Its `Tombs` is an empty wrapper and
  its `Clan Temple` (51b) is the English page's `Associated Temple`, so Descendants is the only real
  gap; add the pair to `PAIR_HEADINGS` for the temple heading in the same change.

- [ ] **Merge 尾張氏 into [[Owari clan]] section-wise, then redirect.** The only pair that is two
  genuinely different articles rather than two translations of one. The source's *"The Owari clan
  from the perspective of the Kinai regime"* (analysis) and *"Owari clan (Inaba Province)"* (a
  distinct branch) have no counterpart in the English page's History / Atsuta Shrine / Later history
  / Cultural influence. Both sections move across; neither script fits, so this is a hand edit.

- [ ] **Union-merge the three pairs where the Japanese page is fuller.** 健磐龍命 (19,798b vs
  13,510b), 建比良鳥命 (9,615b vs 8,387b), 神大根王 (5,710b vs 5,297b). `merge_duplicate_pairs.py`
  REPLACES the target body, and its 2.0x source gate correctly refuses all three — the sections are
  **complementary, not superset/subset**. 健磐龍命 is the clear case: the source holds Nihon Shoki,
  Fudoki, Engishiki and Kokuzo Hongi; the target holds the Kihachi legend and the U-no-matsuri
  festival, and a body-replacing merge would destroy those. What is needed is a section-wise union
  that keeps both sides, which is a third operation neither script performs — do not lower the 2.0x
  gate to reach these.

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
