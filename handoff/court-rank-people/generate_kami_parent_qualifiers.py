#!/usr/bin/env python3
"""Qualify a kami's P40 (child) statement with the OTHER parent.

Emma 2026-07-16, reading the census (docs/ontology_census.html):

    child (P40)  — 71 qualified statements
        mother (P25)   43
        father (P22)   16

    "For these, I believe that the child being able to go through to grab the
     mother and father of the child and then add this as a qualifier is something
     that we can actually pretty easily do with our quick statements to add a bit
     of context. I believe we can do this pretty programmatically, and this is
     super easy to run, and it is valuable."

THE MODEL. On <parent> P40 <child>, a P25/P22 qualifier names the child's OTHER
parent — "this child, by that mother". That fact is already recorded on the
CHILD's own item as its P22/P25. So this is a JOIN over existing data, not an
inference:

    <A> p:P40 <C>   and   <C> wdt:P22 <A>   and   <C> wdt:P25 <M>
      =>  A|P40|C|P25|M        (A is the father; M is the other parent)

    <A> p:P40 <C>   and   <C> wdt:P25 <A>   and   <C> wdt:P22 <F>
      =>  A|P40|C|P22|F        (A is the mother; F is the other parent)

Nothing is guessed. If the child does not record the other parent, no line is
emitted.

ADD-ONLY and self-healing, so it is drip-safe under random execution order:
  - only emits where the qualifier is ABSENT (the query filters on that), so the
    file shrinks as lines land and never needs a cursor;
  - never touches a P40 statement whose qualifier is already set;
  - refuses when the child names MORE THAN ONE father or mother — that is an
    ontology question, not a mechanical one, and per Emma "it's not the job of
    the script to find ontology errors it's the job to extend existing patterns".

Output: kami_parent_qualifiers.txt (an ATOMIC_FILES entry -> the daily drip).
"""
import io
import os
import sys
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import wdqs_transport

_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "shinto_miraheze")):
    _root = os.path.dirname(_root)
if _root not in sys.path:
    sys.path.insert(0, _root)
# The User-Agent moved into wdqs_transport with the request. It still imports
# WIKIDATA_USER_AGENT unconditionally, for the reason this comment used to carry:
# the import used to sit in a try/except whose handler built a non-canonical agent
# by hand, marked `pragma: no cover` — a silent fail-OPEN in a system whose whole
# design is fail-closed. An unimportable agent must stop the run instead.

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

KAMI_CLASS = "Q524158"
OUTFILE = os.path.join(_here, "kami_parent_qualifiers.txt")


def sparql(query):
    """One WDQS query through the shared transport.

    ⚠ This used to pace itself with a bare `wd_pace()`, which is READ_INTERVAL —
    **0.3s**. `wd_pace.py` says in its own docstring not to pace a SPARQL caller at
    READ_INTERVAL, and this file fires one query per (parent_prop, other_prop) pair,
    so it was the shape CLAUDE.md's 2.5s floor exists to stop. The transport paces
    at the floor and a call site cannot forget it.
    """
    return wdqs_transport.query(query)


def fetch(parent_prop, other_prop):
    """P40 statements where the child names `parent_prop`=the subject, and also
    names `other_prop` — and the statement lacks an `other_prop` qualifier."""
    return sparql(f"""
    SELECT DISTINCT ?a ?child ?other WHERE {{
      ?a wdt:P31/wdt:P279* wd:{KAMI_CLASS} .
      ?a p:P40 ?st .
      ?st ps:P40 ?child .
      ?child wdt:{parent_prop} ?a .          # the subject really is that parent
      ?child wdt:{other_prop}  ?other .      # and the child records the other one
      FILTER NOT EXISTS {{ ?st pq:{other_prop} ?already }}
      FILTER(?other != ?a)
      # Blank nodes are somevalue/novalue snaks, NOT entities. Without this a
      # child whose other parent is "unknown value" emitted a raw hash as the QS
      # value: Q10731395|P40|Q10919837|P25|7dcf796c581d6acb8ee22e6b7d874d3a
      FILTER(isIRI(?other) && isIRI(?child))
    }}""")


def sole(prop, qids):
    """{qid: value} keeping only children with exactly ONE value for prop.

    A child naming two fathers is a modelling question, not a mechanical one.
    """
    if not qids:
        return {}
    values = " ".join(f"wd:{q}" for q in qids)
    rows = sparql(f"""
    SELECT ?c (COUNT(DISTINCT ?v) AS ?n) (SAMPLE(?v) AS ?v1) WHERE {{
      VALUES ?c {{ {values} }}
      ?c wdt:{prop} ?v .
    }} GROUP BY ?c""")
    return {r["c"]["value"].split("/")[-1]: r["v1"]["value"].split("/")[-1]
            for r in rows if int(r["n"]["value"]) == 1}


def main():
    lines, skipped = [], 0
    for parent_prop, other_prop, role in [("P22", "P25", "father -> add mother"),
                                          ("P25", "P22", "mother -> add father")]:
        rows = fetch(parent_prop, other_prop)
        children = {r["child"]["value"].split("/")[-1] for r in rows}
        single = sole(other_prop, children)     # drop ambiguous children
        n = 0
        for r in rows:
            a = r["a"]["value"].split("/")[-1]
            c = r["child"]["value"].split("/")[-1]
            other = r["other"]["value"].split("/")[-1]
            # A somevalue/novalue snak comes back as a BLANK NODE, whose "value"
            # is a bare hash, not a QID. The SPARQL isIRI() filter did not catch
            # these, so guard here — this is what stops
            #   Q10731395|P40|Q10919837|P25|7dcf796c581d6acb8ee22e6b7d874d3a
            # reaching the drip. "unknown mother" is not a mother.
            if not (a.startswith("Q") and c.startswith("Q") and other.startswith("Q")):
                skipped += 1
                continue
            if single.get(c) != other:          # child names >1 of other_prop
                skipped += 1
                continue
            lines.append(f"{a}|P40|{c}|{other_prop}|{other}")
            n += 1
        print(f"  {role:24} {n:>4} lines  ({len(rows)} candidates)")

    lines = sorted(set(lines))
    with open(OUTFILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"\nwrote {OUTFILE}: {len(lines)} qualifier lines")
    print(f"  skipped {skipped} where the child names more than one such parent")
    if lines:
        print("\n--- sample ---")
        for l in lines[:8]:
            print("  " + l)


if __name__ == "__main__":
    main()
