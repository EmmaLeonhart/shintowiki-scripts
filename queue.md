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

- [ ] WDQS transports: adopters **63**; the rest ride each file's next real change.
  Seven defect classes were found and closed 2026-09-16/17 (dead-429, no-retry, CSV, sub-floor
  pacing, catch-and-exit, HTTPError-only, and three callers RETRYING a 429). Full accounts are in
  `DEVLOG.md` — they are finished work and do not belong here.

  What is still OPEN, and only this:
  - ⛔ **Do not batch the remainder.** 26 hand-rolled transport functions are left and **18 are clean
    on all four properties** (retry loop, 429 bails, truncated body retried, pace ≥ 2.5s), audited by
    AST 2026-09-16. There is no named defect left to fix.
  - ⛔ **Migration is NOT uniformly an upgrade — three proven mechanisms**, not a general warning:
    a stronger hand-rolled backoff (`generate_modern_shrine_ranking_qualifiers`: 450s vs the shared
    195s, so it STAYS); `strict=False` parsing; and a caller pacing itself above the 2.5s floor.
    `query()` takes `timeout` and `throttle` for the last two; `max(throttle, WDQS_THROTTLE)` means
    no caller can ask to be faster than the floor.
  - ⛔ **DO NOT PUT A NUMBER ON HOW MANY ARE FRAGILE from a regex.** Seven wrong answers so far from
    pattern-matching this population — the last three were checks I wrote myself in one night. Parse
    with `ast`, and read one flagged file before reporting anything.
  - `generate_description_fixes.py` stays off the shared module (its sibling imports it); it carries
    the policy rather than sharing it.

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
