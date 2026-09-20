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

- [ ] Religious buildings: emit `P825` (dedicated to) from the parsed dedication, not just labels
  (Emma, same day: *"using the dedicated to for other ontology not just labels"*). Must respect the
  `INVALID_HONZON` / designation-class rules already in CLAUDE.md.
  ✓ The QID half is DONE and validated — `saint_qids.py`, 48 terms, built 2026-09-19. Emma ruled the
  same day that the **QID identifies and the TABLE renders**, so this emits a statement and changes
  no label.
  ✓ The JOIN is measured and the seam exists: `match_dedication()` names which table entry a label
  matched (2026-09-19), which is what a statement needs. **2,153 of 8,080 table-path items reach a
  validated QID.**
  ⚠ The limit is the SEED, not the join. The commonest dedications have no QID at all — `holy
  trinity` 196, `martin` 163, `assunta` 106, `madonna` 105, `peter paul` 99, `notre dame` 97,
  `mariä himmelfahrt` 90, `christus` 89. Resolving those ~12 keys would roughly double the yield,
  and each needs the same `ALLOWED_CLASSES` validation — the 101-row seed was 52% wrong and a
  fresh lookup will be too.
  ⚠ Decide before writing the generator whether 2,153 ships on its own or waits for the top keys.
- [ ] Religious buildings: render BOTH dedications (Emma, same day). `Sint-Bartholomeus- en
  Barbarakerk`, `Saints Apostles Peter and Paul church in …`. Needs a join word per language and
  the Dutch hyphen-elision form.

<!-- Spent injector markers below. NOT queue items, and not a done-list:
     scheduled/inject_due_items.py re-injects any item whose marker is missing from this
     file, whatever its json records, so the marker has to outlive the work. Each one's
     outcome is in DEVLOG.md under its date. -->
<!-- scheduled:p361-duplicate-part-of-removals -->
<!-- scheduled:p958-corrections-batch-paste -->

