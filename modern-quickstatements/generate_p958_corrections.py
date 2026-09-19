"""Emit QuickStatements that CORRECT a wrong or missing P958 section — in two shapes.

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

────────────────────────────────────────────────────────────────────────────────────────
WHAT CHANGED 2026-09-18, and why the old output could never have run.

This used to emit, for every correction, the pair

    -QID|P13677|"id"|P958|"old"
     QID|P13677|"id"|P958|"new"

into one file. The first line is the shape `direct_daily_edits.execute_removal` refuses
outright, and refuses for a reason: a '-' line matches on entity+property+VALUE and calls
wbremoveclaims on the whole claim, so it deletes the P13677 statement, its references and
its other qualifiers rather than the named qualifier. That shape cost four items their
entire ojp-hani P1448 official name on 2026-09-09. So the file was unregistered, and
would have been a data-loss batch if anyone had registered it.

The remedy is not a new verb in the executor. Two shapes already exist that say exactly
what a correction means, and each correction is routed to the one that fits it:

  * **Section MISSING** -> one ordinary add line, `QID|P13677|"id"|P958|"new"`, written
    to `p958_corrections.txt`, which is registered in ATOMIC_FILES. Order-independent,
    so the random daily drip can run it whenever it draws it.

  * **Section PRESENT but wrong** -> a remove-then-add PAIR appended to
    `sequential_misc.txt`:

        -QID|P13677|"id"                                remove the whole statement
         QID|P13677|"id"|P958|"new"|<every other qualifier>|<every reference>

    The removal carries no qualifier fields, so it is not the refused shape and it is not
    pretending to be a qualifier edit: it takes the statement, and the line below rebuilds
    it. `sequential_misc.txt` runs one line per day in strict order and holds the cursor
    until a line lands, which is the only channel here where the add is guaranteed to
    follow its remove -- in the random atomic pool the remove could fire second and leave
    the item with no statement at all.

    The rebuild line is generated from the LIVE statement, so every qualifier besides
    P958 and every reference comes back. A statement whose rank is not normal, or which
    carries a snak this file cannot render back into QS v1, is REPORTED and not emitted:
    the pair would silently drop what it cannot write, and a correction that loses a
    reference is worse than a wrong section.

The live state is read first either way, so a value that is already correct emits NOTHING
rather than a no-op remove/add pair -- Q135039671 below is exactly that case.
────────────────────────────────────────────────────────────────────────────────────────

REPORT + GENERATE ONLY. This writes text files and makes no edits.

Generating is NOT clearance to submit. `wikidata_editing_lockout.state` is the one thing
that says and covers "EVERY write path... and the hand-run QuickStatements batches" in its
own words, so this output waits with everything else. (Emma's "quickstatements are
separate" was about pacing, not about the lockout -- an earlier version of this docstring
cited it the wrong way round and declared the batch ungated.)

Usage:  python generate_p958_corrections.py [--out p958_corrections.txt] [--dry-run]
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
import os
import sys
import urllib.parse
import urllib.request

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace

# NOT at import time: this module is imported by tests/test_p958_corrections_shape.py,
# and rewrapping stdout under pytest breaks its capture (I/O on closed file).
API = "https://www.wikidata.org/w/api.php"
HERE = os.path.dirname(os.path.abspath(__file__))
SEQUENTIAL = os.path.join(HERE, "sequential_misc.txt")

# (QID, Kokugakuin page id, the section it SHOULD carry).
# Sourced from Emma directly -- she read the page. Anything added here must come from
# someone having actually looked at the Kokugakuin page, not from an inference.
CORRECTIONS = [
    ("Q111776816", "181621", "1"),
    ("Q134925373", "181621", "0"),
    ("Q135039671", "181621", "n/a"),

    # Found 2026-08-25 by reading the Kokugakuin pages themselves, via
    # kokugakuin_candidates.py, while measuring that reader against 120 items whose
    # P958 is already set. It agreed with Wikidata on 72 and disagreed on these two —
    # and on both, the page is right and the item is wrong. Each was confirmed by
    # opening the entry rather than inferred from the mismatch.
    #
    # 181329 lists three candidates: (1)小山尾津神社 (2)尾津神社 (3)御衣野尾津神社.
    # Q135186791 is labelled 尾津神社 exactly, so it is slot 2; its recorded "1" is
    # 小山尾津神社's slot.
    ("Q135186791", "181329", "2"),
    # 180834 lists exactly one candidate and numbers it (2): （論）東大谷日女命神社.
    # There is no slot 1 on that page at all, so the recorded "1" cannot be right.
    ("Q135069120", "180834", "2"),
]


def p13677_claims(qid):
    """The item's full P13677 claims, live, in the order Wikidata serves them."""
    wd_pace()
    url = API + "?" + urllib.parse.urlencode(
        {"action": "wbgetclaims", "entity": qid, "property": "P13677", "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    return data.get("claims", {}).get("P13677", [])


def claim_value(claim):
    return claim.get("mainsnak", {}).get("datavalue", {}).get("value")


def sections_of(claim):
    return [q.get("datavalue", {}).get("value")
            for q in claim.get("qualifiers", {}).get("P958", [])]


def qs_token(snak):
    """A snak rendered back into a QS v1 value token, or None if it cannot be.

    Only the five value shapes `direct_daily_edits.parse_qs_value` can read back are
    rendered. Anything else returns None and the caller reports the statement instead of
    emitting a rebuild that would quietly drop it.
    """
    if snak.get("snaktype") != "value":
        return snak.get("snaktype") if snak.get("snaktype") in ("novalue", "somevalue") else None
    dv = snak.get("datavalue", {})
    kind, value = dv.get("type"), dv.get("value")
    if kind == "wikibase-entityid":
        qid = value.get("id")
        return qid if qid and qid.startswith("Q") else None
    if kind == "string":
        return '"%s"' % value
    if kind == "monolingualtext":
        return '%s:"%s"' % (value.get("language"), value.get("text"))
    if kind == "time":
        return "%s/%d" % (value.get("time"), value.get("precision"))
    if kind == "globecoordinate":
        return "@%s/%s" % (value.get("latitude"), value.get("longitude"))
    return None


def rebuild_line(qid, kid, want, claim):
    """(line, None) rebuilding the statement with `want` as its section, or (None, why)."""
    if claim.get("rank") not in (None, "normal"):
        return None, "rank is %r — a rebuild would silently normalise it" % claim.get("rank")

    parts = ["%s|P13677|\"%s\"|P958|\"%s\"" % (qid, kid, want)]

    for prop in sorted(claim.get("qualifiers", {})):
        if prop == "P958":
            continue                      # replaced by `want`, above
        for snak in claim["qualifiers"][prop]:
            token = qs_token(snak)
            if token is None:
                return None, "qualifier %s carries a snak this file cannot write back" % prop
            parts.append("%s|%s" % (prop, token))

    for ref in claim.get("references", []):
        for prop in ref.get("snaks-order") or sorted(ref.get("snaks", {})):
            for snak in ref.get("snaks", {}).get(prop, []):
                token = qs_token(snak)
                if token is None:
                    return None, ("reference %s carries a snak this file cannot write back"
                                  % prop)
                parts.append("S%s|%s" % (prop[1:], token))

    return "|".join(parts), None


def build(fetch=p13677_claims):
    """(add_lines, pair_lines, notes) for the whole CORRECTIONS table against live state."""
    add_lines, pair_lines, notes = [], [], []
    for qid, kid, want in CORRECTIONS:
        matches = [c for c in fetch(qid) if claim_value(c) == kid]
        if not matches:
            notes.append("%s: NO P13677 statement with id %s — nothing to correct, check "
                         "the item" % (qid, kid))
            continue
        if len(matches) > 1:
            notes.append("%s: %d P13677 statements carry id %s — a value-matched removal "
                         "cannot say which, so no pair is emitted"
                         % (qid, len(matches), kid))
            continue
        claim = matches[0]
        sections = sections_of(claim)

        if sections == [want]:
            notes.append("%s: already %r — correct, no statement emitted" % (qid, want))
            continue

        if not sections:
            add_lines.append('%s|P13677|"%s"|P958|"%s"' % (qid, kid, want))
            notes.append("%s: section missing — add %r (atomic, order-independent)"
                         % (qid, want))
            continue

        line, why = rebuild_line(qid, kid, want, claim)
        if line is None:
            notes.append("%s: section %s should be %r, NOT emitted — %s"
                         % (qid, sections, want, why))
            continue
        pair_lines.append('-%s|P13677|"%s"' % (qid, kid))
        pair_lines.append(line)
        notes.append("%s: section %s -> %r — remove-then-add pair (sequential), rebuild "
                     "carries %d qualifier(s) and %d reference(s)"
                     % (qid, sections, want,
                        len([p for p in claim.get("qualifiers", {}) if p != "P958"]),
                        len(claim.get("references", []))))
    return add_lines, pair_lines, notes


def existing_sequential_lines(path=None):
    path = path or SEQUENTIAL
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="p958_corrections.txt")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; write neither file")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    add_lines, pair_lines, notes = build()

    for n in notes:
        print(n)

    already = set(existing_sequential_lines())
    new_pairs = [ln for ln in pair_lines if ln not in already]

    print("\n%d add line(s) -> %s" % (len(add_lines), args.out))
    print("%d sequential line(s), %d not yet in sequential_misc.txt"
          % (len(pair_lines), len(new_pairs)))

    if args.dry_run:
        for ln in add_lines + new_pairs:
            print("   %s" % ln)
        return

    with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(add_lines) + ("\n" if add_lines else ""))

    if new_pairs:
        # Append only, below the cursor: the cursor is an index into the executable
        # lines and anything inserted above it changes which edit runs next.
        with io.open(SEQUENTIAL, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(new_pairs) + "\n")
        print("appended %d line(s) to %s" % (len(new_pairs), SEQUENTIAL))


if __name__ == "__main__":
    main()
