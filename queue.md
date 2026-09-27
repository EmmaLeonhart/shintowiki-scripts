# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- [ ] **Find out why the direct drip lands 0 edits on some days.** 09-24 and 09-26: every write
  failed ("The save has failed." / "You do not have the permissions needed"). 09-25: 497 landed.
  No block, rights change or filter hit on the account. The drip now logs the error `code` +
  `messages` (DEVLOG 2026-09-27). Read them from the next failing cleanup-loop run and fix the cause.

- [ ] **LATER, after the 0-edit-day fix: Engishiki list membership review.** Emma
  2026-09-27: the least important pipeline for its level of complexity. It's marginally good, but
  editing is too unreliable to verify it does anything productive. Her ruling, in order:
  1. Stop the REMOVALS (`list_membership_removals`, `orphan_membership_removals`,
     `multi_ordinal_removals`) and keep adding new memberships (`list_membership_rebuild`), if the
     adds can run without the removals.
  2. If they can't be separated: keep it all as it is.
  3. If it has made no edits lately: remove it altogether.
  Nothing downstream reads it (the katakana step's P361 hop is a sub-shrine's part-of its parent,
  and excludes list items). Check first: its recent landed edits, and whether orphan removals ↔
  rebuild loop (692 overlapping pairs, read from code, unverified).

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
    ✓ Live IDs, session of **2026-09-27**: `6e2ac79f` :03 (now monitors each wikidata-drip run first),
    `3ce10a86` :15, `da0748fb` :42, `bb1c79c5` 08:03 — created after `CronList` reported no jobs.
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
