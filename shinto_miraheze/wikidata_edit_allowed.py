#!/usr/bin/env python3
"""Guard: is WIKIDATA editing currently allowed, or are we inside a lockout?

Emma, 2026-08-18: "I want a gate to be set up that there will be no wikidata
editing for a month." This is that gate, and it is the SINGLE source of truth —
`shinto_miraheze/wikidata_editing_lockout.state`. Before it existed the freeze
was a `FREEZE_WIKIDATA_UNTIL="..."` date pasted into two separate workflow
files, which is exactly how create-items.yml came within hours of creating two
items straight through the 2026-08-06 enwiki-mention freeze: a freeze duplicated
per-workflow is a freeze one workflow can miss.

This is the Wikidata sibling of `wiki_edit_allowed.py` (which gates
shinto.miraheze). Two different wikis, two independent lockouts.

Every path that can WRITE to Wikidata calls this and bails early:

    if python shinto_miraheze/wikidata_edit_allowed.py; then
      ... do the Wikidata edits ...
    else
      echo "wikidata editing locked — skipping"
    fi

or, in Python:

    from shinto_miraheze.wikidata_edit_allowed import editing_allowed
    allowed, detail = editing_allowed()
    if not allowed:
        print("SKIPPED: " + detail)
        return 0

Exit 0 = editing allowed (no lockout, or the lockout has expired).
Exit 1 = LOCKED — skip all Wikidata writes.

The three credentialed writers (`direct_daily_edits.py`, `create_items.py`,
`substitute_source_shrine_proposal.py`) gate in code, so a lockout holds for a
local run too, not just for CI. The hand-run QuickStatements batches live in the
funding-and-networking repo and are gated there (`!quickstatements_now.bat`).

A locked run is a SKIP, not a failure: nothing was attempted, so nothing broke.
"""
import datetime
import io
import json
import pathlib
import sys

STATE_PATH = pathlib.Path(__file__).with_name("wikidata_editing_lockout.state")


def editing_allowed():
    """(allowed: bool, detail: str)."""
    if not STATE_PATH.exists():
        return True, "no wikidata lockout state file — editing allowed"
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        # A corrupt state file must not silently hard-lock Wikidata forever.
        return True, f"wikidata lockout state unreadable ({e}) — defaulting to allowed"
    if not state.get("locked"):
        return True, "wikidata editing not locked"
    locked_until = state.get("locked_until")
    if not locked_until:
        return False, "LOCKED (no expiry date recorded)"
    try:
        until = datetime.date.fromisoformat(locked_until)
    except ValueError:
        return False, f"LOCKED (unparseable locked_until={locked_until!r})"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if today >= until:
        return True, f"wikidata lockout expired ({locked_until}) — editing resumed"
    return False, f"LOCKED until {locked_until} — {state.get('reason', '')}"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    allowed, detail = editing_allowed()
    print(("ALLOWED — " if allowed else "LOCKED — ") + detail)
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
