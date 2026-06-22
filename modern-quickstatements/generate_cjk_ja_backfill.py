"""
generate_cjk_ja_backfill.py — C1: backfill the Japanese label of shrines that
have none but carry a CJK-ideographic name in a Chinese (zh-family) label.

Shinto shrines without a ja label are weird edge cases (mostly Taiwan-era
shrines labelled only in Chinese). Per the agenda we just copy the CJK name onto
the ja label — CJK ideographs are shared, so the Chinese label is a usable ja
label. Guarded so ONLY genuine CJK-ideographic labels are copied (never hangul
or Latin), and skip anything with a quote.

Emits ``Qxxx|Lja|"<name>"`` to ``cjk_ja_backfill.txt`` (in
``submit_daily_batch.ATOMIC_FILES``). Tiny set (≈3 today); grows slowly.

Usage:
    python generate_cjk_ja_backfill.py            # write the .txt
    python generate_cjk_ja_backfill.py --stats    # query + report only
"""

import argparse
import io
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(HERE, "cjk_ja_backfill.txt")
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SHINTO_SHRINE = "Q845945"
TRANSIENT_STATUS = (500, 502, 503, 504)


class RateLimitError(Exception):
    """HTTP 429 — bail immediately (repo policy)."""


def _is_cjk_char(ch):
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF      # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF   # Extension A
        or 0xF900 <= cp <= 0xFAFF   # Compatibility Ideographs
        or ch in "々〆ヶ"            # iteration / abbreviation marks used in JA names
    )


def is_cjk_ideographic(s):
    """True iff s is non-empty and every character is a CJK ideograph (a clean
    label safe to copy onto a ja label — no spaces, Latin, or hangul)."""
    return bool(s) and all(_is_cjk_char(c) for c in s)


def lines_for(qid, label):
    """A single Lja QuickStatement, or [] if the label isn't clean CJK."""
    if not is_cjk_ideographic(label) or '"' in label:
        return []
    return [f'{qid}|Lja|"{label}"']


def fetch_rows(retries=3):
    """Shrines with NO ja label but a zh-family label. Returns [(qid, label)]
    (first zh-family label per item), or None if the endpoint stayed down."""
    query = f"""
    SELECT ?item ?lab WHERE {{
      ?item wdt:P31/wdt:P279* wd:{SHINTO_SHRINE} .
      ?item rdfs:label ?lab . FILTER(STRSTARTS(LANG(?lab), "zh"))
      FILTER NOT EXISTS {{ ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja") }}
    }}
    ORDER BY ?item
    """
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(
                SPARQL_ENDPOINT,
                data={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=120,
            )
            if r.status_code == 429:
                print("FATAL: 429 from SPARQL endpoint — bailing")
                raise RateLimitError("429")
            if r.status_code in TRANSIENT_STATUS:
                if attempt < retries:
                    time.sleep(10 * attempt)
                    continue
                return None
            r.raise_for_status()
            rows = r.json()["results"]["bindings"]
            break
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            if attempt < retries:
                time.sleep(10 * attempt)
            else:
                return None
    # first zh-family label per item
    out, seen = [], set()
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        if qid in seen:
            continue
        seen.add(qid)
        out.append((qid, b["lab"]["value"]))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Query + report, write nothing.")
    args = ap.parse_args()

    rows = fetch_rows()
    if rows is None:
        print("SPARQL unavailable — leaving existing output untouched.")
        return

    all_lines = []
    for qid, label in rows:
        all_lines.extend(lines_for(qid, label))
    print(f"Shrines with a zh label but no ja: {len(rows)}; "
          f"emitting {len(all_lines)} Lja backfills.")

    if args.stats:
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))
        if all_lines:
            f.write("\n")
    print(f"Wrote {os.path.basename(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
