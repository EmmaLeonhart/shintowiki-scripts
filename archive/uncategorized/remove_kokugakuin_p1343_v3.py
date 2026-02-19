#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remove_kokugakuin_p1343_v3.py
─────────────────────────────
Remove every main-statement of described by source (P1343) where the value is
Kokugakuin University Shrine database (new) (Q135159299). Deleting a claim
removes any qualifiers/references attached to that claim.

USAGE
  python remove_kokugakuin_p1343_v3.py            # live
  python remove_kokugakuin_p1343_v3.py --dry      # preview only
  python remove_kokugakuin_p1343_v3.py --verbose  # chatty
  python remove_kokugakuin_p1343_v3.py --limit 1  # first WDQS page only
"""

import argparse, re, json, random, time, sys, requests
from requests_toolbelt.utils import dump

# ─── config ─────────────────────────────────────────────────────────
BOT_USER = "Immanuelle@ImmanuelleMisc"          # hard-coded like always
BOT_PASS = "030akvvhf8b3f6fg7mpt85fo8rvp6d58"   # hard-coded like always
WD_USER = BOT_USER
WD_PASS = BOT_PASS

WD_API = "https://www.wikidata.org/w/api.php"
WD_SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "ImmanuelleKokugakuinRemover/0.3 (https://www.wikidata.org/wiki/User:Immanuelle; mailto:immanuelleleonhart@gmail.com)"
}

P1343 = "P1343"
KOKUGAKUIN_NEW = "Q135159299"

WDQS_PAGE_LIMIT = 5000
BATCH_SIZE = 50
SLEEP_BETWEEN_PAGES = 1.2
SLEEP_BETWEEN_BATCHES = 0.8
MAX_RETRIES = 6
MAXLAG = 10

GUID_RE = re.compile(r"^Q\d+\$[0-9A-Fa-f-]+$")

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
    POST with assert=user and bot=1. Retries on maxlag/5xx.
    Accepts dict OR list of tuples (for duplicate keys like multiple 'claim').
    """
    base = [("format","json"), ("assert","user"), ("bot",1), ("token",TOKEN), ("maxlag",MAXLAG)]
    if isinstance(data, dict):
        payload = base + list(data.items())
    else:
        payload = base + list(data)
    for attempt in range(1, retries + 1):
        r = S.post(WD_API, data=payload)
        if r.status_code >= 500:
            if attempt == retries:
                return {"error": {"code": f"http-{r.status_code}", "info": r.text}}
            backoff(attempt); continue
        try:
            j = r.json()
        except Exception:
            if attempt == retries:
                return {"error": {"code": "invalid-json", "info": r.text[:500]}}
            backoff(attempt); continue
        if "error" in j and j["error"].get("code") == "maxlag":
            if verbose: print("  · maxlag → backing off…")
            backoff(attempt); continue
        return j
    return {"error": {"code": "exhausted-retries", "info": "gave up"}}

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# ─── WDQS (GUIDs in SPARQL; Q-items only) ───────────────────────────
def query_statement_page(offset, limit, verbose=False):
    """
    Returns list[str] of GUIDs for main statements P1343 = Q135159299 on Q-items.
    """
    sparql = f"""
SELECT ?guid WHERE {{
  ?item p:{P1343} ?statement .
  ?statement ps:{P1343} wd:{KOKUGAKUIN_NEW} .
  FILTER(STRSTARTS(STR(?item), "http://www.wikidata.org/entity/Q"))
  BIND( STRAFTER(STR(?statement), "/entity/statement/") AS ?local )
  BIND( STRBEFORE(?local, "-") AS ?eid )
  BIND( SUBSTR(?local, STRLEN(?eid) + 2) AS ?uuid )
  BIND( CONCAT(?eid, "$", ?uuid) AS ?guid )
}}
LIMIT {limit}
OFFSET {offset}
"""
    resp = S.post(WD_SPARQL, data={"query": sparql, "format": "json"})
    if verbose:
        data_dump = dump.dump_all(resp)
        with open(f"sparql_debug_offset_{offset}.txt", "wb") as f:
            f.write(data_dump)

    if resp.status_code != 200:
        print("⚠️ SPARQL endpoint error:", resp.status_code)
        print(f"Full request/response written to sparql_debug_offset_{offset}.txt")
        raise SystemExit(1)
    j = resp.json()
    return [b["guid"]["value"] for b in j.get("results", {}).get("bindings", [])]

# ─── sanity: check that a GUID exists ───────────────────────────────
def claim_exists(guid):
    r = wd_post({"action":"wbgetclaims", "claim": guid})
    return "claims" in r

# ─── remover ────────────────────────────────────────────────────────
def remove_claims_batch(guids, verbose=False):
    """
    Calls wbremoveclaims sending multiple 'claim' params (no pipes).
    """
    params = [
        ("action","wbremoveclaims"),
        # one 'claim' per GUID:
    ]
    for g in guids:
        params.append(("claim", g))
    params.append(("summary",
        f"Remove {P1343} = {KOKUGAKUIN_NEW} (Kokugakuin University Shrine database (new)) "
        f"from main statements; claim deletion also removes qualifiers/references."
    ))
    return wd_post(params, verbose=verbose)

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
        guids = query_statement_page(offset, WDQS_PAGE_LIMIT, verbose=verbose)
        if not guids:
            if verbose: print("No more rows.")
            break

        # basic local validation
        good = [g for g in guids if GUID_RE.match(g)]
        bad_local = [g for g in guids if not GUID_RE.match(g)]
        if bad_local and verbose:
            print("  · skipping malformed GUIDs (regex):", bad_local[:5], ("…+" if len(bad_local) > 5 else ""))

        # remote existence check on a small sample to catch systemic issues
        sample = good[:3]
        for g in sample:
            if not claim_exists(g):
                print(f"  ERROR: GUID not found by wbgetclaims → {g}")
                print("         (If this happens for many, WDQS may be ahead/behind or GUID format is wrong.)")
                # Do not abort; continue with others.

        if verbose:
            print(f"  Found {len(good)} valid-looking GUIDs on this page.")
            if good:
                print(f"  Example GUID: {good[0]}")

        if dry:
            for g in good[:10]:
                print("DRY → would remove", g)
            if len(good) > 10:
                print(f"DRY → …and {len(good)-10} more on this page")
        else:
            for batch in chunked(good, BATCH_SIZE):
                resp = remove_claims_batch(batch, verbose=verbose)
                if "error" in resp:
                    err = resp["error"]
                    print("  ERROR:", err)

                    # If invalid-guid, try one-by-one so good ones still go through
                    if err.get("code") == "invalid-guid":
                        for g in batch:
                            r1 = remove_claims_batch([g], verbose=verbose)
                            if "error" in r1:
                                if verbose:
                                    print("    ✗", g, "→", r1["error"])
                            else:
                                total_removed += 1
                                if verbose:
                                    print("    ✓ removed", g, f"(total {total_removed})")
                                time.sleep(SLEEP_BETWEEN_BATCHES + random.random() * 0.2)

                    time.sleep(2.0)  # brief pause after any error
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
    ap.add_argument("--verbose", action="store_true", help="print progress and save WDQS dumps")
    ap.add_argument("--limit", type=int, default=None, help="limit number of WDQS pages to process (testing)")
    args = ap.parse_args()
    try:
        main(dry=args.dry, verbose=args.verbose, page_limit=args.limit)
    except KeyboardInterrupt:
        sys.exit("aborted")
