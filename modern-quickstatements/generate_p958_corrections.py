"""Emit individual QuickStatements that CORRECT a wrong or missing P958 section.

Why this exists separately from generate_p958_qualifiers.py: that one is ADD-only. It
derives the section from the parent list's P1352 ranking and adds it where absent, and
it cannot touch a statement that already carries a P958 -- QuickStatements has no
"overwrite a qualifier" verb. So an item whose section is present but WRONG is invisible
to it forever.

That is a real gap, not a hypothetical one. Emma, 2026-08-19, on Kokugakuin page 181621:

    "https://www.wikidata.org/wiki/Q135039671 should be 'n/a' however
     https://www.wikidata.org/wiki/Q111776816 should be '1' and
     https://www.wikidata.org/wiki/Q134925373 should be '0'. There were actually
     significant errors here that we caught... We have to set up individual quick
     statements to change these things so that they get corrected."

A correction is two QS lines, because that is the only way QS expresses it:
    -QID|P13677|"id"|P958|"old"     remove the wrong qualifier
     QID|P13677|"id"|P958|"new"     add the right one

REPORT + GENERATE ONLY. This writes a text file. It makes no edits: the batch is pasted
into QuickStatements by hand, which is a separate channel from the scripts governed by
`wikidata_editing_lockout.state` (Emma: "quickstatements are separate").

The live state is read first, so a value that is already correct emits NOTHING rather
than a no-op remove/add pair -- Q135039671 below is exactly that case, and re-issuing it
would churn a statement for no reason.

Usage:  python generate_p958_corrections.py [--out p958_corrections.txt]
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API = "https://www.wikidata.org/w/api.php"

# (QID, Kokugakuin page id, the section it SHOULD carry).
# Sourced from Emma directly -- she read the page. Anything added here must come from
# someone having actually looked at the Kokugakuin page, not from an inference.
CORRECTIONS = [
    ("Q111776816", "181621", "1"),
    ("Q134925373", "181621", "0"),
    ("Q135039671", "181621", "n/a"),
]


def p13677_statements(qid):
    wd_pace()
    url = API + "?" + urllib.parse.urlencode(
        {"action": "wbgetclaims", "entity": qid, "property": "P13677", "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    out = []
    for st in data.get("claims", {}).get("P13677", []):
        value = st["mainsnak"].get("datavalue", {}).get("value")
        quals = st.get("qualifiers", {}).get("P958", [])
        sections = [q.get("datavalue", {}).get("value") for q in quals]
        out.append((value, sections))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="p958_corrections.txt")
    args = ap.parse_args()

    lines, notes, skipped = [], [], 0
    for qid, kid, want in CORRECTIONS:
        sts = p13677_statements(qid)
        match = [s for s in sts if s[0] == kid]
        if not match:
            notes.append(f"{qid}: NO P13677 statement with id {kid} -- nothing to correct, check the item")
            continue
        _, sections = match[0]
        if sections == [want]:
            notes.append(f"{qid}: already {want!r} -- correct, no statement emitted")
            skipped += 1
            continue
        for old in sections:
            lines.append(f'-{qid}|P13677|"{kid}"|P958|"{old}"')
            notes.append(f"{qid}: remove section {old!r}")
        lines.append(f'{qid}|P13677|"{kid}"|P958|"{want}"')
        notes.append(f"{qid}: add section {want!r}"
                     + ("" if sections else "  (was missing entirely)"))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    for n in notes:
        print(n)
    print(f"\n{len(lines)} QuickStatements line(s) -> {args.out}"
          f"   ({skipped} item(s) already correct, skipped)")


if __name__ == "__main__":
    main()
