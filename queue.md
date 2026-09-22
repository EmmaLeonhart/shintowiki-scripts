# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- [ ] Watch whether `Generate shrines-missing-en-label list` stops 429ing. Its Stage 2 steps hand-
  rolled a WDQS transport at `THROTTLE = 0.5`, five times faster than the repo floor, and the
  workflow failed 5 of 6 runs from 09-16 to 09-20 — so `identical_name_en_labels.txt` and
  `temple_identical_name_en_labels.txt` have not regenerated since 09-17. Raised to the floor
  2026-09-20.
  ⛔ MEASURED 2026-09-20, by dispatching the workflow: the throttle change did **not** stop it.
  Run 35509769098 bailed again, and the log says why it was never going to:
      Stage 2 targets (no-kana, no-en): 4082 shrines, 3041 distinct ja labels.
      SPARQL 502 transient (attempt 1/3)
      FATAL: 429 Too Many Requests from SPARQL endpoint — bailing
  The retry path never consulted `THROTTLE` at all. It slept `10 * attempt` — ten seconds after a
  502 — where CLAUDE.md says *"503/504 → back off hard, do not retry tightly"* and the floor it
  names comes *"with exponential backoff (15/45/135s)"*. Now `_backoff()`, four attempts, imported
  from `wdqs_transport` so it cannot drift.
  ⚠ Also NOT known to fix it. Next measurement is the next run; the levers after this are a smaller
  `BATCH` than 150 labels per POST, or a slower throttle (the floor is a floor, a caller may be
  slower). ⚠ And a cost to watch: an exhausted backoff is now 195s per batch, not 30s, against a
  `timeout-minutes: 20` job that normally finishes in ~7m.
  ⚠ A sweep of every WDQS caller then found **eight** hand-rolled transports on the same tight
  retry, **two of them other steps of this same workflow** — `generate_shrines_missing_en_label.py`
  runs first in it and `generate_cjk_ja_backfill.py` last, so they share its endpoint budget and
  step 1 was hammering before Stage 2 ever ran. All eight now import `wdqs_transport.backoff`.
  That widens what the next run measures: it is no longer one generator's pacing.
  ⚠ Reading `gh run view --json jobs` for this is a trap: `continue-on-error: true` rewrites a
  step's **conclusion** to success while its **outcome** stays failure, so both Stage 2 steps read
  green there while the re-fail step correctly called them failed.
  ⚠ While it fails, those two files are frozen snapshots re-offering landed lines — which costs an
  API call each and changes nothing, so it is untidy rather than harmful.
  ⛔ MEASURED 2026-09-21, and it is NOT confined to this workflow. A dispatched
  `label-generator-regenerate.yml` (run 35682528723) drew a 429 too, in
  `generate_multilang_quickstatements.py` — which already imports `wdqs_transport` and was never
  one of the eight hand-rolled callers. It died at language 18 of 57, so **39 languages did not
  regenerate**, and two 502s before it (`de`, `it`) retried at 15s and recovered.
  So the shared transport is working as written and the endpoint is still refusing us. **The lever
  that has not been tried is issuing FEWER queries, not pacing them better** — 36 queries for 18
  languages, two per language, is the shape to attack before touching THROTTLE again.

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
