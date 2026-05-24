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

For each ojp-hani P1448 that has a confirmed `<base>カミノヤシロ` qualifier, it
removes the now-redundant raw `<base>` katakana wherever it still sits:
  * as a sibling P1814 qualifier on the same official name, and/or
  * as a top-level P1814 statement on the item.
The modern (hiragana) top-level reading never matches and is left untouched.

Output: kana_redundant_remove.txt
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
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def is_katakana(value):
    has_hira = any("぀" <= ch <= "ゟ" for ch in value)
    has_kata = any("゠" <= ch <= "ヿ" for ch in value)
    return has_kata and not has_hira


def ml(text):
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'{OJP}:"{esc}"'


def s(text):
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


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
      OPTIONAL {{ ?item p:P1814 ?ts . ?ts ps:P1814 ?top . }}
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
        sib = r.get("sibling", {}).get("value")
        if sib and sib == base and is_katakana(sib):
            key = ("q", item, on, sib)
            if key not in seen:
                seen.add(key)
                lines.append(f'-{item}|P1448|{ml(on)}|P1814|{s(sib)}')
        top = r.get("top", {}).get("value")
        if top and top == base and is_katakana(top):
            key = ("t", item, top)
            if key not in seen:
                seen.add(key)
                lines.append(f'-{item}|P1814|{s(top)}')

    with open(REMOVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"Wrote {len(lines)} lines to {REMOVE_FILE} (0 is normal until adds have landed)")


if __name__ == "__main__":
    main()
