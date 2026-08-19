#!/usr/bin/env python3
"""Wikidata gate: is "Immanuelle" still named on the two enwiki pages?

Emma, 2026-08-06: the Wikidata editing freeze is gated on the **enwiki** situation —
no Wikidata editing while "Immanuelle" is mentioned on [[Wikipedia:AI noticeboard]] or
[[Wikipedia talk:WikiProject Japan]]. Her clarification the same day, on which side the
gate belongs: *"the freeze thing there is a wikidata thing, based on the enwiki thing,
shintowiki if it still runs is not an issue."* So this gates the QuickStatements
pipeline, NOT shinto.miraheze.org editing. Her read on how long: the mentions will
*"probably disappear pretty quickly but not 100% sure"* — which is why the gate is a
condition and not a date.

`cleanup-loop.yml`'s window-gate runs this live: a non-zero exit forces
`wikidata-daily-fire=false`, so the QS submission and its `direct_daily_edits.py`
fallback never run. `enwiki-mention-check.yml` runs it daily with `--record` so the
state file carries a visible history rather than a memory of the last check.

Reads en.wikipedia.org only. It touches NOTHING on shinto.miraheze.org — the Miraheze
blackout is a separate rule with its own state file.

    python check_enwiki_mentions.py            # report
    python check_enwiki_mentions.py --record   # also write enwiki_mention_gate.state

Exit 0 = clear (no mentions) — Wikidata editing may proceed as far as this gate cares.
Exit 1 = mentions remain, or the check failed — Wikidata editing stays frozen.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT

import argparse
import datetime
import io
import json
import pathlib
import urllib.parse
import urllib.request
from shinto_miraheze.wd_pace import wd_pace

STATE = pathlib.Path(_uar) / "shinto_miraheze" / "enwiki_mention_gate.state"
NEEDLE = "Immanuelle"
PAGES = [
    "Wikipedia:AI noticeboard",
    "Wikipedia talk:WikiProject Japan",
]


def count_mentions(title):
    """(count, error). Raw wikitext, so an archived thread stops counting."""
    url = ("https://en.wikipedia.org/w/index.php?action=raw&title="
           + urllib.parse.quote(title))
    req = urllib.request.Request(url, headers={"User-Agent": ua_for(url)})
    try:
        wd_pace()
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    return text.count(NEEDLE), None


def evaluate():
    """(clear: bool, per_page: dict, failed: bool)."""
    per_page, total, failed = {}, 0, False
    for title in PAGES:
        n, err = count_mentions(title)
        if err is not None:
            failed = True
            per_page[title] = f"CHECK FAILED: {err}"
            continue
        per_page[title] = n
        total += n
    # A page that could not be read is not evidence of absence. Fail closed.
    return (not failed and total == 0), per_page, failed


def main():
    _usys.stdout = io.TextIOWrapper(_usys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true",
                    help="write the result to shinto_miraheze/enwiki_mention_gate.state")
    args = ap.parse_args()

    clear, per_page, failed = evaluate()
    for title, val in per_page.items():
        print(f"{title}: {val}" if isinstance(val, str)
              else f"{title}: {val} mention(s) of {NEEDLE!r}")

    if failed:
        print("GATE CLOSED — a page could not be read; an unreadable page is not absence.")
    elif clear:
        print("GATE OPEN — no mentions remain; the enwiki condition no longer blocks "
              "Wikidata editing.")
    else:
        print("GATE CLOSED — mentions remain; NO Wikidata editing.")

    if args.record:
        prior = {}
        if STATE.exists():
            try:
                prior = json.loads(STATE.read_text(encoding="utf-8"))
            except Exception:
                prior = {}
        now = datetime.datetime.now(datetime.timezone.utc)
        state = {
            "gate": "enwiki mentions of Immanuelle (Emma 2026-08-06)",
            "blocks": "Wikidata editing (QuickStatements submission + direct-edit fallback)",
            "condition": ("clear when 'Immanuelle' appears on neither "
                          "[[Wikipedia:AI noticeboard]] nor "
                          "[[Wikipedia talk:WikiProject Japan]]"),
            "clear": clear,
            "pages": per_page,
            "checked": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "first_checked": prior.get("first_checked") or now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": ("shinto.miraheze.org editing is NOT gated on this — Emma 2026-08-06: "
                     "'the freeze thing there is a wikidata thing, based on the enwiki thing, "
                     "shintowiki if it still runs is not an issue'."),
        }
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
        print(f"recorded into {STATE.name}")

    return 0 if clear else 1


if __name__ == "__main__":
    # Exit codes are LOAD-BEARING and the caller distinguishes all three:
    #   0 = gate CLEAR   1 = gate CLOSED (mentions remain)   2 = the check itself FAILED
    #
    # Before 2026-08-19 an exception also exited 1, so a crash was indistinguishable from a
    # normal closed gate. That happened for real: a fail-closed User-Agent router had no entry
    # for en.wikipedia.org, this script raised, and the workflow printed "Mentions remain —
    # Wikidata editing stays frozen" and reported success. The gate is designed to OPEN BY
    # ITSELF when the threads archive off; a crash that reads as "still closed" means it can
    # never open, and nothing says so. Fail loudly instead.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("CHECK FAILED — this is NOT 'the gate is closed'. The gate state was not updated.")
        raise SystemExit(2)
