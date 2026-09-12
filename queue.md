# shintowiki-scripts — Work Queue

Conventions in `CLAUDE.md`. Delete items when done (history → `DEVLOG.md`).

Finished work does not live here, even when it has not delivered yet. Emma, 2026-08-25, on the
lost-shrine creates: *"It is finished so it's not blocked lol shouldn't be in the queue."* Batches
that are built, wired and waiting only on the lockout date are recorded in `DEVLOG.md` and readable
from `ATOMIC_FILES`; they are not queue items.

## stuff to do today

- **Apply the 9 resolved `{{wikidata link}}` QIDs to the wiki.**
  `resolve_blank_wikidata_links.py` resolved 9 of the 58 named blank pages, each with its evidence
  recorded in `blank_wikidata_link_proposals.state`. Emma's own case checks out independently:
  `Shizensha` → `Q139921367`, the QID she wrote in the todo, reached via its stated name 自然社.
  - [ ] Write the applier and wire it into `wiki-cleanup.yml` — this repo has NO local wiki creds and
    the rule is to ship a CI step, not to defer. Standard flags (`--apply` default-off, `--max-edits`,
    `--run-tag`), `THROTTLE = 2.5`, and it must re-read each page and only fill a template that is
    still blank. shinto.miraheze is locked until 2026-09-14 (weekly edit-test 403), so it lands on the
    first fire after that; the lockout gates the WRITE, not the build.
  - The other 49 are refused with a named reason, not skipped: 39 state no Japanese name and are not a
    sitelink of anything (Tenrikyo sect texts, kuni-no-miyatsuko, shintowiki-only pages — many likely
    have no Wikidata item at all), 6 state a name that is not a sitelink (大祖教, 世界平和教団,
    大伯国造 …), 3 are one- or two-character titles (`R`, `S`, `T`), 1 states two names resolving to
    different items. Refusing these is the design; do not lower the bar to raise the count.

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
