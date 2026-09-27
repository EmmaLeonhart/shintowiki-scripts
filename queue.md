# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- [ ] **Run the Wikidata drip on every push to main.** Emma 2026-09-27: nobody objects to her
  editing any more, so the conflict/time gating is too aggressive. Any push to main should run the
  pipeline. Keep the random noise between edits and drop the strict time gating. Wiki-side steps
  and the QuickStatements attempt must not sit in front of the Wikidata edits. Plan: a lean
  workflow (generate → drip) on push, not cleanup-loop (which cancels in progress). Decide the
  daily total, the overlap rule and the conflict gate with Emma first.

- [ ] **CURRENT: analysis of the drip's pipelines, one at a time with Emma.** Explain how each
  generator works (not just its output), what reads its property, and how much is already landed.
  Kana and honorifics: kept. Founding dates: paused. Court rank + kami parents: moved to
  `handoff/court-rank-people/`. Weekly prune of landed lines: shipped (first run 36299480522).
  ⛔ **Not finished until the first prune run (36299480522) completes and its per-file counts are
  reviewed with Emma.** Until then no completion figure is final.

- [ ] **Find out why the direct drip lands 0 edits on some days.** 09-24 and 09-26: every write
  failed ("The save has failed." / "You do not have the permissions needed"). 09-25: 497 landed.
  No block, rights change or filter hit on the account. The drip now logs the error `code` +
  `messages` (DEVLOG 2026-09-27). Read them from the next failing cleanup-loop run and fix the cause.

- [ ] **Per-run drip tally: keep it over time.** Since 2026-09-27 each drip run prints a per-file
  landed / already there / failed / skipped table with the first failure reason, to the log and the
  run summary. Still missing: persisting it (the drip workflow commits nothing), so completion and
  bad days can be read across runs.

- [ ] **END OF QUEUE: sort out the wiki-link fetchers.** Emma 2026-09-27: `fetch_p6262_from_wiki.py` /
  `fetch_p11250_from_wiki.py` read their lines from shinto.miraheze.org pages, which CI can't reach.
  That's suspicious spaghetti, and it's unclear where these lines should come from; probably
  Wikidata, not the wiki. Work out what the fetchers actually do and what they should do. (On
  09-27 their line patterns were changed to refuse Category:/Template: pages.)

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
<!-- scheduled:label-generator-continue-on-error-campaign -->
