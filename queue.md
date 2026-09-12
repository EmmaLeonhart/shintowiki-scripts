# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Fill `{{wikidata link}}` on the 58 named pages that have no interwiki pairs to resolve from.**
  Promoted from `todo.md` 2026-09-12 (Emma's Shizensha item). Measured, so the numbers below are the
  wiki's, not an estimate: `shinto_miraheze/report_blank_wikidata_links.py`, whole of ns 0.
  - The ADD half is built and 95% done: **10,521 of 11,069** non-redirect mainspace pages carry a
    filled `{{wikidata link|Q…}}`. **233 blank**, **315 with no template at all**.
  - The gap is real but small: of the 233 blank, **170 are Q-titled stubs** (the QID is the title,
    and `dedupe_duplicate_qids` is going to redirect them into the real-named page, so they are not
    worth filling), 5 are lists/dabs, and **58 are named pages like `Shizensha`** — the ones
    `wikidata_lookup` can never reach, because it resolves only from the template's own
    (lang, target) pairs and these have none.
  - [ ] Resolve those 58. ⛔ NOT with a per-page `wbsearchentities`/SPARQL sweep — CLAUDE.md forbids
    exactly that shape. 58 is small enough to resolve from a source we already hold, or by hand.
  - The 315 with no template are a separate and mostly-not-ours population: 57 Q-titled, and much of
    the rest are language-prefixed mainspace titles (`Az:Bəşəriyyət`, `Ba:Category:…`, `Ast:Torre`)
    plus `Main Page`. Weird is signal here — do not point an op at them without asking.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-11**: `14f69b80` :03, `0bc8be25` :15, `e63f99f1` :42,
    `d553fe57` 08:03, created and verified via `CronList` this session. The four listed before these
    were the 2026-08-31 session's and were dead on arrival — the fourth such stale set this file has
    carried. Trust `CronList`, not this line.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
