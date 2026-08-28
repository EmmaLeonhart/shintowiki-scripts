# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

- [ ] **Decide the 16 held duplicate pairs.** `redirect_translated_duplicates.py --plan-only`
  prints them live with their reason; the 17 mechanical ones are done. These need a judgement
  the script correctly refuses to make, in three groups:

  - **The English page is genuinely missing a section** the Japanese one has — 上毛野国造
    (genealogy), 伊勢国造 (墓), 建稲種命 (no Overview at all, despite being 1.04x by bytes),
    那須国造 (territory), and 島津国造 / 明石国造 / 熊野国造 (base). Either the section moves
    across first and then the pair redirects, or the pair is a merge.
  - **The Japanese page is the fuller one** — 健磐龍命 (19,798b vs 13,510b, holding Nihon Shoki,
    Fudoki, Engishiki and Kokuzo Hongi sections the English page has none of), 建比良鳥命 (still
    carrying raw jawiki headings), 神大根王 (0.93x, near-parallel). These are `merge_duplicate_pairs`
    shape, not redirect shape — but all three are under its 2.0x source gate, so neither script
    will touch them as they stand.
  - **A page-specific heading no map should be guessing at** — 闘鶏大山主 ("The Ice House of Tsuge"
    vs "The Himuro of Tsuge"), 針間鴨国造 (*Kitadera Chishiki-kyō* vs "Kitadera Knowledge Sutra"),
    紀伊国造 ("Generations of…" vs "Lineage of…"), 天道根命, 牟義都国造 ("Clan Temple"), and
    尾張氏, which is two genuinely different articles — the Japanese one has an Inaba-Province
    section with no counterpart. The first five look like straightforward translation variants on
    inspection; adding each to `CLASSES` is overfitting a general map to single pages, so the
    honest fix is per-pair.

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
