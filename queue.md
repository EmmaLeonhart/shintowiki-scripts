# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- [ ] `generate_multilang_quickstatements.py` asks WDQS **two queries per language, 57 languages
  = 114 per run**, and each returns ~37,000 rows. It drew a 429 on 2026-09-21 (run 35682528723)
  at language 18, and it was already importing `wdqs_transport` — it was never one of the eight
  hand-rolled callers fixed on 09-20. **So the untried lever is asking FEWER questions, not pacing
  them better.** Both queries per language differ only by a per-language
  `FILTER NOT EXISTS { ?item rdfs:label ?x FILTER(LANG(?x)="<lang>") }` over the same fixed
  shrine/temple set.
  • ⚠ Not a speed optimisation, and must not be argued as one — this project is deliberately slow.
    It is load reduction, which CLAUDE.md demands outright: *"You don't fucking hammer it."*
  • ⚠ The rotation added 2026-09-21 spreads the COST of a bail across languages; it does not
    reduce the load that causes one. Both are wanted.
  • ⛔ Do NOT widen the per-language `except Exception` to catch the 429 `SystemExit`. A 429 bails
    by policy, and continuing to the next language is the hammering the policy exists to stop.
  • ⚠ Bounded first step: measure whether one query per language, or one query for the whole
    class set plus a single (item, language) label-existence pass, returns the same rows. If the
    row sets differ at all, stop and write down how — do not ship a query that changes the
    population.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-21**: `f9177ea8` :03, `77dc3fc6` :15, `12c63985` :42,
    `f6ded1e6` 08:03 — created after `CronList` reported, once again, no jobs at all beforehand.
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
