"""
Fetch P11250 QuickStatements lines from the shintowiki wiki page.

Reads [[QuickStatements/P11250]] (public, no auth needed), filters out
items that already have a P11250 claim on Wikidata (P11250 lines only)
or are Wikidata redirects (all lines), and writes the remaining QS lines
to a local file for submission by submit_daily_batch.py.

The wiki page may also contain ``Qxxx|Len|"..."`` label-set lines emitted
by ``generate_p11250_quickstatements.py`` for items missing an English
label. Those pass through unchanged (no P11250-presence dedup applies).
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
import io
import re
import sys
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
SPARQL_URL = "https://query-main.wikidata.org/sparql"
PAGE_TITLE = "QuickStatements/P11250"
OUTPUT_FILE = "p11250_miraheze_links.txt"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:.+"$')
QS_LABEL_RE = re.compile(r'^(Q\d+)\|Len\|".+"$')


def fetch_redirect_qids(qids):
    """Return the subset of QIDs that are redirects on Wikidata.

    Items that have been merged become redirects. `direct_daily_edits.py`
    blows up on those with 'entity ID refers to a redirect' because the
    Wikidata API refuses to add statements to a redirect. We filter them
    here so they never reach the submission pipeline.
    """
    redirects = set()
    qid_list = sorted(qids)
    for i in range(0, len(qid_list), 50):
        batch = qid_list[i : i + 50]
        try:
            resp = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(batch),
                    "props": "info",
                    "format": "json",
                },
                headers={"User-Agent": ua_for("https://www.wikidata.org/w/api.php")},
                timeout=30,
            )
            resp.raise_for_status()
            entities = resp.json().get("entities", {})
            for qid, entity in entities.items():
                if "redirects" in entity:
                    redirects.add(qid)
        except Exception as e:
            print(f"WARNING: redirect check failed for batch {batch[0]}..: {e}")
    return redirects


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
            headers={"User-Agent": ua_for(SPARQL_URL)},
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
        headers={"User-Agent": ua_for(WIKI_API)},
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

    p11250_lines = []
    label_lines = []
    for line in wikitext.split("\n"):
        line = line.strip()
        if QS_LINE_RE.match(line):
            p11250_lines.append(line)
        elif QS_LABEL_RE.match(line):
            label_lines.append(line)

    print(f"Found {len(p11250_lines)} P11250 lines and {len(label_lines)} Len lines on wiki page")

    # Filter out items that already have P11250 on Wikidata (only applies
    # to P11250 lines — Len lines are independent of P11250 presence).
    existing_qids = fetch_existing_p11250_qids()
    if existing_qids is None:
        # SPARQL failed — fail closed: write nothing to prevent duplicates
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        print("Wrote 0 QS lines to avoid duplicate submissions")
        return

    candidate_qids = (
        {QS_LINE_RE.match(line).group(1) for line in p11250_lines}
        | {QS_LABEL_RE.match(line).group(1) for line in label_lines}
    )
    redirect_qids = fetch_redirect_qids(candidate_qids)
    if redirect_qids:
        print(f"Filtered out {len(redirect_qids)} redirect QIDs")

    lines = []
    skipped_existing = 0
    skipped_redirect = 0
    for line in p11250_lines:
        qid = QS_LINE_RE.match(line).group(1)
        if qid in redirect_qids:
            skipped_redirect += 1
        elif qid in existing_qids:
            skipped_existing += 1
        else:
            lines.append(line)

    label_kept = 0
    for line in label_lines:
        qid = QS_LABEL_RE.match(line).group(1)
        if qid in redirect_qids:
            skipped_redirect += 1
        else:
            lines.append(line)
            label_kept += 1

    if skipped_existing:
        print(f"Filtered out {skipped_existing} items that already have P11250")
    if label_kept:
        print(f"Kept {label_kept} Len lines (no P11250-presence dedup applied)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} QS lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
