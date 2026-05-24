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
  * SEED: the ojp-hani P1448 has NO P1814 qualifier, but the item has a top-level
    katakana P1814 statement → add `<that kana>カミノヤシロ`.

This script ONLY adds. The redundant raw katakana (old qualifier / top-level
statement) is removed by the SEPARATE script generate_kana_qualifier_remove.py,
which only acts after a fresh SPARQL query confirms the カミノヤシロ qualifier is
already present. Two separate scripts, add first, remove later — never one action.

Output: kana_qualifier_add.txt
"""

import io
import sys
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
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
        return r.json()["results"]["bindings"]


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


def main():
    print("=== Generate カミノヤシロ kana-qualifier ADD QuickStatements (no direct edits) ===\n")
    lines = []

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
        lines.append(f'{qid(r["item"]["value"])}|P1448|{ml(r["on"]["value"])}|P1814|{s(kana + SUFFIX)}')
        n_app += 1
    print(f"  {n_app} append lines")

    # SEED: ojp-hani P1448 with NO P1814 qualifier, item has a top-level katakana
    # P1814 statement. Seed `<top>カミノヤシロ` as the qualifier.
    seed_q = f"""
    SELECT ?item ?on ?top WHERE {{
      ?item p:P1448 ?st .
      ?st ps:P1448 ?on . FILTER(LANG(?on) = "{OJP}")
      FILTER NOT EXISTS {{ ?st pq:P1814 ?anyq }}
      ?item p:P1814 ?ts . ?ts ps:P1814 ?top .
    }}
    """
    print("Querying SEED candidates (top-level katakana, no qualifier)...")
    rows = fetch_sparql(seed_q) or []
    n_seed = 0
    seen = set()
    for r in rows:
        top = r["top"]["value"]
        if not is_katakana(top):
            continue
        key = (qid(r["item"]["value"]), r["on"]["value"], top)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f'{qid(r["item"]["value"])}|P1448|{ml(r["on"]["value"])}|P1814|{s(top + SUFFIX)}')
        n_seed += 1
    print(f"  {n_seed} seed lines")

    with open(ADD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"\nWrote {len(lines)} lines to {ADD_FILE}")


if __name__ == "__main__":
    main()
