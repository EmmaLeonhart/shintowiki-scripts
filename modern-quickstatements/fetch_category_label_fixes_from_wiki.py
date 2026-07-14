"""
Fetch category-label-fix QuickStatements lines from the shintowiki wiki page.

Reads [[QuickStatements/Category label fixes]] (public, no auth
needed) — corrective Len lines for the category-prefix bug (labels
applied without the ``Category:`` prefix). Filters out items whose en
label now already starts with ``Category:`` (fixed) or that are now
Wikidata redirects, and writes the remaining QS lines to
category_label_fixes.txt for submission by direct_daily_edits.py.

Mirror of fetch_en_labels_from_wiki.py — same flow, but the drop
condition is "label already carries the prefix" instead of "has any
en label" (these lines OVERWRITE damaged labels, so "has a label" is
exactly the state they exist to change).
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
PAGE_TITLE = "QuickStatements/Category label fixes"
OUTPUT_FILE = "category_label_fixes.txt"
QS_LINE_RE = re.compile(r'^(Q\d+)\|Len\|".+"$')

WD_API = "https://www.wikidata.org/w/api.php"


def fetch_en_label_state(qids):
    """Batch-query Wikidata for the en label and redirect-status of each
    QID. Returns ``{qid: (en_label: str, is_redirect: bool)}`` for every
    QID we successfully fetched (en_label "" when unset). QIDs whose
    batch failed are omitted — caller treats absence as "unknown, keep
    the line". Returns None on 429 (caller writes an empty file)."""
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
            print(f"WARNING: label batch failed ({batch[0]}..): {e}")
            continue

        for qid in batch:
            entity = entities.get(qid, {})
            if "missing" in entity:
                # Item gone from Wikidata — treat as "drop the line".
                out[qid] = ("Category:<missing>", True)
                continue
            is_redirect = "redirects" in entity
            labels = entity.get("labels", {})
            en_label = (labels.get("en", {}) or {}).get("value", "").strip()
            out[qid] = (en_label, is_redirect)
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

    fix_lines = []
    for line in wikitext.split("\n"):
        line = line.strip()
        if QS_LINE_RE.match(line):
            fix_lines.append(line)

    print(f"Found {len(fix_lines)} fix lines on wiki page")

    candidate_qids = {QS_LINE_RE.match(line).group(1) for line in fix_lines}
    label_state = fetch_en_label_state(candidate_qids)
    if label_state is None:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        print("Wrote 0 QS lines to avoid duplicate submissions")
        return

    lines = []
    skipped_fixed = skipped_redirect = 0
    for line in fix_lines:
        qid = QS_LINE_RE.match(line).group(1)
        state = label_state.get(qid)
        if state is None:
            # Fetch failed for this batch — keep the line, re-check next run.
            lines.append(line)
            continue
        en_label, is_redirect = state
        if is_redirect:
            skipped_redirect += 1
            continue
        if en_label.startswith("Category:"):
            skipped_fixed += 1
            continue
        lines.append(line)

    if skipped_fixed:
        print(f"Filtered out {skipped_fixed} items whose label already has the prefix")
    if skipped_redirect:
        print(f"Filtered out {skipped_redirect} redirect/missing QIDs")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} QS lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
