# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Miraheze is unreachable from CI — decide the route, it cannot be fixed from inside this repo.**
  ANSWERED 2026-09-12 (`DEVLOG.md`, `shinto_miraheze/probe_miraheze_403.py`): Cloudflare serves our
  GitHub Actions runners a managed challenge — 272 KB of `text/html`, *"Checking your connection…"* —
  on **every** request including unauthenticated reads, while the identical script from a home
  connection gets 200 throughout. The control proves it is not the UA: a deliberately generic UA from
  the same runner still gets Miraheze's own 193-byte `text/plain` policy message.
  - So: not the User-Agent, not the bot account, not the wiki being down. Emma guessed a UA change
    broke it; the dates rule that out both ways — `EmmaBot/3.1` (set 2026-08-18) passed the weekly
    test from CI on 08-19, 08-23 and 08-30 and carried **3,000 edits over 09-01..09-04**, and no UA
    change lands before the first 403s of 07-12. The block began **between 09-04 and 09-06**, so it
    is INTERMITTENT — an earlier note here calling CI permanently unable to reach the wiki was wrong.
  - Leading hypothesis, NOT confirmed: the challenge says *"unusual activity"* and the four days
    before it ran 502/859/853/786 edits. A fit, not a finding — Emma's 2026-07-27 quiet period is
    evidence against volume being the whole story, since the challenge came back after it.
  - [ ] Emma's call, since the remedy is outside the repo: ask Miraheze to allowlist the bot, or run
    the wiki-writing jobs from an origin that is not challenged. Do not spend more ticks re-probing.
  - ⚠ This also reframes `docs/fandom_vs_miraheze_2026-09-12.md`: its reliability table compares one
    host that challenges our runners with one that does not, which is not a comparison of the two
    wikis.

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
