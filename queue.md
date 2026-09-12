# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Find out why shinto.miraheze 403s in CI but not locally.**
  Emma 2026-09-12, on the Fandom-vs-Miraheze research: *"yeah the miraheze wiki is supposed to just
  get edited like normal so idk what is going on with it lol."* That redirected the item from
  migrating away to diagnosing. The Fandom research is written up in
  `docs/fandom_vs_miraheze_2026-09-12.md` and is hers to read; no migration is planned.
  - Established: from a home connection **all three real probes return 200** (plain siteinfo, a page
    read, and siteinfo with mwclient's UA suffix), MediaWiki 1.45.4, `EmmaBot/3.1`. So the canonical
    UA is not blocked and the wiki is not down.
  - Established: a UA-policy refusal has a **distinct signature** — 403, `Content-Type: text/plain`,
    193 bytes, *"Your request is not compliant with our user agent policy."* A Cloudflare challenge
    would be HTML. Either one identifies itself; nothing recorded it until now.
  - [ ] Dispatch `probe-miraheze-403.yml` and compare its output with the local baseline above.
    Same script, two origins — that is the difference never tested. Azure `centralus` runner IPs
    versus a home connection.
  - [ ] Then fix the recording, whatever the answer: `weekly_wiki_edit_test.py` stores only the
    exception's `str()`, and its workflow pipes the script through `|| echo`, so five 403s produced
    no evidence between them. One failed probe also locks **8 days**.

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
