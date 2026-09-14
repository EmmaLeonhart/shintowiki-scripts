"""
generate_kana_qualifier_add.py
==============================
Step 1 of the カミノヤシロ kana-qualifier work (Wikidata bot request 2026-02-26):
the ADD generator. GENERATOR ONLY — writes QuickStatements lines into an atomic
.txt file that the single daily QS submitter runs. It NEVER edits Wikidata and
the lines carry NO edit summaries. (CLAUDE.md "Wikidata editing — ONE path only".)

It emits ADD lines that put a `<katakana reading>カミノヤシロ` P1814 qualifier on
Old-Japanese (ojp-hani) P1448 official names:
  * APPEND: the ojp-hani P1448 already has a katakana P1814 qualifier not ending
    in カミノヤシロ → add `<that kana>カミノヤシロ`.
  * MOVE: the item has a top-level katakana P1814 and the ojp-hani P1448 does not
    yet carry THAT reading plus the suffix → add `<that kana>カミノヤシロ`.

This script ONLY adds. The redundant raw katakana (old qualifier / top-level
statement) is removed by the SEPARATE script generate_kana_qualifier_remove.py,
which only acts after a fresh SPARQL query confirms the カミノヤシロ qualifier is
already present. Two separate scripts, add first, remove later — never one action.

⭐ MOVE was SEED until 2026-09-13, and only reached names carrying no P1814
qualifier at all. That left 742 top-level katakana readings unreachable by either
half of this pipeline — APPEND only ever suffixes the qualifier already on a name,
so nothing moved the top-level, and the remove step demands exactly
`<top>カミノヤシロ`, which therefore never appeared. Reported in
`docs/stuck_katakana_readings.md`; Emma ruled *"Move it, then delete"* when given
the choice between relocating those readings and deleting them, and the widened
filter is that ruling. See the comment on the pass for what the readings are and
why a name may legitimately end up with several.

Output: kana_qualifier_add.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import collections
import re
import io
import sys
import time
import requests

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
SUFFIX = "カミノヤシロ"
OJP = "ojp-hani"
ADD_FILE = "kana_qualifier_add.txt"


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
        r.raise_for_status()
        try:
            return r.json()["results"]["bindings"]
        except ValueError as e:
            # A TRUNCATED BODY. WDQS answers 200 and then cuts the response short
            # mid-row; `r.json()` raises requests' JSONDecodeError, a ValueError,
            # and this loop caught only ReadTimeout. On 2026-09-13 that ended a
            # forty-minute sweep at its last language with nothing written, because
            # these generators write their .txt only at the end.
            #
            # The parse sits OUTSIDE the request's try on purpose — the request and
            # the parse fail differently — so it gets its own guard rather than a
            # restructured loop. Purely additive: the success path is untouched and
            # a previously-fatal case now retries on the same backoff.
            if attempt < retries:
                print(f"SPARQL short read (attempt {attempt}/{retries}): {e}")
                time.sleep(10 * attempt)
                continue
            print("SPARQL short read after retries — exiting gracefully")
            return None


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def is_katakana(value):
    """Old-Japanese katakana reading: has katakana, no hiragana."""
    has_hira = any("぀" <= ch <= "ゟ" for ch in value)
    has_kata = any("゠" <= ch <= "ヿ" for ch in value)
    return has_kata and not has_hira


def ml(text):
    """QuickStatements monolingual value for the ojp-hani official name."""
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'{OJP}:"{esc}"'


def s(text):
    """QuickStatements string value."""
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


# Resolved __file__-relative, not cwd-relative (CLAUDE.md): CI sets
# working-directory but a hand-run does not.
_HERE = _uos.path.dirname(_uos.path.abspath(__file__))
REMOVALS_FILE = _uos.path.join(_HERE, "ronsha_ojp_name_removals.txt")


def names_queued_for_removal():
    """{(qid, ojp-hani name)} that `ronsha_ojp_name_removals.txt` is going to delete.

    ⛔ WHY THIS SKIP IS NOT A GUARD THAT BLOCKS THE WORK. A qualifier line here reads

        Q10896675|P1448|ojp-hani:"出雲神社"|P1814|"イツモノカミノヤシロ"

    and `direct_daily_edits.execute_line` does `guid = find_claim(...)` and then, at
    lines 823-825, **creates the claim if it is missing**. So once the ronsha removal
    has deleted that official name, this line does not decorate anything — it
    RE-CREATES the statement the removal deliberately deleted, without its references
    and without its P1264. Both generators re-derive from live Wikidata every build,
    so the removal re-queues, the add re-queues, and the pair oscillates forever at
    two edits a cycle, stripping the statement's sources each time round.

    Measured 2026-09-13: **1,734 items appear in both files** (2,564 (item, property,
    value) triples are staged both ways across all atomic files, and this pair is the
    bulk of them). Sampled 20 of the 1,734 against live Wikidata: every ojp-hani name
    still present, all with references and P1264 — **so nothing has been damaged yet**.
    The removals simply have not reached them. This is a latent collision, closed
    before it fires, not a repair.

    Nothing is lost by skipping: the statement these readings would decorate is the
    one being deleted. The reading belongs on the Engishiki ENTRY item, which is what
    the removal exists to enforce (CLAUDE.md, list membership belongs to the entry
    item).

    The removals file is regenerated at step 128 of `generate-quickstatements.yml` and
    this generator runs at step 260, so the file read here is this run's own output.
    """
    out = set()
    if not _uos.path.exists(REMOVALS_FILE):
        return out
    for line in io.open(REMOVALS_FILE, encoding="utf-8"):
        m = re.match(r'^-(Q\d+)\|P1448\|ojp-hani:"(.*)"$', line.strip())
        if m:
            out.add((m.group(1), m.group(2).replace('\\"', '"')))
    return out


def main():
    # ⛔ INSIDE main(), NOT AT MODULE SCOPE. Rebinding sys.stdout at import
    # replaces pytest's captured stream with a wrapper over a buffer pytest then
    # closes, and every later test in the same PROCESS dies on "I/O operation on
    # closed file" — not just this module's. It poisoned four sibling modules'
    # tests before being traced back here, and it is the fourth time this repo has
    # hit the same thing (build_ronsha_ranking_queue.py was moved for exactly this
    # reason). The rebind is for the CI console's encoding, which only matters when
    # the file is run as a script.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("=== Generate カミノヤシロ kana-qualifier ADD QuickStatements (no direct edits) ===\n")
    lines = []
    doomed = names_queued_for_removal()
    n_doomed = 0
    print(f"{len(doomed)} ojp-hani name(s) queued for removal — not decorating those")

    # APPEND: ojp-hani P1448 with a katakana qualifier not ending in カミノヤシロ,
    # and the statement does NOT already carry a カミノヤシロ qualifier.
    append_q = f"""
    SELECT ?item ?on ?kana WHERE {{
      ?item p:P1448 ?st .
      ?st ps:P1448 ?on ; pq:P1814 ?kana .
      FILTER(LANG(?on) = "{OJP}")
      FILTER(!STRENDS(STR(?kana), "{SUFFIX}"))
      FILTER NOT EXISTS {{ ?st pq:P1814 ?done . FILTER(STRENDS(STR(?done), "{SUFFIX}")) }}
    }}
    """
    print("Querying APPEND candidates (existing katakana qualifier)...")
    rows = fetch_sparql(append_q) or []
    n_app = 0
    for r in rows:
        kana = r["kana"]["value"]
        if not is_katakana(kana):
            continue
        if (qid(r["item"]["value"]), r["on"]["value"]) in doomed:
            n_doomed += 1
            continue
        lines.append(f'{qid(r["item"]["value"])}|P1448|{ml(r["on"]["value"])}|P1814|{s(kana + SUFFIX)}')
        n_app += 1
    print(f"  {n_app} append lines")

    # MOVE: the item holds a top-level katakana P1814 and its ojp-hani P1448 name
    # does not yet carry THAT reading plus カミノヤシロ. Put `<top>カミノヤシロ` on
    # the name; `generate_kana_qualifier_remove.py` then retires the top-level once
    # it confirms the exact value landed. That pair IS "move it, then delete".
    #
    # ⭐ This used to be a narrower SEED pass, gated on the name having NO P1814
    # qualifier at all (`FILTER NOT EXISTS { ?st pq:P1814 ?anyq }`), and that gate
    # is what stranded 742 top-level katakana readings. A name that already carried
    # SOME reading was skipped here, while the APPEND pass above only ever suffixes
    # the qualifier already on the name — so nothing moved the top-level, and the
    # remove step, which demands exactly `<top>カミノヤシロ`, could never fire.
    # Reported 2026-09-11 in docs/stuck_katakana_readings.md; Emma ruled on
    # 2026-09-13, given the choice between moving and deleting them: *"Move it,
    # then delete."* Widening this filter is that ruling — 216 more (item, name,
    # reading) triples, measured the same day, on top of the 509 SEED reached.
    #
    # What those readings are: a top-level katakana here is the Old-Japanese
    # reading of the item's ENGISHIKI name, not of the modern shrine. Q11549570
    # 氷室神社 is read ひむろじんじゃ and carries `タカ-` — the reading of 高橋神社,
    # the name in its P1448. A hyphen marks a portion the source did not read
    # (`アハシマノ-イサハノ` for 粟島坐伊射波神社, the 坐 unread), so the value is a
    # gap-marked partial reading, and the gap survives the move intact.
    #
    # ⚠ Several names per item and several readings per item are both normal and
    # multiply out: Q110915859 is a candidate for four Engishiki entries and
    # carries three ojp-hani names, so all four readings go onto all three names.
    # That is the pre-existing SEED behaviour, not something this widening
    # introduced, and the remove step's per-name guard already accounts for it.
    #
    # The "does the name already have it" test is done in PYTHON. Expressing it as
    # FILTER(STR(?done) = CONCAT(STR(?top), "カミノヤシロ")) works here, but the same
    # construction timed out the remove generator with a 504 on 2026-09-10 and the
    # lesson is recorded there; a cheap OPTIONAL plus a set lookup cannot regress
    # that way. 1,672 rows in 25s, measured 2026-09-13.
    move_q = f"""
    SELECT ?item ?on ?top ?done WHERE {{
      ?item p:P1448 ?st .
      ?st ps:P1448 ?on . FILTER(LANG(?on) = "{OJP}")
      ?item p:P1814 ?ts . ?ts ps:P1814 ?top .
      OPTIONAL {{ ?st pq:P1814 ?done . FILTER(STRENDS(STR(?done), "{SUFFIX}")) }}
    }}
    """
    print("Querying MOVE candidates (top-level katakana not yet on the name)...")
    rows = fetch_sparql(move_q) or []
    tops = collections.defaultdict(set)
    done = collections.defaultdict(set)
    for r in rows:
        key = (qid(r["item"]["value"]), r["on"]["value"])
        tops[key].add(r["top"]["value"])
        if "done" in r:
            done[key].add(r["done"]["value"])
    n_move = n_already = 0
    for (item, on), values in sorted(tops.items()):
        for top in sorted(values):
            if not is_katakana(top):
                continue
            if top + SUFFIX in done[(item, on)]:
                n_already += 1
                continue
            if (item, on) in doomed:
                n_doomed += 1
                continue
            lines.append(f'{item}|P1448|{ml(on)}|P1814|{s(top + SUFFIX)}')
            n_move += 1
    print(f"  {n_move} move lines ({n_already} already on the name)")

    with open(ADD_FILE, "w", encoding="utf-8") as f:
        # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not stable, so
        # emitting in result order rewrote all 3,962 lines of this file every build.
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    print(f"\nWrote {len(lines)} lines to {ADD_FILE} "
          f"({n_doomed} skipped: their ojp-hani name is queued for removal)")


if __name__ == "__main__":
    main()
