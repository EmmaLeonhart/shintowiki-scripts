# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Miraheze: waiting for Cloudflare to stop challenging our runners. Nothing is owed by anyone.**
  Diagnosed 2026-09-12 (`shinto_miraheze/probe_miraheze_403.py`, `DEVLOG.md`): Cloudflare serves the
  GitHub Actions runners a managed challenge — 272 KB of `text/html`, *"Checking your connection…"* —
  on every request, reads included, while the identical script from Emma's connection gets 200. The
  control settles that it is not our UA: a deliberately generic UA from the same runner still gets
  Miraheze's own 193-byte `text/plain` policy refusal.
  - **Intermittent, not permanent.** `EmmaBot/3.1` passed from CI on 08-19, 08-23 and 08-30 and
    carried ~800 edits/day on 09-01..09-04. It began between 09-04 and 09-06.
  - **Probed DAILY since 2026-09-12** (Emma: *"Daily"*), `LOCK_DAYS` 8 → 2, so the day it lifts we
    know within 24 hours instead of up to eight days. The failure reason now records which 403 it is.
  - ⛔ **Emma has ruled out contacting Miraheze** (2026-09-12). Do not propose it again, and do not
    re-probe by hand — the daily test is the probe. There is nothing to decide and nothing to do;
    this item exists so the next session does not re-derive it.
  - ⚠ It also reframes `docs/fandom_vs_miraheze_2026-09-12.md`: that reliability table compares one
    host that challenges our runners against one that does not, which is not a comparison of the two
    wikis.

- [ ] WDQS transports: **69 callers, each hand-rolled.** All 8 that had a retry loop catching only
  `ReadTimeout`/`ConnectionError` are now covered (2026-09-14). What is left is the rest, and it is
  per-file reading.

  ⛔ **DO NOT PUT A NUMBER ON HOW MANY ARE FRAGILE.** Three regexes gave three wrong answers:
  *"65 of 72"* missed every `except Exception` and `except (ValueError, KeyError)`, which already
  catch a JSON error; *"50"* counted a file fixed hours earlier whose clause puts the tuple in a
  variable; *"~41 with no retry loop"* matched only `for attempt in range` and missed the
  `for wait in (0, 15, 45, 135)` shape. Grounded, by reading: **34 have some retry construct, 35
  have none, 10 already use the 15/45/135 backoff.**

  ⚠ **Migration is NOT uniformly an upgrade.** Those 10 escalate harder than a flat backoff, and
  no two unmigrated transports share a body. The failure costs one day of one file — CI is
  `continue-on-error` and the next run repairs it — so this rides with each file's next real change.
  `modern-quickstatements/wdqs_transport.py` is the target, and it now carries the repo's 15/45/135
  so adopting it cannot downgrade anyone.

  Adopters: 11. The first three joined on the tick of their own reference fix — the intended
  cadence. `generate_court_rank_quickstatements.py` had **0.5s** spacing (the exact figure CLAUDE.md
  cites from the incident that set the 2.5s floor) and a 5/10/15 backoff; the saijin and honzon
  generators each had no retry, no throttle, and a 429 check placed after a *successful* urlopen,
  which never fires. All strictly improved, all live-checked after the swap. The transport's own tests no longer
  leave `time.sleep` monkeypatched process-wide — that had `test_wd_pace_actually_waits` failing
  for any run that put this directory ahead of `tests/`, which `ci.yml`'s argument order hid.

  ⭐ **The one subclass where migration IS uniform, found 2026-09-16 by reading:** a file whose
  ONLY 429 handling is `if r.status == 429` inside a `with urlopen(...)` block. That branch is
  unreachable — urllib's default opener raises `HTTPError` on any non-2xx, so the body never runs
  and `r.status` is always a success code (proved against a local server answering 429, pinned in
  `test_wdqs_transport.py`). None of them had a retry construct either, so the whole documented
  policy was absent and the module is strictly stronger with no per-file judgement left. Verified by
  reading every member: none has an `except HTTPError` 429 branch, and none has a retry construct
  around its WDQS call (kofun's loop is `for q in (q1, q2)`; the loops in address-citation, p3225,
  shakaku and souken are in their ja.wikipedia fetchers).

  **Fourteen files are in it.** The five whose only urlopen was the WDQS one migrated as one batch.
  Eight of the other nine also fetch ja.wikipedia, rakuten or the Wikidata API through urlopen, so
  each needs that fetcher moved to `requests` as well (what `generate_court_rank_quickstatements.py`
  did) before it can satisfy the no-raw-urlopen assertion — still each file's own next-real-change:
  `generate_address_citation_from_article.py`, `generate_kofun_quickstatements.py`,
  `generate_ontology_census_page.py`, `generate_p3225_quickstatements.py`,
  `generate_shakaku_references.py`, `generate_souken_quickstatements.py`, `match_kokugakuin_ids.py`,
  `parse_onkamui_bunrei.py` (WDQS half only — its rakuten fetcher carries the same dead check and is
  a different host).
  - ⚠ **`generate_description_fixes.py` is NOT in the subclass** even though it carries the dead
    line: it has a live `except HTTPError` 429 bail beside it, so the dead line is decoration, not
    the whole policy. It keeps its own transport by the module's own note.
  - ⚠ **`shinto_miraheze/build_ronsha_ranking_queue.py` is in the subclass and was left alone**:
    `wdqs_transport` lives in `modern-quickstatements/`, and a plain `import wdqs_transport` does
    not reach across. Nothing here imports that way yet, so wiring it is a cross-subproject
    dependency decision, not a mechanical swap.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-15 (evening)**: `73ea2203` :03, `4db94229` :15, `68188662` :42,
    `5824b16c` 08:03. `CronList` reported **no jobs at all** at the start of this session — including
    the set created earlier the same day, which died with that session. Every recorded set this file
    has carried has been dead by the time the next session read it. Trust `CronList`, not this line.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
