#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remove_kokugakuin_p1343.py
──────────────────────────
Remove every main-statement of described by source (P1343) where the value is
Kokugakuin University Shrine database (new) (Q135159299). Deleting a claim
removes any qualifiers/references attached to that claim.

USAGE
─────
  python remove_kokugakuin_p1343.py            # live
  python remove_kokugakuin_p1343.py --dry      # preview only
  python remove_kokugakuin_p1343.py --verbose  # chatty
  python remove_kokugakuin_p1343.py --limit 2  # only 2 WDQS pages (for testing)
"""

import argparse, json, random, time, sys, requests
from requests_toolbelt.utils import dump

# ─── config ─────────────────────────────────────────────────────────
BOT_USER = "Immanuelle@ImmanuelleMisc"          # hard-coded like always
BOT_PASS = "030akvvhf8b3f6fg7mpt85fo8rvp6d58"   # hard-coded like always
WD_USER = BOT_USER
WD_PASS = BOT_PASS

WD_API = "https://www.wikidata.org/w/api.php"
WD_SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "ImmanuelleKokugakuinRemover/0.1 (https://www.wikidata.org/wiki/User:Immanuelle; mailto:immanuelleleonhart@gmail.com)"
}

P1343 = "P1343"
KOKUGAKUIN_NEW = "Q135159299"

# Tuning
WDQS_PAGE_LIMIT = 5000       # rows per WDQS page
BATCH_SIZE = 50              # wbremoveclaims can take multiple GUIDs separated by |
SLEEP_BETWEEN_PAGES = 1.2
SLEEP_BETWEEN_BATCHES = 0.8
MAX_RETRIES = 6
MAXLAG = 10

S = requests.Session()
S.headers.update(HEADERS)
TOKEN = ""

# ─── helpers ────────────────────────────────────────────────────────
def backoff(attempt):
    time.sleep(min(2 ** attempt, 30) + random.random())

def wd_login():
    global TOKEN
    t = S.get(WD_API, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}).json()
    S.post(WD_API, data={
        "action": "login",
        "lgname": WD_USER,
        "lgpassword": WD_PASS,
        "lgtoken": t["query"]["tokens"]["logintoken"],
        "format": "json",
    })
    TOKEN = S.get(WD_API, params={"action": "query", "meta": "tokens", "format": "json"}).json()["query"]["tokens"]["csrftoken"]

def wd_post(data, retries=MAX_RETRIES, verbose=False):
    """
    POST to MediaWiki API with assert=user and bot=1 (ignored if no bot right).
    Retries on maxlag and 5xx.
    """
    base = {"format": "json", "assert": "user", "bot": 1, "token": TOKEN, "maxlag": MAXLAG}
    for attempt in range(1, retries + 1):
        r = S.post(WD_API, data={**base, **data})
        if r.status_code >= 500:
            if attempt == retries:
                return {"error": {"code": f"http-{r.status_code}", "info": r.text}}
            backoff(attempt)
            continue
        try:
            j = r.json()
        except Exception:
            if attempt == retries:
                return {"error": {"code": "invalid-json", "info": r.text[:500]}}
            backoff(attempt)
            continue

        # Handle maxlag
        if "error" in j and j["error"].get("code") == "maxlag":
            if verbose:
                print("  · maxlag → backing off…")
            backoff(attempt)
            continue

        return j
    return {"error": {"code": "exhausted-retries", "info": "gave up"}}

def statement_iri_to_guid(iri: str) -> str:
    """
    Convert RDF statement IRI:
      http://www.wikidata.org/entity/statement/Q42-54AEEF4F-...
    → GUID:
      Q42$54AEEF4F-...
    """
    tail = iri.rsplit("/", 1)[-1]  # "Qxx-UUID"
    if "-" not in tail:
        raise ValueError(f"Unexpected statement IRI: {iri}")
    qid, uuid = tail.split("-", 1)
    return f"{qid}${uuid}"

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ─── WDQS ───────────────────────────────────────────────────────────
def query_statement_page(offset, limit, verbose=False):
    """
    Returns list[dict]: {"item":"Qxxx", "statement":"http://.../Qxxx-UUID"}
    Only main statements (p:P1343) matching wd:Q135159299.
    """
    sparql = f"""
