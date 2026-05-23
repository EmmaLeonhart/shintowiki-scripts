"""
generate_shrines_missing_en_label.py
====================================
Produce a synced worklist of every Shinto shrine (P31 = Q845945) on Wikidata
that has a Japanese label but NO English label. Output is a JSON file the daily
translation feed (a LOCAL cron) consumes one item at a time: it translates the
Japanese label to English using the name-in-kana reading and appends an
``Qxxx|Len|"..."`` line to ``en_labels.txt`` for the daily QuickStatements
submission to pick up.

Run by ``.github/workflows/generate-shrines-missing-en-label.yml`` every 24h,
which commits the refreshed JSON. The list naturally shrinks as labels land on
Wikidata (the next refresh drops items that gained an en label).

Output: ``shrines_missing_en_label.json`` (alongside this script):
    {"generated_at": "...Z", "count": N,
     "items": [{"qid": "Q123", "ja": "四所神社", "kana": "ししょじんじゃ"}, ...]}
"""

import io
import json
import sys
import time
from datetime import datetime, timezone

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SHINTO_SHRINE = "Q845945"
OUTPUT_FILE = "shrines_missing_en_label.json"


class RateLimitError(Exception):
    """Raised on HTTP 429 — Wikidata/SPARQL scripts bail immediately, no retries."""


def fetch_sparql(query, retries=3):
    """Run a SPARQL query with retry on timeout; bail immediately on 429."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=180,
            )
            if r.status_code == 429:
                print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
                raise RateLimitError("429 Too Many Requests")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except requests.exceptions.ReadTimeout:
            print(f"SPARQL timeout (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(10 * attempt)
            else:
                print("SPARQL endpoint timed out after all retries — exiting gracefully")
                return None


def main():
    # Shinto shrines with a ja label but no en label, plus the kana reading
    # (P1814) when present — the daily feed needs the kana to romanize/translate.
    query = f"""
    SELECT ?item ?ja ?kana WHERE {{
      ?item wdt:P31 wd:{SHINTO_SHRINE} .
      ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja")
      FILTER NOT EXISTS {{ ?item rdfs:label ?en . FILTER(LANG(?en) = "en") }}
      OPTIONAL {{ ?item wdt:P1814 ?kana . }}
    }}
    ORDER BY ?item
    """
    print("Querying Wikidata for Shinto shrines missing an English label...")
    rows = fetch_sparql(query)
    if rows is None:
        print("No results (timeout) — leaving existing list untouched.")
        return

    # One row per (item, kana); collapse to one entry per item, keeping the
    # first kana reading seen (items may have multiple P1814 values).
    items = {}
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        ja = r["ja"]["value"]
        kana = r.get("kana", {}).get("value", "")
        if qid not in items:
            items[qid] = {"qid": qid, "ja": ja, "kana": kana}
        elif kana and not items[qid]["kana"]:
            items[qid]["kana"] = kana

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(items),
        "items": list(items.values()),
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    with_kana = sum(1 for i in items.values() if i["kana"])
    print(f"Wrote {len(items)} shrines to {OUTPUT_FILE} ({with_kana} have a kana reading)")


if __name__ == "__main__":
    main()
