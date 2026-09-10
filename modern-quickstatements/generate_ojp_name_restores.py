"""
generate_ojp_name_restores.py
=============================
Put back the four ojp-hani P1448 official names that `kana_redundant_remove.txt`
deleted, with their references and qualifiers.

WHAT HAPPENED. `generate_kana_qualifier_remove.py` emitted lines of the shape

    -Q135040123|P1448|ojp-hani:"白城神社"|P1814|"シラキノ"

meaning "drop the redundant raw katakana qualifier from this official name".
QuickStatements cannot do that — `Help:QuickStatements` lists *"remove a qualifier
without removing the statement itself"* under what it cannot do — and a `-` line
removes the whole statement whatever fields follow it. `direct_daily_edits`
reaches the same end by a different route: it parses the trailing qualifier fields
and then ignores them, matching entity+property+value and calling `wbremoveclaims`
on the claim. So each line deleted an entire official name: its value, its two
references, its P1264, and the カミノヤシロ qualifier that
`generate_kana_qualifier_add.py` had just placed on it.

332 such lines were queued. Four ran, after Emma lifted the Wikidata lockout on
2026-09-06 — the rest were stopped on 2026-09-09. Emma's ruling that day:
*"Rebuild them from history."*

| item | name | deleted | restored from parent revid |
|---|---|---|---|
| Q135040123 | 白城神社 | 2026-09-07 | 2514653730 |
| Q135070009 | 御食神社 | 2026-09-07 | 2514473910 |
| Q135194697 | 風速神社 | 2026-09-07 | 2541518816 |
| Q135195565 | 大神社   | 2026-09-08 | 2520963592 |

The statement content below is copied verbatim from those parent revisions, so
this is a restore, not a reconstruction — no value is inferred.

SHAPE: one line per qualifier and one line per reference block, never a line that
carries several at once. `execute_set_qualifier` fails the WHOLE line when any one
qualifier is already present ("The statement has already a qualifier with hash …"),
so a fat line becomes unrunnable the moment any part of it has landed. Split this
way every line is independently idempotent and the drip's random order cannot
matter: whichever line runs first creates the bare statement, the others attach
their own piece to it.

ADD-ONLY and self-healing: each build asks Wikidata what is already back and emits
only what is still missing. It goes empty by itself once all four are whole.

Output: ojp_name_restores.txt
"""
import io
import json
import os
import sys
import time

import requests

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WD_API = "https://www.wikidata.org/w/api.php"
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "ojp_name_restores.txt")

# Verbatim from the parent revision of each removing edit. `quals` and `refs` keep
# the original order; a ref block is one reference, its snaks in `snaks-order`.
DESTROYED = [
    {
        "qid": "Q135040123", "name": "白城神社", "parent_revid": 2514653730,
        "quals": [("P1264", ("item", "Q193292")),
                  ("P1814", ("str", "シラキノ")),
                  ("P1814", ("str", "シラキノカミノヤシロ"))],
        "refs": [[("P4656", ("str", "https://ja.wikipedia.org/wiki/越前国の式内社一覧"))],
                 [("P248", ("item", "Q135159299")), ("P13677", ("str", "182203"))]],
    },
    {
        "qid": "Q135070009", "name": "御食神社", "parent_revid": 2514473910,
        "quals": [("P1264", ("item", "Q193292")),
                  ("P1814", ("str", "ミケノ")),
                  ("P1814", ("str", "ミケツ")),
                  ("P1814", ("str", "ミケツカミノヤシロ"))],
        "refs": [[("P4656", ("str", "https://ja.wikipedia.org/wiki/佐渡国の式内社一覧"))],
                 [("P248", ("item", "Q135159299")), ("P13677", ("str", "182477"))]],
    },
    {
        "qid": "Q135194697", "name": "風速神社", "parent_revid": 2541518816,
        "quals": [("P1264", ("item", "Q193292")),
                  ("P1814", ("str", "カサハヤノ")),
                  ("P1814", ("str", "カサハヤノカミノヤシロ"))],
        "refs": [[("P4656", ("str", "https://ja.wikipedia.org/wiki/越前国の式内社一覧"))],
                 [("P248", ("item", "Q135159299")), ("P13677", ("str", "182265"))]],
    },
    {
        "qid": "Q135195565", "name": "大神社", "parent_revid": 2520963592,
        "quals": [("P1264", ("item", "Q193292")),
                  ("P1814", ("str", "オシロノ")),
                  ("P1814", ("str", "オシロノカミノヤシロ"))],
        "refs": [[("P4656", ("str", "https://ja.wikipedia.org/wiki/因幡国の式内社一覧"))],
                 [("P248", ("item", "Q135159299")), ("P13677", ("str", "182728"))]],
    },
]


