# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- [ ] Fix the 3 failing Tests checks on the staged QuickStatements data (Emma, 2026-10-07):
  `test_derived_name_in_kana` (items both shipped and held), `test_descriptions_are_not_edited`
  (Q135040933/Q135040944 same Izumo description), `test_no_file_undoes_another` (a file pair staging
  one triple both ways). Fix the generators, never the tests; any dropped drip lines go to Emma first.
- [ ] Find out what the round 2 browser QuickStatements errors were (#289736: 62, #289739: 27, about
  1% against round 1's ~0.1%) and fix the generator if it is a pattern.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-27**: `6e2ac79f` :03 (now monitors each wikidata-drip run first),
    `3ce10a86` :15, `da0748fb` :42, `bb1c79c5` 08:03 — created after `CronList` reported no jobs.
    Session of 2026-10-03: `1c5e70e8` :03, `d0bb6e6c` :15, `d9244767` :42, `16cb87b1` 08:03.
    Session of 2026-10-06: `e454a83f` :03, `7ffa1e27` :15, `a6f16584` :42, `1e5163b0` 08:03.
    Every recorded set this file has carried has been dead by the time the next session read it.
    Trust `CronList`, not this line.
    ⚠ 2026-09-19: this session read "keep last" as "optional", did the queue work, and reported the
    crons as something to offer rather than doing them. It is not optional — a fresh session has
    none, so recreating the set IS the item, and the only reason it is pinned last is that a
    planning burst kills them.
    ⚠ `durable: true` does nothing — `CronCreate` says so in its own parameter description ("Has no
    effect — durable persistence is not available"). So the recreate-every-session step is the only
    mechanism there is, not a workaround for one that keeps failing.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.

<!-- Spent injector markers below. NOT queue items, and not a done-list:
     scheduled/inject_due_items.py re-injects any item whose marker is missing from this
     file, whatever its json records, so the marker has to outlive the work. Each one's
     outcome is in DEVLOG.md under its date. -->
<!-- scheduled:p361-duplicate-part-of-removals -->
<!-- scheduled:p958-corrections-batch-paste -->
<!-- scheduled:label-generator-continue-on-error -->
<!-- scheduled:label-generator-continue-on-error-campaign -->
