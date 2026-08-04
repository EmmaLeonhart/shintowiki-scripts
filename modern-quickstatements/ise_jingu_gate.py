#!/usr/bin/env python3
"""Gate for the 21 神宮125社 item creations (`ise_jingu_creates.txt`).

Creating items is the most conspicuous thing this repo does to Wikidata, so this
gate is the conjunction of BOTH standing holds, and it fails closed on any error:

1. THE WIKIDATA FREEZE. Emma 2026-08-03 froze all Wikidata editing until
   2026-08-10. `cleanup-loop.yml` enforces that for the daily drip; the drip
   cannot create items, so `create_items.py` runs outside it and needs its own
   copy of the date. If Emma extends the freeze in CLAUDE.md, extend it here too.

2. THE CONFLICT GATE. The ブルーノ・プラス caution window — the same
   `conflict_gate` the drip consults. Creating 21 shrine items while a watched
   editor is active is exactly the visibility Emma ranks as worse than data loss.

Note what this gate does NOT do: it does not check whether the items already
exist. `create_items.py` does that per-block, live, and refuses any label that
already has an item with the same P31.
"""
import datetime
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import conflict_gate  # noqa: E402

# Mirrors FREEZE_WIKIDATA_UNTIL in cleanup-loop.yml / CLAUDE.md.
FREEZE_UNTIL = datetime.date(2026, 8, 10)

# `None` is a meaningful value for last_watched_edit (the watched editor has no
# edits at all), so the "not supplied" sentinel cannot be None.
_UNSET = object()


def is_open(today=None, last_watched_edit=_UNSET):
    """(open?, reason) — may the 21 Ise creations run yet?"""
    today = today or datetime.date.today()
    if today < FREEZE_UNTIL:
        return False, (f"Wikidata freeze until {FREEZE_UNTIL} "
                       f"({(FREEZE_UNTIL - today).days}d left)")
    try:
        if last_watched_edit is _UNSET:
            last_watched_edit = conflict_gate.fetch_last_watched_edit()
        if not conflict_gate.should_run(today, last_watched_edit):
            why = conflict_gate.pause_reason(today, last_watched_edit)
            return False, f"conflict_gate: {why}"
    except Exception as e:                       # fail closed, never open
        return False, f"conflict_gate could not be evaluated ({e}) — refusing"
    return True, f"open: past {FREEZE_UNTIL} and conflict_gate clear"


if __name__ == "__main__":
    ok, why = is_open()
    print(f"ise_jingu {'OPEN' if ok else 'CLOSED'}: {why}")