def qs(v):
    """A (kind, value) pair as a QuickStatements v1 field."""
    kind, val = v
    if kind == "item":
        return val
    return '"{}"'.format(val.replace("\\", "\\\\").replace('"', '\\"'))


def fetch_claims(qids):
    """{qid: claims dict}. One request; bails on 429 per the repo's 429 policy."""
    r = requests.get(WD_API, params={
        "action": "wbgetentities", "ids": "|".join(qids),
        "props": "claims", "format": "json",
    }, headers={"User-Agent": WIKIDATA_USER_AGENT}, timeout=60)
    if r.status_code == 429:
        raise SystemExit("FATAL: 429 Too Many Requests from the Wikidata API — bailing")
    r.raise_for_status()
    time.sleep(1)
    return {q: e.get("claims", {}) for q, e in r.json().get("entities", {}).items()}


def live_statement(claims, name):
    """The ojp-hani P1448 statement whose text is `name`, or None."""
    for st in claims.get("P1448", []):
        dv = st["mainsnak"].get("datavalue", {}).get("value", {})
        if isinstance(dv, dict) and dv.get("text") == name and dv.get("language") == "ojp-hani":
            return st
    return None


def snak_value(snak):
    """(kind, value) for a live snak, comparable with the DESTROYED table."""
    dv = snak.get("datavalue", {})
    val = dv.get("value")
    if isinstance(val, dict) and "id" in val:
        return ("item", val["id"])
    return ("str", val)


def has_qualifier(st, prop, value):
    return any(snak_value(s) == value for s in st.get("qualifiers", {}).get(prop, []))


def has_reference(st, block):
    """A live reference carrying every (prop, value) in `block`."""
    for ref in st.get("references", []):
        snaks = ref.get("snaks", {})
        if all(any(snak_value(s) == v for s in snaks.get(p, [])) for p, v in block):
            return True
    return False


def main():
    print("=== Restore the ojp-hani official names deleted by kana_redundant_remove ===\n")
    claims = fetch_claims([d["qid"] for d in DESTROYED])

    lines = []
    for d in DESTROYED:
        st = live_statement(claims.get(d["qid"], {}), d["name"])
        stmt = '{}|P1448|ojp-hani:"{}"'.format(d["qid"], d["name"])
        pieces = 0
        for prop, value in d["quals"]:
            if st is None or not has_qualifier(st, prop, value):
                lines.append("{}|{}|{}".format(stmt, prop, qs(value)))
                pieces += 1
        for block in d["refs"]:
            if st is None or not has_reference(st, block):
                tail = "|".join("S{}|{}".format(p[1:], qs(v)) for p, v in block)
                lines.append("{}|{}".format(stmt, tail))
                pieces += 1
        print("{} {} — {}".format(
            d["qid"], d["name"],
            "whole, nothing to do" if not pieces else "{} piece(s) still missing".format(pieces)))

    with io.open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sorted(lines)) + ("\n" if lines else ""))
    print("\nWrote {} lines to {} (0 means all four are whole again)".format(
        len(lines), os.path.basename(OUT_FILE)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
