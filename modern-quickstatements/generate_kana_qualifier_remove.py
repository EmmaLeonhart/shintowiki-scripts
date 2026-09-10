"""
generate_kana_qualifier_remove.py
=================================
Step 2 of the カミノヤシロ kana-qualifier work (Wikidata bot request 2026-02-26):
the REMOVE generator. GENERATOR ONLY — writes QuickStatements removal lines into
an atomic .txt file for the single daily QS submitter. NEVER edits Wikidata; no
edit summaries.

This is the SEPARATE second script (see generate_kana_qualifier_add.py for step
1). It only ever emits a removal for a statement where a fresh SPARQL query
CONFIRMS the `<kana>カミノヤシロ` qualifier is already present on the ojp-hani P1448
official name. Because the confirmation is in the SPARQL itself, a removal can
never be generated before the add has actually landed — so the raw katakana
reading is never lost.

⛔ **THE SIBLING-QUALIFIER HALF IS GONE (2026-09-09). QuickStatements cannot remove
a qualifier.** `Help:QuickStatements` lists *"remove a qualifier without removing the
statement itself"* under what QuickStatements cannot do: a `-` line removes the whole
statement, whatever fields follow it. So the line this generator used to emit —

    -Q135040123|P1448|ojp-hani:"白城神社"|P1814|"シラキノ"

did not strip the redundant katakana qualifier. It deleted the entire ojp-hani official
name, taking the statement's references, its P1264, and the カミノヤシロ qualifier that
`generate_kana_qualifier_add.py` had just put there. `direct_daily_edits.execute_removal`
does the same thing by a different route: it parses the trailing qualifier fields and then
ignores them, matching on entity+property+value and calling `wbremoveclaims` on the claim.

Measured on the 332 pending lines, 2026-09-09: every one carried references (325 with two,
7 with one) and 329 carried a P1264 besides the P1814. **Four had already executed** —
Q135040123, Q135070009, Q135194697 (2026-09-07/08) and Q135195565 (2026-09-08), each now
with no P1448 at all. Removal resumed when Emma lifted the Wikidata lockout on 2026-09-06.

Only the top-level branch survives, and it is a genuine whole-statement removal, so
QuickStatements expresses it correctly.

For each ojp-hani P1448 that has a confirmed `<base>カミノヤシロ` qualifier, it
removes the now-redundant raw `<base>` katakana where it sits:
  * as a top-level P1814 statement on the item — but ONLY once EVERY ojp-hani
    P1448 name on the item already carries a カミノヤシロ qualifier. This guard
    matters for multi-name items (a shrine proposed as the site of several
    Engishiki shrines, with >1 ojp-hani P1448): the ADD step seeds the item's
    single top-level katakana onto each of those names, so the top-level is the
    SOURCE for all of them. Removing it after only one name's add has landed
    (QS runs in random order) would strand the names whose add hasn't run yet.
    So we hold the top-level removal until none of the item's ojp-hani names is
    still missing the qualifier — "add to both first, then remove top-level"
    (Emma 2026-05-30).
The modern (hiragana) top-level reading never matches and is left untouched.

Output: kana_redundant_remove.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import io
import sys
import time
import requests

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
SUFFIX = "カミノヤシロ"
OJP = "ojp-hani"
REMOVE_FILE = "kana_redundant_remove.txt"


class RateLimitError(Exception):
    """Raised on HTTP 429 — bail, no retries."""


_last = 0.0


def fetch_sparql(query, retries=3):
    global _last
    for attempt in range(1, retries + 1):
        elapsed = time.time() - _last
        if elapsed < 5:
            time.sleep(5 - elapsed)
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=120,
            )
        except requests.exceptions.ReadTimeout:
            _last = time.time()
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            print("SPARQL timed out after retries — exiting gracefully")
            return None
        _last = time.time()
        if r.status_code == 429:
            print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
            raise RateLimitError("429")
        if r.status_code in (503, 504):
            # CLAUDE.md: 503/504 -> back off hard, do not retry tightly.
            if attempt < retries:
                time.sleep(15 * (3 ** (attempt - 1)))
                continue
            print(f"SPARQL returned {r.status_code} after retries — exiting gracefully")
            return None
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def is_katakana(value):
    has_hira = any("぀" <= ch <= "ゟ" for ch in value)
    has_kata = any("゠" <= ch <= "ヿ" for ch in value)
    return has_kata and not has_hira


def s(text):
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def ronsha_removal_confirmed(top, done):
    """Is a ronsha's top-level katakana `top` safe to remove, given that its P460
    entry's ojp-hani official name carries the kana qualifier `done`?

    Only when `done` is PRECISELY `top` + カミノヤシロ. A merely suffixed qualifier
    is not enough: three of the fifteen 論社 point at an entry carrying a DIFFERENT
    entry's reading (阿須伎神社 アスキノ against the ronsha's -アメワカヒコノ, and two
    more), because their own reading belongs to a 同社坐 sub-entry with no item of
    its own. A loose STRENDS check would read those as confirmed and delete a
    reading that exists nowhere else.
    """
    return is_katakana(top) and done == top + SUFFIX


def main():
    print("=== Generate カミノヤシロ kana-qualifier REMOVE QuickStatements (no direct edits) ===\n")

    # Only statements that ALREADY have a カミノヤシロ qualifier (confirmed). Pull
    # the confirmed value plus any sibling raw qualifier and any top-level P1814.
    q = f"""
    SELECT ?item ?on ?done ?sibling ?top WHERE {{
      ?item p:P1448 ?st .
      ?st ps:P1448 ?on . FILTER(LANG(?on) = "{OJP}")
      ?st pq:P1814 ?done . FILTER(STRENDS(STR(?done), "{SUFFIX}"))
      OPTIONAL {{ ?st pq:P1814 ?sibling . FILTER(!STRENDS(STR(?sibling), "{SUFFIX}")) }}
      OPTIONAL {{
        ?item p:P1814 ?ts . ?ts ps:P1814 ?top .
        # Only expose the top-level for removal once EVERY ojp-hani P1448 name on
        # the item already carries a カミノヤシロ qualifier — i.e. no name still
        # depends on this top-level as its add source. Guards the multi-name case.
        FILTER NOT EXISTS {{
          ?item p:P1448 ?st2 . ?st2 ps:P1448 ?on2 . FILTER(LANG(?on2) = "{OJP}")
          FILTER NOT EXISTS {{ ?st2 pq:P1814 ?q2 . FILTER(STRENDS(STR(?q2), "{SUFFIX}")) }}
        }}
      }}
    }}
    """
    print("Querying REMOVE candidates (カミノヤシロ qualifier confirmed present)...")
    rows = fetch_sparql(q) or []
    lines = []
    seen = set()
    for r in rows:
        item = qid(r["item"]["value"])
        on = r["on"]["value"]
        base = r["done"]["value"][: -len(SUFFIX)]   # e.g. エノカミノヤシロ -> エノ
        if not base:
            continue
        # ⛔ THE SIBLING-QUALIFIER REMOVAL IS NOT EMITTED — see the module docstring.
        # `-<item>|P1448|<name>|P1814|<sib>` does not remove the sibling qualifier; it
        # removes the whole P1448 official-name statement. Kept unemitted rather than
        # deleted so the SPARQL still binds ?sibling and the shape is documented where
        # it used to fire.
        top = r.get("top", {}).get("value")
        if top and top == base and is_katakana(top):
            key = ("t", item, top)
            if key not in seen:
                seen.add(key)
                lines.append(f'-{item}|P1814|{s(top)}')

    # RONSHA: the mirror of the add generator's P460 branch. A Shikinai Ronsha
    # holds the Engishiki entry's katakana reading as a top-level P1814 while the
    # ojp-hani official name lives on the entry item it points at with P460. Once
    # that entry's name carries `<this exact reading>カミノヤシロ`, the top-level
    # copy on the ronsha is redundant in exactly the same way SEED's is, and this
    # removes it.
    #
    # The confirmation is an EXACT value match in the SPARQL itself -- the entry
    # must carry this ronsha's reading plus the suffix, not merely some suffixed
    # qualifier -- so the reading provably still exists elsewhere before the copy
    # goes. Under the drip's random order the remove can never precede the add.
    #
    # This is a whole-statement removal of a top-level P1814, which QuickStatements
    # expresses correctly. It is NOT the qualifier removal that destroyed four
    # ojp-hani official names on 2026-09-09 (see the module docstring).
    # The exact-value comparison is done in PYTHON, not in the SPARQL. Expressing it
    # as FILTER(STR(?done) = CONCAT(STR(?top), "カミノヤシロ")) made Blazegraph compute
    # a string concat per candidate row and the query returned 504 Gateway Timeout
    # (2026-09-10). The confirmation is just as strict either way -- a removal is
    # still only emitted when the entry carries this ronsha's reading plus the
    # suffix -- and the query stays cheap.
    # Driven from the ENTRY side, which is the small one. Starting at
    # `?ronsha p:P1814 ?ts` walks every P1814 statement on Wikidata before any
    # join can prune it, and that ordering returned 504 Gateway Timeout twice on
    # 2026-09-10. The relocated qualifiers (ojp-hani official names already
    # carrying a カミノヤシロ reading) are a few thousand rows, so binding those
    # first and then following P460 backwards keeps the query small.
    ronsha_q = f"""
    SELECT ?ronsha ?top ?done WHERE {{
      ?entry p:P1448 ?st .
      ?st ps:P1448 ?on . FILTER(LANG(?on) = "{OJP}")
      ?st pq:P1814 ?done . FILTER(STRENDS(STR(?done), "{SUFFIX}"))
      ?ronsha wdt:P460 ?entry ; wdt:P1814 ?top .
      FILTER NOT EXISTS {{
        ?ronsha p:P1448 ?rs . ?rs ps:P1448 ?ron . FILTER(LANG(?ron) = "{OJP}")
      }}
    }}
    """
    print("Querying RONSHA removals (entry carries this exact reading + suffix)...")
    rows = fetch_sparql(ronsha_q) or []
    n_ronsha = 0
    for r in rows:
        top = r["top"]["value"]
        if not ronsha_removal_confirmed(top, r["done"]["value"]):
            continue
        key = ("r", qid(r["ronsha"]["value"]), top)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f'-{qid(r["ronsha"]["value"])}|P1814|{s(top)}')
        n_ronsha += 1
    print(f"  {n_ronsha} ronsha removal lines")

    with open(REMOVE_FILE, "w", encoding="utf-8") as f:
        # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not stable, so
        # emitting in result order reshuffled this file on every build — 49, 156 and 123
        # lines on three consecutive regenerations, each an identical set in a new order.
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    print(f"Wrote {len(lines)} lines to {REMOVE_FILE} (0 is normal until adds have landed)")


if __name__ == "__main__":
    # Rebound here rather than at import time (same as submit_daily_batch.py):
    # at module level it replaced pytest's captured stdout, and every test that
    # imported this module died in teardown with "I/O operation on closed file".
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
