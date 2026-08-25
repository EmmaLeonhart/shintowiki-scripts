#!/usr/bin/env python3
"""Gate for the 21 神宮125社 item creations (`ise_jingu_creates.txt`).

Creating items is the most conspicuous thing this repo does to Wikidata, so this
gate is the conjunction of BOTH standing holds, and it fails closed on any error:

1. THE WIKIDATA LOCKOUT, read from `shinto_miraheze/wikidata_editing_lockout.state`
   via `wikidata_edit_allowed.editing_allowed()`.

   This gate used to carry `FREEZE_UNTIL = datetime.date(2026, 8, 10)` — its own
   copy of the date, with a comment telling the next person to extend it by hand
   when Emma extended the freeze. Nobody did, so from 2026-08-10 it reported
   **OPEN throughout the lockout running to 2026-09-18**, and was saved from
   mattering only because `create_items.py` and `create-items.yml` check the real
   state file too. That is the precise failure CLAUDE.md describes: a freeze
   duplicated per-file is a freeze one file can miss, which is how create-items.yml
   once came within hours of creating two items through the 2026-08-06 freeze.
   Lifting or extending a lockout means editing that ONE state file.

2. THE CONFLICT GATE. The ブルーノ・プラス caution window — the same
   `conflict_gate` the drip consults. Creating 21 shrine items while a watched
   editor is active is exactly the visibility Emma ranks as worse than data loss.

Note what this gate does NOT do: it does not check whether the items already
exist. Nothing at run time does — `create_items.py` has no duplicate guard
(Emma removed it 2026-08-04). That question was answered when the batch was
generated: `build_subject_map.py` asked ja.wikipedia and Wikidata for an article,
a jawiki sitelink, and an exact ja label for each of the 21, and all three came
back empty. Re-running `lineage/build_ise_creates.py` is what re-checks it.
"""
import datetime
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

import conflict_gate  # noqa: E402
from shinto_miraheze.wikidata_edit_allowed import editing_allowed  # noqa: E402

# `None` is a meaningful value for last_watched_edit (the watched editor has no
# edits at all), so the "not supplied" sentinel cannot be None.
_UNSET = object()


def is_open(today=None, last_watched_edit=_UNSET):
    """(open?, reason) — may the 21 Ise creations run yet?"""
    today = today or datetime.date.today()
    try:
        allowed, detail = editing_allowed()
    except Exception as e:                       # fail closed, never open
        return False, f"wikidata lockout could not be evaluated ({e}) — refusing"
    if not allowed:
        return False, f"wikidata lockout: {detail}"
    try:
        if last_watched_edit is _UNSET:
            last_watched_edit = conflict_gate.fetch_last_watched_edit()
        if not conflict_gate.should_run(today, last_watched_edit):
            why = conflict_gate.pause_reason(today, last_watched_edit)
            return False, f"conflict_gate: {why}"
    except Exception as e:                       # fail closed, never open
        return False, f"conflict_gate could not be evaluated ({e}) — refusing"
    return True, "open: wikidata lockout clear and conflict_gate clear"


if __name__ == "__main__":
    ok, why = is_open()
    print(f"ise_jingu {'OPEN' if ok else 'CLOSED'}: {why}")
