"""
Fetch P11250 QuickStatements lines from the shintowiki wiki page.

Reads [[QuickStatements/P11250]] (public, no auth needed), filters out
items that already have a P11250 claim on Wikidata, and writes the
remaining QS lines to a local file for submission by submit_daily_batch.py.
"""

import io
import re
import sys
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
PAGE_TITLE = "QuickStatements/P11250"
OUTPUT_FILE = "p11250_miraheze_links.txt"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:.+"$')


def fetch_existing_p11250_qids():
    """Query Wikidata SPARQL for all items that already have P11250.

    Returns a set of QIDs, or None if the query fails (caller must
    treat None as 'cannot safely deduplicate — write nothing').
    """
    query = "SELECT ?item WHERE { ?item wdt:P11250 ?val . }"
    try:
        resp = requests.get(
            SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        if resp.status_code == 429:
            print("ERROR: SPARQL 429 — cannot deduplicate, writing empty file")
            return None
        resp.raise_for_status()
        results = resp.json().get("results", {}).get("bindings", [])
        qids = set()
        for r in results:
            uri = r.get("item", {}).get("value", "")
            if "/Q" in uri:
                qids.add(uri.rsplit("/", 1)[-1])
        print(f"SPARQL: {len(qids)} items already have P11250")
        return qids
    except Exception as e:
        print(f"ERROR: SPARQL query failed ({e}) — cannot deduplicate, writing empty file")
        return None


def main():
    print(f"Fetching [[{PAGE_TITLE}]] from shintowiki...")
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page": PAGE_TITLE,
            "prop": "wikitext",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if resp.status_code == 429:
        print("WARNING: 429 Too Many Requests — writing empty file")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        return
    resp.raise_for_status()

    data = resp.json()
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

    all_lines = []
    for line in wikitext.split("\n"):
        line = line.strip()
        if QS_LINE_RE.match(line):
            all_lines.append(line)

    print(f"Found {len(all_lines)} QS lines on wiki page")

    # Filter out items that already have P11250 on Wikidata
    existing_qids = fetch_existing_p11250_qids()
    if existing_qids is None:
        # SPARQL failed — fail closed: write nothing to prevent duplicates
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        print("Wrote 0 QS lines to avoid duplicate submissions")
        return

    lines = []
    skipped = 0
    for line in all_lines:
        m = QS_LINE_RE.match(line)
        qid = m.group(1)
        if qid in existing_qids:
            skipped += 1
        else:
            lines.append(line)

    if skipped:
        print(f"Filtered out {skipped} items that already have P11250")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} QS lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
