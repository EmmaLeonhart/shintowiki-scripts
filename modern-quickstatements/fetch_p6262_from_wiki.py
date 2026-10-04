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
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
import io
import re
import sys
import time
import requests
from shinto_miraheze.wd_pace import wd_pace
from wiki_link_state_fallback import state_fallback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
SPARQL_URL = "https://query-main.wikidata.org/sparql"
PAGE_TITLE = "QuickStatements/P6262"
OUTPUT_FILE = "p6262_fandom_links.txt"
# Category: and Template: pages are not linked (Emma, 2026-09-27: "Strip both"). They were
# 63% of the Miraheze lines and 26% of the Fandom ones; only article links are wanted.
# Emma, 2026-10-03: never stage these. Q123999885's title has a quote mark, and the wiki round
# trip escaped it into a 1 MB line of backslashes. She added its Fandom link by hand.
BLACKLIST = {"Q123999885"}
QS_LINE_RE = re.compile(r'^(Q\d+)\|P6262\|"shinto:(?!(?:Category|Template):).+"$')


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
    if "--no-wiki" in sys.argv:
        # The wiki-editing lockout means zero Miraheze requests: go straight to the
        # title map the wiki page is rendered from.
        print("--no-wiki: skipping the wiki page, topping up from duplicate_qids.state")
        state_fallback("P6262", QS_LINE_RE, OUTPUT_FILE, fetch_existing_p6262_qids(), fetch_redirect_qids)
        return
    print(f"Fetching [[{PAGE_TITLE}]] from shintowiki...")
    wd_pace()          # one Wikidata request per call site, paced
    try:
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
    except requests.RequestException as e:
        print(f"WARNING: wiki unreachable ({e}) — falling back to duplicate_qids.state")
        state_fallback("P6262", QS_LINE_RE, OUTPUT_FILE, fetch_existing_p6262_qids(), fetch_redirect_qids)
        return
    if resp.status_code != 200:
        # 403 (Miraheze blocks the Actions runners), 429, anything else: the page is
        # unreadable, so top up from the title map it is rendered from.
        print(f"WARNING: wiki returned HTTP {resp.status_code} — falling back to duplicate_qids.state")
        state_fallback("P6262", QS_LINE_RE, OUTPUT_FILE, fetch_existing_p6262_qids(), fetch_redirect_qids)
        return

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

    p6262_lines = []
    for line in wikitext.split("\n"):
        line = line.strip()
        m = QS_LINE_RE.match(line)
        if m and m.group(1) not in BLACKLIST:
            p6262_lines.append(line)

    print(f"Found {len(p6262_lines)} P6262 lines on wiki page")

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
