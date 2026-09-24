# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

<!-- scheduled:label-generator-continue-on-error-campaign -->
- [ ] **Campaign: fix the label-generator `continue-on-error` blindness.** Emma, 2026-09-21,
  offered drop / keep / keep+re-fail and picked none of them: ***"We run a campaign to fix it
  on Thursday."*** So this is not "apply one of the three options" -- it is the whole
  blindness, across every workflow that has it.
  • **The failure being fixed:** `label-generator-regenerate.yml` reported **success** for two
    days in Aug 2026 while all of its pipeline steps died on their first line. The only visible
    traces were job time falling **12m24s to ~55s** and the diff shrinking to a one-line date
    stamp, which reads as "nothing needed regenerating".
  • **It is 8 steps now, not the five the old note says** -- tokipona, korean, chinese,
    indonesian, multilang, religious-building multilang, stage-1 en replacements, docs HTML.
  • ⛔ **The reporting trap, and it is the same one the missing-en-label item hit:**
    `continue-on-error: true` rewrites a step's **conclusion** to success while its **outcome**
    stays failure, so `gh run view --json jobs` reads green on a step that died. Any check
    written for this must read `outcome`, not `conclusion`.
  • **The pattern already exists in this repo** -- `generate-shrines-missing-en-label.yml:147`
    keeps per-step isolation and then re-fails the run from the collected `outcome`s. That is
    the shape to generalise, not to reinvent per workflow.
  • **So sweep, do not patch one file:** `git grep -ln 'continue-on-error' .github/workflows/`
    and decide each one, because a workflow with tolerant steps and no re-fail step is the
    silent-failure shape wherever it appears.
  • ⚠ `strip_husk_lines.py` is the counter-example to preserve: *"deliberately not
    continue-on-error"*. A step whose failure must stay red is not a gap to fill in.
  • **Evidence to start from, and it is not hypothetical:** the 2026-09-21 20:16 cron ran it
    (**run 35682528723**) and caught the blindness live — `Run multilang pipeline` exited 1 on a
    WDQS 429, **17 of 57 languages regenerated and 39 never ran**, and the run, every step's
    conclusion, `--log-failed` and the commit diff all read clean. Full writeup in `DEVLOG.md`
    under 2026-09-21 (cont.). Read it before touching anything.
  • ⛔ **One third of the question is already answered:** the API does not expose `outcome` at
    all, only `conclusion`. An external/after-the-fact checker is not buildable, so the re-fail
    step is the only thing that restores the signal without dropping `continue-on-error`.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-23**: `420f4ec3` :03, `ebc63cff` :15, `a5c98015` :42,
    `0b4acc3b` 08:03 — created after `CronList` reported no jobs at all beforehand.
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
