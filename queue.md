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

- [ ] ~41 WDQS callers have no retry loop at all, so a truncated response body ends the run and
  their `.txt` — written only at the end — is lost for the day. **All 8 that HAD a retry loop are
  now covered** (2026-09-14), each with a faked-transport test that drives the real fetcher.

  ⛔ **Not a batch job, and the count is not the point.** Two published figures for this were regex
  artifacts before the taxonomy was read off the files; any regex over except-clauses will miscount.
  No two of the ~40 unmigrated transports share a body, so each is its own judgement about throttle,
  bail policy and where the parse sits. Against that: the failure costs one day of one file, because
  CI is `continue-on-error` and the next run repairs it. So this rides with each file's next real
  change, and `modern-quickstatements/wdqs_transport.py` is what it migrates to.

  ⭐ What made the 8 doable was realising the fix is ADDITIVE in both shapes — widen the clause
  where the parse is inside the try, guard the parse where it is outside — and that a faked
  transport verifies it without running a forty-minute sweep. I had tagged five of them
  "verifiable only by running a sweep" an hour after disproving exactly that.

- **Pinned tail (keep last)**

  - [ ] Ensure the FOUR session-local crons are running: work-loop :03, auto-flush :15,
    status-report :42, briefing 08:03. Crons are session-local and expire after 7 days, so a
    recorded ID is only ever evidence about the session that made it — check `CronList`, do not
    trust the IDs written here.
    ⛔ **There is NO debrief cron.** Emma retired it 2026-08-28: *"Debrief shouldn't happen anymore
    in this repo lol."* Do not recreate it from any doc that still says five.
    ✓ Live IDs, session of **2026-09-11**: `14f69b80` :03, `0bc8be25` :15, `e63f99f1` :42,
    `d553fe57` 08:03, created and verified via `CronList` this session. The four listed before these
    were the 2026-08-31 session's and were dead on arrival — the fourth such stale set this file has
    carried. Trust `CronList`, not this line.
    ⚠ The 08:03 briefing has **no skill in this repo** — `deep-briefing` lives in the hub and there is
    no `DAILY.md` here, so its prompt was written from what `DEVLOG.md` 2026-08-27 records of it:
    skip-check, push, then `AskUserQuestion` as the deliverable.
  - [ ] Run the status-report action once more independently as an end-of-session summary.
