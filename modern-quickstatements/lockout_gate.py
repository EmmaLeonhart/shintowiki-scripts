#!/usr/bin/env python3
"""Gate for create batches that need nothing beyond the Wikidata lockout.

Used by the 2026-09-28 deity batches (deity_creates.txt, deity_role_creates.txt).
The conflict_gate global pause was removed 2026-09-27 (Emma), so the lockout state
file is the only standing hold. Fails closed if the lockout cannot be read.
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
for p in (_here, _root):
    if p not in sys.path:
        sys.path.insert(0, p)

from shinto_miraheze.wikidata_edit_allowed import editing_allowed  # noqa: E402


def is_open(today=None):
    try:
        allowed, detail = editing_allowed()
    except Exception as e:                       # fail closed, never open
        return False, f"wikidata lockout could not be evaluated ({e}) — refusing"
    if not allowed:
        return False, f"wikidata lockout: {detail}"
    return True, "open: wikidata lockout clear"


if __name__ == "__main__":
    ok, why = is_open()
    print(f"lockout_gate {'OPEN' if ok else 'CLOSED'}: {why}")
