# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Indonesian labels are derived by pykakasi from the KANJI, not from the English label.**
  Emma 2026-09-10: *"the Indonesian labels often appear quite dubious and I'm not sure how they were
  derived. They should be derived from the proposed English labels for the shrines."*
  `shinto-label-generator/generate_indonesian_proposals.py` fetches `?enLabel` and uses it only in a
  `# Source:` comment; the label itself is `pykakasi(kana or ja_label)` with macrons stripped and
  `uu/ou/aa/ii/ee` blanket-collapsed. 元八幡 / "Moto Hachiman" ships as `Kuil Genpachi Hata`; 陶山神社 /
  "Tōzan Shrine" ships twice, as `Kuil Sueyamajinja` AND `Kuil Tozanjinja`. Rebuild it to take the
  English label — existing on Wikidata, else the proposal from our own en-label files — strip the
  English shrine/temple word, and emit `Kuil {stem}` / `Wihara {stem}`. Emit NOTHING where no English
  label exists rather than guessing from kanji. 44,058 current proposals; measure the coverage drop.

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
