#!/usr/bin/env python3
"""Is the 2026-08-06 editing hold's release condition met yet?

Emma, 2026-08-06: shintowiki does no editing until "Immanuelle" is no longer
mentioned on [[Wikipedia:AI noticeboard]] or [[Wikipedia talk:WikiProject Japan]].
Her read was that the mentions would probably archive off fairly quickly, but she
was not certain — so the hold is condition-gated, not dated, and this script is how
the condition gets evaluated instead of remembered.

Reads enwiki only. It touches NOTHING on shinto.miraheze.org — the Miraheze blackout
(blackout_until in wiki_editing_lockout.state) is a separate rule and still applies.

    python check_enwiki_mentions.py            # report
    python check_enwiki_mentions.py --record   # also stamp the result into the state file

Exit 0 = condition MET (no mentions; the hold can be lifted by a human).
Exit 1 = condition NOT met (mentions remain, or the check failed).

Lifting the hold is a human act: delete the `editing_hold` object from
shinto_miraheze/wiki_editing_lockout.state. This script never lifts it.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT

import argparse
import datetime
import io
import json
import pathlib
import urllib.parse
import urllib.request

STATE = pathlib.Path(_uar) / "shinto_miraheze" / "wiki_editing_lockout.state"
NEEDLE = "Immanuelle"
PAGES = [
    "Wikipedia:AI noticeboard",
    "Wikipedia talk:WikiProject Japan",
]


def count_mentions(title):
    """(count, error). Raw wikitext, so archived/removed threads stop counting."""
    url = ("https://en.wikipedia.org/w/index.php?action=raw&title="
           + urllib.parse.quote(title))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    return text.count(NEEDLE), None


def main():
    _usys.stdout = io.TextIOWrapper(_usys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true",
                    help="write the result into editing_hold.last_checked* in the state file")
    args = ap.parse_args()

    total, failed, parts = 0, False, []
    for title in PAGES:
        n, err = count_mentions(title)
        if err is not None:
            failed = True
            parts.append(f"{title}: CHECK FAILED ({err})")
            print(f"{title}: CHECK FAILED — {err}")
            continue
        total += n
        parts.append(f"{title}: {n} mention(s)")
        print(f"{title}: {n} mention(s) of {NEEDLE!r}")

    if failed:
        # A failed fetch is not evidence of absence. Treat it as not-met.
        print("CONDITION NOT MET — a page could not be read; not treating that as absence.")
        met = False
    else:
        met = total == 0
        print("CONDITION MET — no mentions remain; a human may delete `editing_hold` "
              "from wiki_editing_lockout.state." if met else
              f"CONDITION NOT MET — {total} mention(s) remain; the editing hold stands.")

    if args.record and STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
        hold = state.get("editing_hold")
        if hold:
            hold["last_checked"] = datetime.date.today().isoformat()
            hold["last_checked_result"] = "; ".join(parts) + (
                " - condition MET" if met else " - condition NOT met")
            STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
            print(f"recorded into {STATE.name}")
        else:
            print("no editing_hold in the state file — nothing to record")

    return 0 if met else 1


if __name__ == "__main__":
    raise SystemExit(main())
