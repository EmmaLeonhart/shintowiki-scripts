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

<!-- scheduled:p958-corrections-batch-paste -->
## Scheduled — the P958 corrections batch is now pasteable

The Wikidata lockout (`shinto_miraheze/wikidata_editing_lockout.state`) ran to **2026-09-18**
and its own wording covered *"the hand-run QuickStatements batches"*, so this waited rather
than being treated as small enough to be an exception. That date has passed.

**Re-read the state file before acting** — the date passing is the expected unlock, but the
file is the authority, not this text.

Built 2026-08-19 by `modern-quickstatements/generate_p958_corrections.py`. A correction is
necessarily two lines, because QuickStatements has no verb for overwriting a qualifier.

**Regenerate before pasting** rather than trusting any block written earlier — the generator
reads live state first, so an already-correct item emits nothing instead of a churn pair.

- **BLOCKED-ON-USER-ACTION** once the date passes: her account, her paste, no date on it and
  nobody chasing it.

<!-- scheduled:p361-duplicate-part-of-removals -->
## Scheduled — the 24 `part of` removals are unblocked

Held by the Wikidata lockout to **2026-09-18**. Re-read
`shinto_miraheze/wikidata_editing_lockout.state` before acting; the file decides, not this
text.

**14 true duplicates** (the same ordinal repeated) plus **10 confirmed leftovers** (the
blank-ordinal side, in the cases where the list itself names the item at the ordinal already
carried). Per-item evidence is committed at
`modern-quickstatements/p361_multi_part_of_audit.json`.

**This is the sequential-misc mechanism's job, not QuickStatements'** — which of two
*identical* statements gets removed is not expressible by value. The mechanism is built,
tested, and ships empty.

⚠️ **Do not widen this to the other classes.** The audit's other two are explicitly not
defects: **47** carry distinct ordinals and are legitimate, and **42** name the item nowhere
on the list side — those were folded into the orphan work by Emma on 2026-08-19, not into
this removal. A blanket strip would have been wrong for 45 of 55.

