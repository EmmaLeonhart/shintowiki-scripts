#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
from urllib.parse import urlparse

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WDQS_ENDPOINT = "https://query.wikidata.org/sparql"

# -------------------------
# CONFIG – EDIT THESE
# -------------------------
USERNAME = "Immanuelle@ImmanuelleMisc"        # <-- put your bot username
PASSWORD = "030akvvhf8b3f6fg7mpt85fo8rvp6d58"    # <-- put your bot password

DRY_RUN = False                     # True = do not remove, just print
BATCH_SIZE_GUIDS = 50               # wbremoveclaims supports multiple GUIDs separated by '|'
SPARQL_LIMIT = 5000                 # How many statement rows to fetch per WDQS page
MAX_RETRIES = 6                     # API retry attempts
USER_AGENT = "RemoveP1343Kokugakuin/1.0 (contact: you@example.com)"

EDIT_SUMMARY = (
    "Remove P1343 = Kokugakuin University Shrine database (new) (Q135159299) "
    "from main statements (includes any qualifiers/references on those statements)."
)

# Respect the servers
SLEEP_BETWEEN_WDQS_PAGES = 1.5
SLEEP_BETWEEN_EDIT_BATCHES = 0.8
MAXLAG = "5"  # be kind to replicas

# -------------------------
# Helpers
# -------------------------

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

def req_with_retry(method, url, **kwargs):
    """HTTP with retry & simple backoff; also retry if maxlag error occurs."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.request(method, url, timeout=60, **kwargs)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2 ** attempt / 2.0)
            continue

        # Handle 5xx
        if resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                resp.raise_for_status()
            time.sleep(2 ** attempt / 2.0)
            continue

        # Check for maxlag in MediaWiki API responses
        if "application/json" in resp.headers.get("Content-Type", "") and url == WIKIDATA_API:
            data = None
            try:
                data = resp.json()
            except Exception:
                pass
            if isinstance(data, dict) and "error" in data and data["error"].get("code") == "maxlag":
                # Backoff, then retry
                if attempt == MAX_RETRIES:
                    return resp  # let caller handle
                time.sleep(2 ** attempt)
                continue

        return resp

    return resp

def login(username, password):
    # Step 1: get login token
    params = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    }
    r = req_with_retry("GET", WIKIDATA_API, params=params)
    r.raise_for_status()
    login_token = r.json()["query"]["tokens"]["logintoken"]

    # Step 2: post login
    data = {
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "lgtoken": login_token,
        "format": "json"
    }
    r = req_with_retry("POST", WIKIDATA_API, data=data)
    r.raise_for_status()
    j = r.json()
    if j.get("login", {}).get("result") != "Success":
        raise RuntimeError(f"Login failed: {j}")

def get_csrf_token():
    params = {"action": "query", "meta": "tokens", "type": "csrf", "format": "json"}
    r = req_with_retry("GET", WIKIDATA_API, params=params)
    r.raise_for_status()
    return r.json()["query"]["tokens"]["csrftoken"]

def statement_iri_to_guid(statement_iri: str) -> str:
    """
    Convert RDF statement IRI like:
      http://www.wikidata.org/entity/statement/Q42-54AEEF4F-...
    into MediaWiki GUID:
      Q42$54AEEF4F-...
    """
    # keep only path after /entity/statement/
    path = urlparse(statement_iri).path
    # path looks like "/entity/statement/Q42-UUID"
    local = path.split("/")[-1]
    # RDF uses '-', API wants '$' between Qid and UUID
    if "-" not in local:
        raise ValueError(f"Unexpected statement IRI form: {statement_iri}")
    qid, uuid = local.split("-", 1)
    return f"{qid}${uuid}"

def fetch_statement_page(offset: int, limit: int):
    """
    Return list of dicts: [{"item": "Qxxx", "statement": "http://.../Qxxx-UUID"}]
    """
    sparql = f"""
SELECT ?item ?statement WHERE {{
  ?item p:P1343 ?statement .
  ?statement ps:P1343 wd:Q135159299 .
}}
LIMIT {limit}
OFFSET {offset}
"""
    headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
    r = req_with_retry("POST", WDQS_ENDPOINT, data={"query": sparql}, headers=headers)
    r.raise_for_status()
    data = r.json()
    out = []
    for b in data.get("results", {}).get("bindings", []):
        item = b["item"]["value"].rsplit("/", 1)[-1]
        statement = b["statement"]["value"]
        out.append({"item": item, "statement": statement})
    return out

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def remove_claims(guids, csrf_token):
    """
    Call wbremoveclaims with up to 50 GUIDs.
    """
    claims_param = "|".join(guids)
    data = {
        "action": "wbremoveclaims",
        "format": "json",
        "claim": claims_param,
        "token": csrf_token,
        "summary": EDIT_SUMMARY,
        "assert": "bot",
        "maxlag": MAXLAG,
        "bot": "1"
    }
    r = req_with_retry("POST", WIKIDATA_API, data=data)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"wbremoveclaims error: {j['error']}")
    return j

def main():
    print("Logging in...")
    login(USERNAME, PASSWORD)
    csrf = get_csrf_token()
    print("Got CSRF token.")

    total_removed = 0
    page = 0
    offset = 0

    while True:
        print(f"Querying WDQS page {page} (offset {offset}) ...")
        rows = fetch_statement_page(offset, SPARQL_LIMIT)
        if not rows:
            break

        # Prepare GUIDs
        guids = []
        for row in rows:
            guid = statement_iri_to_guid(row["statement"])
            guids.append(guid)

        print(f"  Found {len(guids)} statements on this page.")

        if DRY_RUN:
            for g in guids[:10]:
                print("  [DRY-RUN] would remove:", g)
            if len(guids) > 10:
                print(f"  [DRY-RUN] ... and {len(guids)-10} more on this page")
        else:
            # Remove in batches
            for batch in chunked(guids, BATCH_SIZE_GUIDS):
                try:
                    _ = remove_claims(batch, csrf)
                    total_removed += len(batch)
                    print(f"  Removed {len(batch)} statements. Total so far: {total_removed}")
                except Exception as e:
                    print("  ERROR removing batch:", batch[:2], "...", str(e))
                    # conservative sleep before continuing
                    time.sleep(3)

                time.sleep(SLEEP_BETWEEN_EDIT_BATCHES)

        # Next page
        page += 1
        offset += SPARQL_LIMIT
        time.sleep(SLEEP_BETWEEN_WDQS_PAGES)

    print("Done.")
    if DRY_RUN:
        print("DRY_RUN=True: no edits were made.")
    else:
        print(f"Total statements removed: {total_removed}")

if __name__ == "__main__":
    main()
