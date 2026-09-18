"""Strip the ordinal-less `part of` leftover from shrines that also hold the real one.

The population is the `blank_ordinal_side` class of `p361_multi_part_of_audit.json`
(2026-08-19): an item holding TWO `P361` statements into the same Engishiki list, one
carrying the `P1545` series ordinal the list itself names and one carrying nothing. The
blank one is import residue; the ordinalled one is the membership.

WHY THIS WRITES TO `sequential_misc.txt` AND NOT TO AN ATOMIC FILE.

A QuickStatements removal matches on entity+property+VALUE. Both statements carry the
same value, so `-Q|P361|Qlist` does not say which of the two to take. What decides it is
`direct_daily_edits.find_claim`, which returns the FIRST claim on the item matching that
property and value and removes that one only -- qualifiers are never consulted. So the
line removes the leftover exactly when the leftover is the item's first `P361` statement
into that list, and removes the membership when it is not. That is a fact about live
claim ORDER, which this script reads and an atomic file cannot.

It also means the line must run ONCE. Drawn a second time out of the ~105k atomic pool
-- 0.28%/day, so not never -- the same line would match the surviving statement and take
the membership with it. `sequential_misc.txt` runs each line exactly once, in order, and
its cursor never revisits one. That is the whole reason this is not an ordinary batch.

RESIDUAL, stated rather than guarded: if something else removes the blank statement
between generation and execution, the line's value still matches the ordinalled keeper
and would take it. Nothing in the executor can see the difference. The exposure is the
same one every value-matched removal file here carries, and the standing ruling covers
the outcome -- Emma, 2026-08-25: "we remove it and then we add it again." Re-run this
script to re-confirm live state before appending anything.

WHAT IS DELIBERATELY EXCLUDED, and why each exclusion is not a guard against the work:

  * Already staged in a REGISTERED removal drip (`list_membership_removals.txt`,
    `multi_ordinal_removals.txt`, `orphan_membership_removals.txt`). Those files strip an
    affected item's membership into that list ENTIRELY, which is the established intent
    -- "every single membership thing on those items should be removed ... We remove it
    and then we add it again." A sequential line on the same pair is one removal too
    many, aimed at whatever survives the drip.
  * The whole `true_duplicate` class, for that reason: measured 2026-09-18, all 14 are
    staged in at least one of those three files. Most are not duplicate pairs at all but
    the multi-ordinal collapse (one statement carrying five `P1545` values beside the
    clean ones), which is `multi_ordinal_removals.txt`'s job.
  * Pairs whose removable statement is NOT the first matching claim. Value-matching
    cannot reach the second one, and the 2026-07-10 ruling on that shape stands: report
    only.
  * Pairs the audit marks "list names this item nowhere". Emma folded those into the
    orphan work on 2026-08-19; they are not this removal.

Read-only against Wikidata (one batched `wbgetentities`), so it is safe to run inside a
lockout. Appending its output to `sequential_misc.txt` is what eventually edits.

Usage:
    python modern-quickstatements/generate_p361_leftover_removals.py --dry-run
    python modern-quickstatements/generate_p361_leftover_removals.py
"""
import argparse
import io
import json
import os
import sys
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wd_pace import wd_pace  # noqa: E402
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "p361_multi_part_of_audit.json")
SEQUENTIAL = os.path.join(HERE, "sequential_misc.txt")
WD_API = "https://www.wikidata.org/w/api.php"

# The registered, dripping removal files. A pair present in any of them is already
# being stripped in full and must not also get a sequential line.
STAGED_FILES = (
    "list_membership_removals.txt",
    "multi_ordinal_removals.txt",
    "orphan_membership_removals.txt",
)


def load_population(audit_path=None):
    """(class, row) for every pair the audit puts in scope for a duplicate removal."""
    with io.open(audit_path or AUDIT, encoding="utf-8") as fh:
        audit = json.load(fh)
    out = [("true_duplicate", r) for r in audit["true_duplicate"]]
    out += [("blank_leftover", r) for r in audit["blank_ordinal_side"]
            if "leftover" in (r.get("verdict") or "")]
    return out


