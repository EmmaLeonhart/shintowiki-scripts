#!/usr/bin/env python3
"""Gate for the three lost-shrine creations (`lost_shrine_creates.txt`).

Emma, 2026-08-24, asked for this batch to be registered so it delivers on 2026-09-18:
*"Register it — deliver on 2026-09-18."* A batch with no gate never runs, so this is what
registration actually consists of.

**It reads the lockout STATE FILE, it does not carry a date.** `ise_jingu_gate.py` was
written with `FREEZE_UNTIL = datetime.date(2026, 8, 10)` pasted into it, which is the exact
shape CLAUDE.md forbids — *"a freeze duplicated per-workflow is a freeze one workflow can
miss"* — and that date is now in the past, so that gate reports OPEN while the repo is
inside a lockout running to 2026-09-18. It is saved from mattering only because
`create_items.py` and `create-items.yml` both check the real state file too. A gate whose
own answer is wrong and is covered by something else is still a gate that will be believed
by the next person to read it, so this one asks the single source of truth directly.

Both standing holds have to be clear, and any error fails closed:

1. **The Wikidata lockout** — `shinto_miraheze/wikidata_editing_lockout.state`, via
   `wikidata_edit_allowed.editing_allowed()`. Lifting or extending it means editing that
   one file and nothing else.
2. **The conflict gate** — the ブルーノ・プラス caution window the drip also consults.
   That matters more here than anywhere: this batch exists *because* of that editor, and
   creating replacements for items they repurposed while they are actively editing is
   precisely the visibility Emma ranks as worse than data loss.

What this gate does NOT do is check whether the three shrines already have items. Nothing
at run time does — `create_items.py` has no duplicate guard, by Emma's instruction. That
question was answered when the batch was generated: `docs/bruno_plus_analysis_2026-07.md`
§4 established that none of the eight 加茂神社 items is the Odawara one, that no item holds
Chikadono any more, and that 見光寺's item now asserts a different temple. Re-running
`generate_lost_shrine_creates.py` is what re-checks it.
"""
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

# `None` is a meaningful value for last_watched_edit (the watched editor has no edits at
# all), so the "not supplied" sentinel cannot be None.
_UNSET = object()


def is_open(today=None, last_watched_edit=_UNSET):
    """(open?, reason) — may the three lost-shrine creations run yet?"""
    import datetime
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
            return False, f"conflict_gate: {conflict_gate.pause_reason(today, last_watched_edit)}"
    except Exception as e:                       # fail closed, never open
        return False, f"conflict_gate could not be evaluated ({e}) — refusing"

    return True, "open: wikidata lockout clear and conflict_gate clear"


if __name__ == "__main__":
    ok, why = is_open()
    print(f"lost_shrine {'OPEN' if ok else 'CLOSED'}: {why}")
