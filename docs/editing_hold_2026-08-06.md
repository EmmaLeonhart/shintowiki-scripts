# The 2026-08-06 editing hold — condition-gated, no date

**Emma, 2026-08-06:** shintowiki does no editing until "Immanuelle" is no longer
mentioned on <https://en.wikipedia.org/wiki/Wikipedia:AI_noticeboard> or
<https://en.wikipedia.org/wiki/Wikipedia_talk:WikiProject_Japan>. Her own read:
*"Probably gonna disappear pretty quickly but not 100% sure."*

## Why it needed new machinery rather than a date

The lockout state already had two gates and both are **dates**:

| Field | What it gates | How it ends |
|---|---|---|
| `locked_until` | every wiki-writing workflow, via `wiki_edit_allowed.py` | expires on its own; rewritten by the weekly edit-test |
| `blackout_until` | any Miraheze request at all, incl. the weekly probe | expires on its own, by design (self-draining) |

On 2026-08-06 they read `2026-08-10` and `2026-08-09`. Left alone, three days later
the blackout drains, the Sunday probe fires, and **if that probe's edit succeeds it
writes `locked: false`** — editing reopens, the 32 staged pages in `git_synced/`
create, and nothing anywhere would have consulted Emma's condition. A date cannot
express "until the mentions clear", and the only date available would have been an
invented one that expires silently at the wrong moment.

## What was added

`editing_hold`, an object in `shinto_miraheze/wiki_editing_lockout.state`:

```json
"editing_hold": {
  "hold": true,
  "set": "2026-08-06",
  "set_by": "Emma",
  "release_condition": "…",
  "note": "…",
  "last_checked": "2026-08-06",
  "last_checked_result": "…"
}
```

- **`wiki_edit_allowed.py` checks it first.** A hold returns LOCKED regardless of
  `locked`, `locked_until`, or anything else, so every workflow calling the guard is
  covered.
- **`weekly_wiki_edit_test.py` will not probe while it stands** — the probe *is* an
  edit — and `write_state()` carries the hold across any rewrite, so a pass cannot
  clear it.
- **Only a human lifts it**, by deleting the object. No date, no script, no test run
  can.
- `shinto_miraheze/tests/test_editing_hold.py` covers both bypass routes (expired
  date lock, and the edit-test's unlock path) plus the unheld behaviour.

## Checking the condition

```
python shinto_miraheze/check_enwiki_mentions.py [--record]
```

Reads the raw wikitext of both pages and counts `Immanuelle`; `--record` stamps the
result into the hold. Exit 0 = condition met. It reads **enwiki only** and touches
nothing on shinto.miraheze.org. A failed fetch counts as *not met* — an unreadable
page is not evidence of absence.

State on 2026-08-06: **AI noticeboard 7 · WikiProject Japan talk 2 — not met.**

## What is not covered

Six wiki-writing workflows are `workflow_dispatch`-only and do not call the guard
(`configure-wikidata-link-grok-categories`, `dedupe-duplicate-qids`,
`sunset-jp-char-count-cats`, `sunset-templates-not-transcluded-in-mainspace-cat`,
`tag-templates-not-transcluded-anywhere`, and the manual paths in `cleanup-loop`'s
children are gated but its own steps are not). Nothing schedules them, so the hold
has no scheduled hole; a human clicking Run in the Actions tab is the deliberate
override.

The Miraheze **blackout** (Emma 2026-07-27, `blackout_until: 2026-08-09`) is a
separate rule with a separate rationale and still applies on its own terms: no
request of any kind to shinto.miraheze.org, reads included.
