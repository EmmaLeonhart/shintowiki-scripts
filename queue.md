# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-19**: `2951de5d` :03, `172cd60d` :15, `cc2f00d1` :42,
    `bd6c1736` 08:03 — created and re-verified with `CronList`, which again reported **no jobs at
    all** beforehand, as it has at the start of every session that has checked. Every recorded set
    this file has carried has been dead by the time the next session read it. Trust `CronList`, not
    this line.
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

- [ ] Watch whether `Generate shrines-missing-en-label list` stops 429ing. Its Stage 2 steps hand-
  rolled a WDQS transport at `THROTTLE = 0.5`, five times faster than the repo floor, and the
  workflow failed 5 of 6 runs from 09-16 to 09-20 — so `identical_name_en_labels.txt` and
  `temple_identical_name_en_labels.txt` have not regenerated since 09-17. Raised to the floor
  2026-09-20.
  ⚠ This is NOT known to fix it. The endpoint's limit is not published and the same workflow makes
  other WDQS calls in the window. If the next runs still 429, the levers are a slower throttle (the
  transport lets a caller be slower, never faster) or a smaller `BATCH` than 150 labels per POST.
  ⚠ While it fails, those two files are frozen snapshots re-offering landed lines — which costs an
  API call each and changes nothing, so it is untidy rather than harmful.

- [ ] ⚠ The religious-building items below are the **10%** (Emma, 2026-09-18: *"90% Shinto
  10% others. Japanese Buddhist temples are Shinto"*). Shrine and temple work comes first.
- [ ] Religious buildings: the long tail after the five families — Netherlands 258, Moldova 140,
  Sweden 83, Romania 81, Armenia 44, Finland, Norway, Lithuania. Dutch and Romanian are regular
  enough to read; the Nordic ones and Armenian-in-romanisation are not obviously so. Same
  `plain_latin_katakana` treatment or a documented refusal — ASK before building, under the
  religious-building translation carve-out, rather than inferring from the "all of them" answer,
  which was about a country map that no longer has these at the top of it.
  ⚠ The German block is MEASURED and closed: of 909, 790 named nothing (664 now reach the
  denomination/setting slot, 113 are a bare type word and stay refused), 40 are addresses with
  digits, 25 English wording, 13 punctuation (fixed), 11 French/Italian labels in a German-speaking
  country. Nothing there wants a new family. ⚠ Those 11 are the one loose thread: Switzerland is
  multilingual and `COUNTRY_RULES` is one family per country, so a French label in Q39 gets German
  rules and is correctly refused rather than mis-read. 5 items; not worth a per-item language guess.

- [ ] Religious buildings: the fourth dedication-QID lookup round. 73 concepts, 1,845 slots left.
  `resolve_dedication_qids.py` prints the worklist and filters anything already rejected by review.
  ⚠ Three groups, and they want different things:
  • **No P31 at all** — `聖十字架` 260, `十字架挙栄` 97. The class filter cannot clear them and no
    query changes that. Leave refused unless the items gain a class upstream.
  • **Genuinely ambiguous** — `ヨハネ` 123 (Evangelist vs John of Patmos), `平和` 58. Two survivors
    each; the label does not say which.
  • **`諸聖人` 56** — the only candidate a search finds is the SWEDISH All Saints' Day, already in
    `REJECTED_BY_REVIEW`. It needs the general item, which has not been found; `Q18378` is an
    Italian comune.
  ⚠ Also unresolved and worth a round: the `X of PLACE` phrases — `antonio padova` 22+6+3,
  `francesco assisi` 13+2, `john nepomuk` 10+8, `demetrius thessaloniki` 3. Each is ONE saint and
  needs the phrase's own QID; ⛔ do NOT resolve them from their first part, which would be right by
  luck today and silently wrong if that name ever resolves to a different saint of the same name.

<!-- Spent injector markers below. NOT queue items, and not a done-list:
     scheduled/inject_due_items.py re-injects any item whose marker is missing from this
     file, whatever its json records, so the marker has to outlive the work. Each one's
     outcome is in DEVLOG.md under its date. -->
<!-- scheduled:p361-duplicate-part-of-removals -->
<!-- scheduled:p958-corrections-batch-paste -->

