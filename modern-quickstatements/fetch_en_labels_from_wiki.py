"""
Fetch en-label QuickStatements lines from the shintowiki wiki page.

Reads [[QuickStatements/En labels]] (public, no auth needed), filters
out items whose en label is now set on Wikidata or that are now
Wikidata redirects, and writes the remaining QS lines to
en_labels.txt for submission by submit_daily_batch.py /
direct_daily_edits.py.

Mirror of fetch_p11250_from_wiki.py / fetch_p6262_from_wiki.py — same
flow, but the dedup query is "items with any en label" instead of
"items with the property".
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import io
import re
import sys
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
PAGE_TITLE = "QuickStatements/En labels"
OUTPUT_FILE = "en_labels.txt"
QS_LINE_RE = re.compile(r'^(Q\d+)\|Len\|".+"$')

WD_API = "https://www.wikidata.org/w/api.php"


def fetch_en_label_state(qids):
    """Batch-query Wikidata for the en label and redirect-status of each
    QID. Returns ``{qid: (has_en_label: bool, is_redirect: bool)}`` for
    every QID we successfully fetched. QIDs whose batch failed are
    omitted — caller treats absence as "unknown, keep the line".
    """
    out = {}
    qid_list = sorted(qids)
    for i in range(0, len(qid_list), 50):
        batch = qid_list[i : i + 50]
        try:
            resp = requests.get(
                WD_API,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(batch),
                    "props": "labels|info",
                    "languages": "en",
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            if resp.status_code == 429:
                print("WARNING: Wikidata 429 — aborting label fetch")
                return None
            resp.raise_for_status()
            entities = resp.json().get("entities", {})
        except Exception as e:
            print(f"WARNING: en-label batch failed ({batch[0]}..): {e}")
            continue

        for qid in batch:
            entity = entities.get(qid, {})
            if "missing" in entity:
                # Treat missing as "skip the line" — Wikidata doesn't
                # have this item anymore.
                out[qid] = (True, True)
                continue
            is_redirect = "redirects" in entity
            labels = entity.get("labels", {})
            en_label = (labels.get("en", {}) or {}).get("value", "").strip()
            out[qid] = (bool(en_label), is_redirect)
        time.sleep(0.3)
    return out


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
    if "error" in data:
        print(f"WARNING: parse API error ({data['error'].get('code')}); "
              f"page may not exist yet — writing empty file")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        return
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

    en_lines = []
    for line in wikitext.split("\n"):
        line = line.strip()
        if QS_LINE_RE.match(line):
            en_lines.append(line)

    print(f"Found {len(en_lines)} Len lines on wiki page")

    candidate_qids = {QS_LINE_RE.match(line).group(1) for line in en_lines}
    label_state = fetch_en_label_state(candidate_qids)
    if label_state is None:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        print("Wrote 0 QS lines to avoid duplicate submissions")
        return

    lines = []
    skipped_existing = skipped_redirect = 0
    for line in en_lines:
        qid = QS_LINE_RE.match(line).group(1)
        state = label_state.get(qid)
        if state is None:
            # Fetch failed for this batch — keep the line, we'll re-check next run.
            lines.append(line)
            continue
        has_en_label, is_redirect = state
        if is_redirect:
            skipped_redirect += 1
            continue
        if has_en_label:
            skipped_existing += 1
            continue
        lines.append(line)

    if skipped_existing:
        print(f"Filtered out {skipped_existing} items that now have en labels")
    if skipped_redirect:
        print(f"Filtered out {skipped_redirect} redirect QIDs")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} QS lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
