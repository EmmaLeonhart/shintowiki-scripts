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
    ✓ Live IDs, session of **2026-09-17**: `83b0a8e7` :03, `ce4a2a9e` :15, `c1304ac0` :42,
    `747bc950` 08:03 — created and re-verified with `CronList`. It again reported **no jobs at all**
    at the start of this session, as it has at the start of every session that has checked. Every
    recorded set this file has carried has been dead by the time the next session read it. Trust
    `CronList`, not this line.
    ⚠ `durable: true` does nothing — `CronCreate` says so in its own parameter description ("Has no
    effect — durable persistence is not available"). So the recreate-every-session step is the only
    mechanism there is, not a workaround for one that keeps failing.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.

- [ ] ⚠ The religious-building items below are the **10%** (Emma, 2026-09-18: *"90% Shinto
  10% others. Japanese Buddhist temples are Shinto"*). Shrine and temple work comes first.
- [ ] Religious buildings: drop the `is_latin_script()` gate in stage 1 and transliterate
  Arabic/Hebrew/Devanagari names. ⚠ MY CALL, not hers — she did not answer the question. It follows
  from the two rulings she did give (no dedication means transliteration; non-Japanese temples are in
  scope, and a mandir's name is Devanagari). Reverse it if wrong. Today the gate is why there are no
  Arab-world mosques and no Hebrew-named synagogues at all: not refused downstream, never selected.
- [ ] Religious buildings: no dedication means TRANSLITERATE (Emma, 2026-09-18, *"No dedication
  means transliteration"*). 13,696 of 22,548 are refused at that gate — `Dorfkirche Jördenstorf`,
  `Église du Pras de La Mulatière`, `Santo André de Lourizán`. `romance_katakana` already exists
  and is already wired for country rules; it is the starting point, not a new build.
- [ ] Religious buildings: emit `P825` (dedicated to) from the parsed dedication, not just labels
  (Emma, same day: *"using the dedicated to for other ontology not just labels"*). The morpheme
  table already resolves a dedication to a saint; nothing turns it into a statement. Must respect
  the `INVALID_HONZON` / designation-class rules already in CLAUDE.md.
- [ ] Religious buildings: the saint reading comes from WIKIDATA's label on the resolved QID, not
  from my table (Emma, same day). Table becomes a QID map; `paused/table_audit.tsv`'s 101 rows are
  the seed. Drop rows whose term resolved to a non-religious-figure — `All Saints` → `Q165386` is
  a girl group.
- [ ] Religious buildings: render BOTH dedications (Emma, same day). `Sint-Bartholomeus- en
  Barbarakerk`, `Saints Apostles Peter and Paul church in …`. Needs a join word per language and
  the Dutch hyphen-elision form.

<!-- Spent injector markers below. NOT queue items, and not a done-list:
     scheduled/inject_due_items.py re-injects any item whose marker is missing from this
     file, whatever its json records, so the marker has to outlive the work. Each one's
     outcome is in DEVLOG.md under its date. -->
<!-- scheduled:p361-duplicate-part-of-removals -->
<!-- scheduled:p958-corrections-batch-paste -->

