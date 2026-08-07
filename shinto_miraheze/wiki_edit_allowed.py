#!/usr/bin/env python3
"""Guard: is wiki editing currently allowed, or are we in the week-long lockout?

Every scheduled wiki-WRITING workflow calls this as a bail-early step:

    if python shinto_miraheze/wiki_edit_allowed.py; then
      ... do the wiki edits ...
    else
      echo "wiki editing locked — skipping"
    fi

Exit 0 = editing allowed (no lockout, or the lockout has expired).
Exit 1 = LOCKED — the wiki-editing lockout is in force; skip all wiki writes.

The lockout is written by weekly_wiki_edit_test.py (the Sunday edit-test): a failed
edit locks editing for the week; a successful edit unlocks it. It carries a
`locked_until` date (8 days on failure, > the 7-day test cadence) so it never
auto-expires before the next Sunday test. See docs/wiki_403_audit_2026-07-11.md.

Separately, the state file may carry an `editing_hold` object. That is a HOLD set
by Emma, not by the weekly test: editing stays off until a stated CONDITION is met,
with no date attached. It outranks everything else here — no expiry can lift it and
the weekly edit-test cannot clear it. It is lifted by a human deleting the field
once the condition holds. See docs/editing_hold_2026-08-06.md.
"""
import datetime
import io
import json
import pathlib
import sys

STATE_PATH = pathlib.Path(__file__).with_name("wiki_editing_lockout.state")


def editing_allowed():
    """(allowed: bool, detail: str)."""
    if not STATE_PATH.exists():
        return True, "no lockout state file — editing allowed"
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        # A corrupt state file must not silently hard-lock the wiki forever.
        return True, f"lockout state unreadable ({e}) — defaulting to allowed"
    hold = state.get("editing_hold") or {}
    if hold.get("hold"):
        # Condition-gated, dateless, and above the weekly test. Only a human
        # removing the field lifts it.
        return False, ("HELD — " + (hold.get("release_condition") or "no condition recorded")
                       + f" (set {hold.get('set')} by {hold.get('set_by', 'unknown')})")
    if not state.get("locked"):
        return True, "editing not locked"
    locked_until = state.get("locked_until")
    if not locked_until:
        return False, "LOCKED (no expiry date recorded)"
    try:
        until = datetime.date.fromisoformat(locked_until)
    except ValueError:
        return False, f"LOCKED (unparseable locked_until={locked_until!r})"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if today >= until:
        return True, f"lockout expired ({locked_until}) — editing resumed"
    return False, f"LOCKED until {locked_until} — {state.get('reason', '')}"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    allowed, detail = editing_allowed()
    print(("ALLOWED — " if allowed else "LOCKED — ") + detail)
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
