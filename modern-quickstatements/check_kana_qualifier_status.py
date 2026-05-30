"""
check_kana_qualifier_status.py
==============================
READ-ONLY status check for the カミノヤシロ kana-qualifier work (Open questions #1).

Runs the SAME two SPARQL SELECT queries as ``generate_kana_qualifier_add.py``
(APPEND + SEED) and reports how many ADD candidates still remain on Wikidata,
without writing the pipeline ``.txt`` file or submitting anything.

Interpretation:
  * 0 APPEND + 0 SEED  → the automatic kana-qualifier work is DONE; only the
    manual "AMBIGUOUS" stragglers (items with 0 or >1 ojp-hani P1448 official
    names, which the generators can't disambiguate) would remain — Emma handles
    those directly on Wikidata.
  * >0                 → automatic work remains; the freeze (to 2026-06-06)
    blocks submitting it, but the candidates exist.

SPARQL SELECT only — no edits, safe under the Wikidata freeze. Bails on 429.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# NB: generate_kana_qualifier_add reassigns sys.stdout to a UTF-8 TextIOWrapper
# on import; we rely on that and must NOT wrap it again (double-wrap closes the
# underlying buffer).
from generate_kana_qualifier_add import fetch_sparql, is_katakana, OJP, SUFFIX

APPEND_Q = f"""
SELECT ?item ?on ?kana WHERE {{
  ?item p:P1448 ?st .
  ?st ps:P1448 ?on ; pq:P1814 ?kana .
  FILTER(LANG(?on) = "{OJP}")
  FILTER(!STRENDS(STR(?kana), "{SUFFIX}"))
  FILTER NOT EXISTS {{ ?st pq:P1814 ?done . FILTER(STRENDS(STR(?done), "{SUFFIX}")) }}
}}
"""

SEED_Q = f"""
SELECT ?item ?on ?top WHERE {{
  ?item p:P1448 ?st .
  ?st ps:P1448 ?on . FILTER(LANG(?on) = "{OJP}")
  FILTER NOT EXISTS {{ ?st pq:P1814 ?anyq }}
  ?item p:P1814 ?ts . ?ts ps:P1814 ?top .
}}
"""


def main():
    print("=== kana-qualifier status check (read-only) ===\n")

    rows = fetch_sparql(APPEND_Q) or []
    append = [r for r in rows if is_katakana(r["kana"]["value"])]
    print(f"APPEND candidates remaining: {len(append)}")
    for r in append[:10]:
        print(f"   {r['item']['value'].rsplit('/', 1)[-1]}  on={r['on']['value']}  kana={r['kana']['value']}")

    rows = fetch_sparql(SEED_Q) or []
    seen = set()
    seed = []
    for r in rows:
        if not is_katakana(r["top"]["value"]):
            continue
        key = (r["item"]["value"], r["on"]["value"], r["top"]["value"])
        if key in seen:
            continue
        seen.add(key)
        seed.append(r)
    print(f"SEED candidates remaining:   {len(seed)}")
    for r in seed[:10]:
        print(f"   {r['item']['value'].rsplit('/', 1)[-1]}  on={r['on']['value']}  top={r['top']['value']}")

    total = len(append) + len(seed)
    print()
    if total == 0:
        print("RESULT: 0 automatic kana-qualifier candidates remain → the bulk "
              "work is DONE. Only manual AMBIGUOUS stragglers (Emma's domain) "
              "could remain; Open questions #1 can be pruned.")
    else:
        print(f"RESULT: {total} automatic candidates remain (blocked from "
              "submission by the Wikidata freeze to 2026-06-06).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
