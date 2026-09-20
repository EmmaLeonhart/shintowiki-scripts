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

- [ ] ⚠ The religious-building items below are the **10%** (Emma, 2026-09-18: *"90% Shinto
  10% others. Japanese Buddhist temples are Shinto"*). Shrine and temple work comes first.
- [ ] Religious buildings, native-language tail: the **Nordic three — sv 84, no 21, da 14**.
  Emma 2026-09-20, asked which of nl/sv/no/da to build: ***"All four — nl, sv, no, da"***. Dutch
  shipped that day; these are the rest of the same answer, not a reduced version of it, and they
  are one per tick because this population is the 10%.
  The analysis is already done, so start from it rather than re-measuring:
  • **Letter inventories** (native-shaped labels only): sv = ASCII + ä å ö; no = ASCII + å æ ø;
    da = ASCII + æ é ø.
  • **The type word is the corpus.** `kyrk` is in 68 of the 84 Swedish, `kirke` in 9 of 21
    Norwegian and 8 of 14 Danish — so split the type word off as a morpheme boundary FIRST, the
    way the Dutch family splits `kerk`, and apply phonology to each element.
  • ⛔ **The Swedish `sky` trap, measured.** 17 labels have `sk` before a front vowel. **16 are
    `sky`, and every one of them is a compound `…s` + `kyrka`** — Brukskyrkan, Högåskyrkan,
    Korskyrkan, Betlehemskyrkan. Reading that as the /ɧ/ of `sk`+front swallows the linking s
    and gives ブルーシュルカン for ブルークスシュルカン. The other two are `skä` — `Rönnskärs`,
    `Skänninge` — and those ARE genuinely /ɧ/. Splitting the type word first resolves all 17
    without a special case.
  • Swedish still wants k/g palatalisation before e i y ä ö, and `sj`/`skj`/`stj`/`tj`/`kj`.
  • ⚠ **Danish is the least transparent of the four** and is last for that reason: soft `d`,
    soft `g`, the reduced `-er`/`-en` endings. 14 items, so it can afford an explicit pass over
    the hard parts the way `_pre_french` does rather than a letter-wise table.

- [ ] Religious buildings, the 627 ENGLISH-shaped long-tail labels. Emma 2026-09-20:
  ***"Translate, transliterate the place"*** — dedication and type word through the existing
  morpheme tables, and the placename transliterated **from its own language**.
  These are labels like `Saint Demetrius of Thessaloniki church in Botnărești, Anenii Noi` and
  `Archangels' church in Veza`: an English dedication + an English type word + a local placename.
  Measured 2026-09-20 — Moldova 249/249 English, Hungary 21/21, Lithuania 37/38, Romania 110/115,
  Armenia 48/51, Latvia 17/18, Bulgaria 16/18, Finland 29/36.
  • So the new families here exist **to carry placenames only** — ro, hy, lt, hu, bg, lv. The
    dedication and the type word already have tables.
  • ⛔ Do NOT transliterate these as if the whole label were the local language. It is English;
    only the place is not.
  • ⚠ All 1,119 long-tail items render to nothing today, in ja, zh and ko alike — checked by
    calling `render()` directly. There is no partial output to preserve.
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

