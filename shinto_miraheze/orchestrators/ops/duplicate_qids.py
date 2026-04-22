"""
duplicate_qids op
==================
Read-only collector. Every orchestrator (mainspace, category, template,
miscellaneous) registers this op; on each page visit it extracts the QID
from ``{{wikidata link|Q...}}`` and records ``title -> qid`` in a shared
JSON dict at ``duplicate_qids.state`` next to the per-namespace state
files. Never modifies the page.

After all four orchestrators finish their sweep, ``find_duplicate_page_qids.py``
reads this dict, groups by QID, and renders the wiki report
[[Duplicate page QIDs]]. Because each orchestrator visits every page in
its namespace once per cycle and refreshes the entry, the dict converges
to an accurate wiki-wide snapshot across the four sequential runs.

The state file uses the ``.state`` extension (not ``.json``) so
``commit_state.sh`` picks it up alongside the other orchestrator state
files — that script globs by extension, not filename. Format is still
JSON; the extension is just a file-naming convention for CI pickup.
"""

import json
import os
import re

NAME = "duplicate_qids"
# Every wikitext namespace where {{wikidata link|...}} might appear. Matches
# history_offload.NAMESPACES so this op runs on the same pages the XML
# archive does.
NAMESPACES = (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    421, 829, 861, 863,
)

WDLINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)", re.IGNORECASE)

_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "duplicate_qids.state",
)


def _load() -> dict:
    if not os.path.exists(_STATE_FILE):
        return {}
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save(d: dict) -> None:
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)


def state_path() -> str:
    """Exposed so find_duplicate_page_qids.py can read the same file."""
    return _STATE_FILE


def apply(title: str, text: str):
    """Per-page callback. Updates the shared dict only; returns (None, None)
    so the orchestrator never tries to save the page."""
    d = _load()
    m = WDLINK_RE.search(text)
    new_qid = m.group(1).upper() if m else None
    old_qid = d.get(title)
    if new_qid == old_qid:
        return None, None
    if new_qid is None:
        d.pop(title, None)
    else:
        d[title] = new_qid
    _save(d)
    return None, None