SELECT ?item ?statement WHERE {{
  ?item p:{P1343} ?statement .
  ?statement ps:{P1343} wd:{KOKUGAKUIN_NEW} .
}}
LIMIT {limit}
OFFSET {offset}
"""
    resp = S.post(WD_SPARQL, data={"query": sparql, "format": "json"})
    # Debug dump
    if verbose:
        data_dump = dump.dump_all(resp)
        with open(f"sparql_debug_offset_{offset}.txt", "wb") as f:
            f.write(data_dump)

    if resp.status_code != 200:
        print("⚠️ SPARQL endpoint error:", resp.status_code)
        print(f"Full request/response written to sparql_debug_offset_{offset}.txt")
        raise SystemExit(1)

    j = resp.json()
    out = []
    for b in j.get("results", {}).get("bindings", []):
        item = b["item"]["value"].rsplit("/", 1)[-1]
        stmt = b["statement"]["value"]
        out.append({"item": item, "statement": stmt})
    return out

# ─── remover ────────────────────────────────────────────────────────
def remove_claims_batch(guids, verbose=False):
    """
    Calls wbremoveclaims with up to 50 GUIDs.
    """
    r = wd_post({
        "action": "wbremoveclaims",
        "claim": "|".join(guids),
        "summary": f"Remove {P1343} = {KOKUGAKUIN_NEW} (Kokugakuin University Shrine database (new)) from main statements; claim deletion also removes qualifiers/references.",
    }, verbose=verbose)

    return r

# ─── main ───────────────────────────────────────────────────────────
def main(dry=False, verbose=False, page_limit=None):
    wd_login()

    total_removed = 0
    page = 0
    offset = 0

    while True:
        if page_limit is not None and page >= page_limit:
            break

        if verbose:
            print(f"Querying WDQS page {page} (offset {offset}) …")
        rows = query_statement_page(offset, WDQS_PAGE_LIMIT, verbose=verbose)
        if not rows:
            if verbose:
                print("No more rows.")
            break

        # Convert to GUIDs
        guids = []
        for r in rows:
            try:
                guid = statement_iri_to_guid(r["statement"])
                guids.append(guid)
            except Exception as e:
                if verbose:
                    print("  · skip bad IRI:", r["statement"], "→", e)

        if verbose:
            print(f"  Found {len(guids)} statements on this page.")

        if dry:
            for g in guids[:10]:
                print("DRY → would remove", g)
            if len(guids) > 10:
                print(f"DRY → …and {len(guids)-10} more on this page")
        else:
            for batch in chunked(guids, BATCH_SIZE):
                resp = remove_claims_batch(batch, verbose=verbose)
                if "error" in resp:
                    print("  ERROR:", resp["error"])
                    # soft wait and continue
                    time.sleep(3.0)
                else:
                    n = len(batch)
                    total_removed += n
                    if verbose:
                        print(f"  ✓ removed {n} (total {total_removed})")
                time.sleep(SLEEP_BETWEEN_BATCHES + random.random() * 0.3)

        page += 1
        offset += WDQS_PAGE_LIMIT
        time.sleep(SLEEP_BETWEEN_PAGES + random.random() * 0.3)

    action = "would be removed" if dry else "removed"
    print(f"\n✅ {total_removed} statement(s) {action}.")

# ─── CLI ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="preview only (no edits)")
    ap.add_argument("--verbose", action="store_true", help="print progress")
    ap.add_argument("--limit", type=int, default=None, help="limit number of WDQS pages to process (testing)")
    args = ap.parse_args()
    try:
        main(dry=args.dry, verbose=args.verbose, page_limit=args.limit)
    except KeyboardInterrupt:
        sys.exit("aborted")
