#!/usr/bin/env python3
"""Create Wikidata items from a gated CREATE/LAST batch. Separate from the drip.

Emma 2026-07-16, when told the drip cannot create items: "Different thing that
creates them."

So this is a SEPARATE tool, not an extension of direct_daily_edits.py:
  - direct_daily_edits.py stays what it is — statements on EXISTING items, randomly
    sampled, order-independent. Its ATOMIC_FILES contract is that any line can run
    at any time in any order. A CREATE block violates that by construction, which
    is why test_every_committed_atomic_line_parses rejected it.
  - creation is rarer, more conspicuous, and strictly ordered (LAST is meaningless
    until its CREATE lands). Its own tool, its own schedule, its own state.

WHY THIS EXISTS AT ALL. Nothing in this repo could create an item autonomously:
the QuickStatements toolforge API is permanently dead (it demands a one-time
manual web-UI batch Emma won't do), and direct_daily_edits has no
wbeditentity/new=item path. Every item to date — 37 papers, ~104 authors, the 15
honorifics — Emma ran by hand.

TWO SAFETY PROPERTIES:

1. IDEMPOTENT. Created QIDs are recorded in <batch>.state. A second run creates
   nothing. Without this, a re-run or a retried CI job silently doubles every item.

2. FAILS CLOSED. Gate errors and login failure abort. A creator that fails open
   is worse than one that never runs.

NO DUPLICATE GUARD. There used to be a check-exists-first pass refusing any label
that already existed with the same P31, carried over from a paper/author import
with an 18% duplicate rate. Emma removed it 2026-08-04: "I don't know why this
duplicate guard should exist. Just none." It was the wrong instrument here — it
searched ENGLISH labels, which for Japanese shrines are generic transliterations
(an unrelated 森神社 labelled "Mori Shrine" would have blocked 毛理神社), so it
refused real work while catching nothing a batch's own generator hadn't already
checked more precisely on the ja label. Whether a batch's contents are already on
Wikidata is the generator's question to answer, before the lines are written.

Usage:  python create_items.py --batch vsa_libraries.txt [--apply]
Default is DRY-RUN. --apply is required to write.

Env: MW_BOTNAME / BOT_TOKEN, same as direct_daily_edits.
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import time

import requests

_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "shinto_miraheze")):
    _root = os.path.dirname(_root)
if _root not in sys.path:
    sys.path.insert(0, _root)
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402
from shinto_miraheze.wikidata_edit_allowed import editing_allowed as wikidata_editing_allowed  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WD_API = "https://www.wikidata.org/w/api.php"

# batch file -> gate module name. A batch with no gate never runs.
GATES = {
    "vsa_libraries.txt": "vsa_libraries_gate",
    "ise_jingu_creates.txt": "ise_jingu_gate",
}


def load_blocks(path):
    """[[line, ...], ...] — one list per CREATE block, in file order."""
    blocks, cur = [], None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if s == "CREATE":
                if cur:
                    blocks.append(cur)
                cur = []
                continue
            if cur is None:
                raise SystemExit(f"{path}: statement before any CREATE: {s}")
            cur.append(s)
    if cur:
        blocks.append(cur)
    return blocks


def block_label(block):
    for line in block:
        m = re.match(r'^LAST\|Len\|"(.*)"$', line)
        if m:
            return m.group(1)
    return None


def block_p31(block):
    for line in block:
        m = re.match(r"^LAST\|P31\|(Q\d+)$", line)
        if m:
            return m.group(1)
    return None


def wd_login():
    user, token = os.environ.get("MW_BOTNAME"), os.environ.get("BOT_TOKEN")
    if not (user and token):
        raise SystemExit("MW_BOTNAME / BOT_TOKEN not set — refusing to run")
    s = requests.Session()
    s.headers.update({"User-Agent": WIKIDATA_USER_AGENT})
    lt = s.get(WD_API, params={"action": "query", "meta": "tokens",
                               "type": "login", "format": "json"}, timeout=30
               ).json()["query"]["tokens"]["logintoken"]
    r = s.post(WD_API, data={"action": "login", "lgname": user, "lgpassword": token,
                             "lgtoken": lt, "format": "json"}, timeout=30).json()
    if r.get("login", {}).get("result") != "Success":
        raise SystemExit(f"login failed: {r.get('login', {}).get('reason')}")
    csrf = s.get(WD_API, params={"action": "query", "meta": "tokens",
                                 "format": "json"}, timeout=30
                 ).json()["query"]["tokens"]["csrftoken"]
    return s, csrf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    args = ap.parse_args()

    # GATE 0 - THE WIKIDATA LOCKOUT. Emma, 2026-08-18: "I want a gate to be set up
    # that there will be no wikidata editing for a month." Single source of truth:
    # shinto_miraheze/wikidata_editing_lockout.state. It is checked here, in code,
    # rather than only in the workflow, so a local or manual run is covered too. A
    # locked run is a SKIP, not a failure: nothing was attempted, so nothing broke.
    wd_ok, wd_why = wikidata_editing_allowed()
    if not wd_ok:
        print("SKIPPED: wikidata lockout - {}".format(wd_why))
        return 0


    path = os.path.join(_here, args.batch)
    state_path = os.path.splitext(path)[0] + ".state"

    gate_name = GATES.get(args.batch)
    if not gate_name:
        raise SystemExit(f"{args.batch} has no gate in GATES — refusing to run")
    gate = __import__(gate_name)
    ok, why = gate.is_open()
    print(f"gate: {'OPEN' if ok else 'CLOSED'} — {why}")
    if not ok:
        return 0

    try:
        with open(state_path, encoding="utf-8") as fh:
            done = json.load(fh)
    except Exception:
        done = {}

    blocks = load_blocks(path)
    print(f"{len(blocks)} CREATE block(s) in {args.batch}; {len(done)} already created\n")

    session, csrf = (wd_login() if args.apply else (requests.Session(), None))
    if not args.apply:
        session.headers.update({"User-Agent": WIKIDATA_USER_AGENT})

    for block in blocks:
        label = block_label(block)
        if not label:
            print("SKIP: block has no LAST|Len label")
            continue
        if label in done:
            print(f"{label}: already created as {done[label]} — idempotent skip")
            continue

        if not args.apply:
            print(f"{label}: DRY RUN — would create with {len(block)} statement lines")
            continue

        # create the item, then apply its statements to the real QID
        r = session.post(WD_API, data={
            "action": "wbeditentity", "new": "item", "token": csrf,
            "data": json.dumps({"labels": {"en": {"language": "en", "value": label}}}),
            "format": "json"}, timeout=30).json()
        if "entity" not in r:
            print(f"{label}: CREATE FAILED — {r.get('error', {}).get('info')}")
            continue
        qid = r["entity"]["id"]
        print(f"{label}: created {qid}")
        done[label] = qid
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(done, fh, indent=2)   # persist BEFORE statements: never re-create

        import direct_daily_edits as dde
        for line in block:
            if re.match(r'^LAST\|Len\|', line):
                continue                      # the label is already set
            parsed = dde.parse_qs_line(line.replace("LAST", qid, 1))
            if not parsed:
                print(f"    SKIP unparseable: {line}")
                continue
            try:
                success, msg = dde.execute_line(session, csrf, parsed)
                print(f"    {'OK' if success else 'FAIL'}: {msg}")
            except Exception as e:
                print(f"    ERROR: {e}")
            time.sleep(2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
