#!/usr/bin/env python3
"""Add Emma Leonhart's Google Scholar author ID — scheduled, one-a-day.

Emma 2026-07-15: add Google Scholar author ID (P1960) `kiJ9hGYAAAAJ` to her own
Wikidata item, `Q140568870` (Emma Leonhart), and **schedule the edit to occur in
two weeks** — 2026-07-29 — firing *on* that day rather than drifting for weeks in
the random atomic drip.

Mechanism: the sequential-misc queue (`sequential_misc.txt`), which
`direct_daily_edits.py` runs exactly one line/day, in order — so a line placed
there fires on the next daily run rather than waiting to be randomly sampled out
of the ~25k-line atomic pool. Wikidata still has one editing path (the daily
QuickStatements pipeline, CLAUDE.md); this only chooses which queue the line sits
in.

This generator OWNS exactly one executable line of `sequential_misc.txt` and keeps
it consistent with live state each run (like the repo's other live-diffed
generators — it shrinks as the value lands):

  * before GATE_DATE            -> the line is ABSENT (nothing to run yet);
  * on/after GATE_DATE, unlanded -> the line is PRESENT (fires one-a-day);
  * once P1960 is confirmed live -> the line is REMOVED (add-first, remove-only-
    when-confirmed-present; keeps the single sequential slot free afterwards).

Every executable line but this one is preserved in place; the header comments are
untouched. On any API error the line is left in its GATE-appropriate state (kept
if we cannot confirm the edit landed), never dropped on uncertainty.

    python generate_scholar_id.py
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import datetime
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from shinto_miraheze.wd_pace import wd_pace

HERE = os.path.dirname(os.path.abspath(__file__))
SEQUENTIAL_FILE = "sequential_misc.txt"
SEQUENTIAL = os.path.join(HERE, SEQUENTIAL_FILE)

WD_API = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT

# Two weeks from the 2026-07-15 request. A date rule, not a value to revert
# later (Emma's standing preference — express the exception as a rule).
GATE_DATE = datetime.date(2026, 7, 29)

QID = "Q140568870"          # Emma Leonhart
PROP = "P1960"              # Google Scholar author ID
VALUE = "kiJ9hGYAAAAJ"
TARGET_LINE = '{}|{}|"{}"'.format(QID, PROP, VALUE)


def _api(params):
    params = dict(params, format="json")
    req = urllib.request.Request(WD_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    wd_pace()
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def value_is_live():
    """True/False if P1960=VALUE is/ isn't on the item; None if the lookup fails
    (so the caller keeps the line rather than dropping it on uncertainty)."""
    try:
        ent = _api({"action": "wbgetentities", "ids": QID,
                    "props": "claims"}).get("entities", {}).get(QID)
        if not ent or "missing" in ent:
            return None
        for st in ent.get("claims", {}).get(PROP, []):
            dv = st["mainsnak"].get("datavalue")
            if dv and dv.get("value") == VALUE:
                return True
        return False
    except Exception:
        return None


def desired_present(today=None, live=None):
    """Should TARGET_LINE be an executable line of sequential_misc.txt right now?"""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    if live is True:
        return False          # landed — self-drain
    if today < GATE_DATE:
        return False          # not yet scheduled
    return True               # scheduled, not confirmed landed — keep firing


def apply_to_file(text, present):
    """Return sequential_misc.txt content with TARGET_LINE added/removed to match
    `present`, preserving every comment and every other executable line in place."""
    lines = text.split("\n")
    # Drop a single trailing empty element from a final newline so we can re-add it.
    trailing_nl = text.endswith("\n")
    if trailing_nl and lines and lines[-1] == "":
        lines.pop()

    has = any(l.strip() == TARGET_LINE for l in lines)
    if present and not has:
        lines.append(TARGET_LINE)
    elif not present and has:
        lines = [l for l in lines if l.strip() != TARGET_LINE]

    out = "\n".join(lines)
    if trailing_nl or out:
        out += "\n"
    return out


def main():
    argparse.ArgumentParser().parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    today = datetime.datetime.now(datetime.timezone.utc).date()
    live = value_is_live()
    present = desired_present(today, live)

    with io.open(SEQUENTIAL, "r", encoding="utf-8") as fh:
        before = fh.read()
    after = apply_to_file(before, present)
    if after != before:
        with io.open(SEQUENTIAL, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(after)

    state = ("live" if live is True else
             "absent" if live is False else "unknown (lookup failed)")
    action = "present" if present else "absent"
    changed = "changed" if after != before else "unchanged"
    print("  {} P1960 on Wikidata: {}; gate {} (today {})".format(
        QID, state, GATE_DATE.isoformat(), today.isoformat()))
    print("  sequential_misc.txt: TARGET_LINE {} ({})".format(action, changed))
    print("  " + TARGET_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
