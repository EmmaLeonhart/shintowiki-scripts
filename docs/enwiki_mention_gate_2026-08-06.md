# The enwiki-mention gate — Wikidata editing, held on a condition

**Emma, 2026-08-06.** No Wikidata editing while "Immanuelle" is named on
<https://en.wikipedia.org/wiki/Wikipedia:AI_noticeboard> or
<https://en.wikipedia.org/wiki/Wikipedia_talk:WikiProject_Japan>. Her read on how long
it lasts: *"probably gonna disappear pretty quickly but not 100% sure."*

## Which side it gates — this was got wrong once

Her first phrasing named shintowiki (*"shintowiki does not do any editing until
Immanuelle is not mentioned on … as like the wikidata stuff"*) and it was implemented
that way — a hold on `wiki_edit_allowed.py`, which stops the wiki bot. Asked directly,
she corrected it:

> *"uhh the freeze thing there is a wikidata thing, based on the enwiki thing,
> shintowiki if it still runs is not an issue."*

So the gate belongs on **Wikidata**, and shinto.miraheze.org editing is deliberately
**not** gated on it. The shintowiki-side hold was reverted (`a71f1184` → revert in the
same day's follow-up commit). Do not re-add it.

That direction also matches the threat model already on record: the concern is someone
finding the AI editing **on Wikidata** and blocking it, not the enwiki tags themselves.
The enwiki mentions are the signal that someone is looking.

## How it works

`shinto_miraheze/check_enwiki_mentions.py` fetches the raw wikitext of both pages and
counts `Immanuelle`. Exit 0 = clear, exit 1 = mentions remain **or the check failed**.

- **The live gate:** `cleanup-loop.yml`'s `window-gate` runs the script and forces
  `wikidata-daily-fire=false` on a non-zero exit, ahead of the existing
  `FREEZE_WIKIDATA_UNTIL` date check. The QuickStatements submission and its
  `direct_daily_edits.py` fallback are the only things that edit Wikidata, and both
  hang off that output, so a closed gate stops all of it on every trigger.
- **The daily record:** `enwiki-mention-check.yml` (06:40 UTC) runs the script with
  `--record` and commits `shinto_miraheze/enwiki_mention_gate.state`. It only records —
  the gate that stops the edits is evaluated live, so a failed run here cannot let
  editing through.
- **Fails closed.** A page that cannot be read counts as still-mentioned. An unreadable
  page is not evidence of absence.
- **It opens by itself** when the threads archive off. There is no date to push out and
  nothing to remember; the next `cleanup-loop` fire simply sees a clear check.
- Tests: `shinto_miraheze/tests/test_enwiki_mention_gate.py`.

State on 2026-08-06: **AI noticeboard 7 · WikiProject Japan talk 2 — closed.**

## What this does not touch

- **`FREEZE_WIKIDATA_UNTIL = 2026-08-10`** (Emma 2026-08-03, week-long stop) is
  unchanged and still runs on its own. Both must be satisfied.
- **The Miraheze blackout** (Emma 2026-07-27: no request of any kind to
  shinto.miraheze.org, reads included, until 2026-08-09) is a separate rule with its own
  state file and is unaffected.
- The wiki bot's own lockout (`wiki_editing_lockout.state`, weekly edit-test) is back to
  exactly what it was before 2026-08-06.
