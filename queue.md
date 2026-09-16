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
  `ReadTimeout`/`ConnectionError` are now covered (2026-09-14), and the whole dead-429 subclass is
  closed (2026-09-16, below). What is left is the rest, and it is per-file reading.

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

  **Adopters: 20.** The first six joined on the tick of their own reference fix — the intended
  cadence. `generate_court_rank_quickstatements.py` had **0.5s** spacing (the exact figure CLAUDE.md
  cites from the incident that set the 2.5s floor) and a 5/10/15 backoff; the saijin and honzon
  generators each had no retry, no throttle, and a 429 check placed after a *successful* urlopen.

  ✅ **The dead-429 subclass is CLOSED (2026-09-16) — 14 files, all migrated.** A file whose only
  429 handling was `if r.status == 429` inside a `with urlopen(...)` block. That branch is
  unreachable: urllib's default opener raises `HTTPError` on any non-2xx, so the body never runs and
  `r.status` is always a success code. Proved against a local server answering 429, and pinned as
  `test_a_429_check_after_a_successful_urlopen_can_never_fire`. None of the 14 had a retry construct
  around its WDQS call either, so the whole documented policy was absent from every one — no
  per-file judgement was left, which is what made migrating them as a batch right rather than a
  breach of the cadence above. `test_no_adopter_kept_the_unreachable_429_check` stops it coming back.
  - Eight of them also fetched ja.wikipedia, the Wikidata API, jmapps or rakuten through `urlopen`;
    each of those fetchers moved to `requests` too, because the transport test reads a raw urlopen
    anywhere in an adopter as evidence it regrew its own WDQS client.
  - ⚠ **Each of those conversions also turned a 429 into a bail.** Under `urlopen` a 429 raised
    `HTTPError` and `except Exception` swallowed it straight back into a 3× retry loop — the
    opposite of the repo's unconditional policy, and indistinguishable from a timeout.
  - `shinto_miraheze/build_ronsha_ranking_queue.py` needed an explicit `sys.path` entry, since the
    transport lives in `modern-quickstatements/`. Not a new cross-subproject dependency: that file
    already writes its output into that directory.
  - Five of the eight carried a byte-identical `_get` for the ja.wikipedia API. **It is still five
    copies.** A shared ja.wp transport is a second module and was not smuggled into this change.

- [ ] `generate_description_fixes.py` backs off **30/60/90 over three attempts**. That is the linear
  pattern `wdqs_transport` was mistakenly lifted from and then corrected away from, and CLAUDE.md
  names 15/45/135 as the floor. Its 429 bail and its retryable set already match; only the
  escalation diverges. It is the one WDQS caller deliberately NOT on the shared transport — it is
  imported by its sibling — so this is a change to the file itself, on its next real touch. The
  transport's docstring used to claim it "has the same policy"; that claim is corrected, not the
  code.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-16**: `6d83d5f0` :03, `15ff3f04` :15, `403be522` :42,
    `6730a8f1` 08:03. `CronList` again reported **no jobs at all** at the start of this session, as
    it has at the start of every session that has checked. Every recorded set this file has carried
    has been dead by the time the next session read it. Trust `CronList`, not this line.
    ⚠ `durable: true` does nothing — `CronCreate` says so in its own parameter description ("Has no
    effect — durable persistence is not available"). So the recreate-every-session step is the only
    mechanism there is, not a workaround for one that keeps failing.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