def load_staged(here=None):
    """{(item, list): {files}} over the registered P361 removal drips."""
    here = here or HERE
    staged = {}
    for name in STAGED_FILES:
        path = os.path.join(here, name)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line.startswith("-"):
                    continue
                parts = line[1:].split("|")
                if len(parts) >= 3 and parts[1] == "P361":
                    staged.setdefault((parts[0], parts[2]), set()).add(name)
    return staged


def fetch_claims(ids):
    """{qid: [claim]} for P361, live, in the order Wikidata serves them."""
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = WD_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(chunk),
            "props": "claims", "format": "json", "formatversion": "2"})
        req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
        wd_pace()
        with urllib.request.urlopen(req, timeout=60) as fh:
            data = json.load(fh)
        for qid, ent in data.get("entities", {}).items():
            out[qid] = ent.get("claims", {}).get("P361", [])
    return out


def statements_into(claims, list_qid):
    """The item's P361 claims pointing at that list, in live order."""
    keep = []
    for claim in claims:
        snak = claim.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        if snak.get("datavalue", {}).get("value", {}).get("id") == list_qid:
            keep.append(claim)
    return keep


def ordinals(claim):
    return [s.get("datavalue", {}).get("value")
            for s in claim.get("qualifiers", {}).get("P1545", [])]


def classify(cls, row, stmts, staged_in):
    """(line_or_None, reason). One place, so the exclusions read as a list."""
    item, lst = row["item"], row["list"]
    if staged_in:
        return None, ("already staged for a full strip in %s"
                      % ", ".join(sorted(staged_in)))
    if cls == "true_duplicate":
        return None, "true_duplicate class -- see module docstring, not this removal"
    if len(stmts) < 2:
        return None, "live state holds %d statement(s) -- nothing to de-duplicate" % len(stmts)
    first, rest = stmts[0], stmts[1:]
    if ordinals(first):
        return None, ("the first matching claim carries ordinal %s, so a value-matched "
                      "removal would take the membership" % ordinals(first))
    keepers = [o for c in rest for o in ordinals(c)]
    if not keepers:
        return None, "no ordinalled statement survives the removal"
    confirmed = set(row.get("list_says") or [])
    if confirmed and not (set(keepers) & confirmed):
        return None, ("the surviving ordinals %s are not the %s the list names"
                      % (sorted(keepers), sorted(confirmed)))
    return "-%s|P361|%s" % (item, lst), ("blank leftover is the first claim; %s survives"
                                         % ", ".join("ordinal " + o for o in keepers))


def build():
    """(lines, emitted_rows, excluded_rows)."""
    population = load_population()
    staged = load_staged()
    claims = fetch_claims([r["item"] for _, r in population])
    lines, emitted, excluded = [], [], []
    for cls, row in population:
        stmts = statements_into(claims.get(row["item"], []), row["list"])
        line, reason = classify(cls, row, stmts, staged.get((row["item"], row["list"])))
        if line:
            lines.append(line)
            emitted.append((cls, row, len(stmts), reason, line))
        else:
            excluded.append((cls, row, len(stmts), reason))
    return lines, emitted, excluded


def existing_sequential_lines(path=None):
    path = path or SEQUENTIAL
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    lines, emitted, excluded = build()

    print("EXCLUDED (%d):" % len(excluded))
    for cls, row, n, reason in excluded:
        print("  %-14s %-12s %-10s n=%d  %s"
              % (cls, row["item"], row.get("ja", "")[:9], n, reason))
    print("\nEMITTED (%d):" % len(emitted))
    for cls, row, n, reason, line in emitted:
        print("  %-12s %-10s n=%d  %s\n      %s"
              % (row["item"], row.get("ja", "")[:9], n, reason, line))

    already = set(existing_sequential_lines())
    new = [ln for ln in lines if ln not in already]
    print("\n%d line(s), %d not yet in sequential_misc.txt" % (len(lines), len(new)))
    if args.dry_run or not new:
        return
    # Append only, below the cursor: the cursor is an index into the executable
    # lines and anything inserted above it changes which edit runs next.
    with io.open(SEQUENTIAL, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(new) + "\n")
    print("appended %d line(s) to %s" % (len(new), SEQUENTIAL))


if __name__ == "__main__":
    main()
