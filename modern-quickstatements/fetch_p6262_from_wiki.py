"""
Fetch P6262 QuickStatements lines from the shintowiki wiki page.

Reads [[QuickStatements/P6262]] (public, no auth needed), filters out
items that already have a P6262 claim on Wikidata or are Wikidata
redirects, and writes the remaining QS lines to a local file for
submission by submit_daily_batch.py.

Mirror of fetch_p11250_from_wiki.py — same flow, different property.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.qs_value import qs_escape, qs_parse_value
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
import io
import re
import sys
import time
import requests
from shinto_miraheze.wd_pace import wd_pace

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
SPARQL_URL = "https://query-main.wikidata.org/sparql"
PAGE_TITLE = "QuickStatements/P6262"
OUTPUT_FILE = "p6262_fandom_links.txt"
QS_LINE_RE = re.compile(r'^(Q\d+)\|P6262\|"(shinto:.+)"$')


def fetch_redirect_qids(qids):
    """Return the subset of QIDs that are redirects on Wikidata."""
    redirects = set()
    qid_list = sorted(qids)
    for i in range(0, len(qid_list), 50):
        batch = qid_list[i : i + 50]
        try:
            wd_pace()          # one Wikidata request per call site, paced
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


def fetch_existing_p6262_qids():
    """Query Wikidata SPARQL for all items that already have P6262.

    Returns a set of QIDs, or None if the query fails (caller must
    treat None as 'cannot safely deduplicate — write nothing').
    """
    query = "SELECT ?item WHERE { ?item wdt:P6262 ?val . }"
    try:
        wd_pace()          # one Wikidata request per call site, paced
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
        print(f"SPARQL: {len(qids)} items already have P6262")
        return qids
    except Exception as e:
        print(f"ERROR: SPARQL query failed ({e}) — cannot deduplicate, writing empty file")
        return None


def main():
    print(f"Fetching [[{PAGE_TITLE}]] from shintowiki...")
    wd_pace()          # one Wikidata request per call site, paced
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
    # If the wiki page doesn't exist yet (first run after deploy), the
    # parse API returns an `error` object instead of `parse`. Treat that
    # as "no QS lines to fetch".
    if "error" in data:
        print(f"WARNING: parse API error ({data['error'].get('code')}); "
              f"page may not exist yet — writing empty file")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        return
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

    # Lines are re-rendered through the escape pair rather than copied verbatim. This is
    # the corpus entry point: whatever is on the page lands in an atomic file, and from
    # there in the daily drip and the emergency batch. Q123999885 sat on the page at
    # 1,048,623 characters — escape applied 19 times to
    # `shinto:List of Kofun in Japan with the Name "Hyō"` — and the 2026-09-04 fix does
    # not reach it: that repair re-derives a preserved line from duplicate_qids.state,
    # which does not know this QID, because its page is missing on miraheze. Which is the
    # same reason it ran away in the first place. Parsing here bounds the damage to the
    # wiki page instead of letting it into the corpus, and takes effect on the next fetch
    # rather than waiting on the Miraheze lockout to lift.
    p6262_lines = []
    repaired = 0
    for line in wikitext.split("\n"):
        line = line.strip()
        m = QS_LINE_RE.match(line)
        if m:
            rendered = '{}|P6262|"{}"'.format(m.group(1), qs_escape(qs_parse_value(m.group(2))))
            if rendered != line:
                repaired += 1
                print(f"repaired {m.group(1)}: {len(line)} -> {len(rendered)} chars")
            p6262_lines.append(rendered)

    print(f"Found {len(p6262_lines)} P6262 lines on wiki page ({repaired} repaired)")

    existing_qids = fetch_existing_p6262_qids()
    if existing_qids is None:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        print("Wrote 0 QS lines to avoid duplicate submissions")
        return

    candidate_qids = {QS_LINE_RE.match(line).group(1) for line in p6262_lines}
    redirect_qids = fetch_redirect_qids(candidate_qids)
    if redirect_qids:
        print(f"Filtered out {len(redirect_qids)} redirect QIDs")

    lines = []
    skipped_existing = 0
    skipped_redirect = 0
    for line in p6262_lines:
        qid = QS_LINE_RE.match(line).group(1)
        if qid in redirect_qids:
            skipped_redirect += 1
        elif qid in existing_qids:
            skipped_existing += 1
        else:
            lines.append(line)

    if skipped_existing:
        print(f"Filtered out {skipped_existing} items that already have P6262")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} QS lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
