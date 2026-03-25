"""
test_wikidata_qualifier.py
==========================
Test script: apply a single P459 qualifier to one P13723 statement via the
Wikidata API (wbsetqualifier), bypassing QuickStatements entirely.

Picks the first P13723 statement that lacks a P459 qualifier and adds:
    P459 → Q712534 (modern system of ranked Shinto shrines)

Environment variables:
    MW_BOTNAME  — Wikidata bot-password username (e.g. "EmmaBot@BotName")
    BOT_TOKEN   — Wikidata bot-password token
"""

import json
import os
import sys
import time
import requests

WD_API = "https://www.wikidata.org/w/api.php"
UA = "ShintoShrineQualifierTest/1.0 (User:EmmaBot; shinto.miraheze.org)"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Qualifier to add
QUALIFIER_PROPERTY = "P459"                    # determination method or standard
QUALIFIER_VALUE = "Q712534"                    # modern system of ranked Shinto shrines
TARGET_PROPERTY = "P13723"                     # shrine ranking


def sparql_query(query):
    """Run a SPARQL query against Wikidata."""
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers={"User-Agent": UA},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def find_one_missing_qualifier():
    """Find one P13723 statement that lacks a P459 qualifier.

    Returns (item_qid, rank_value_qid) or None.
    """
    query = """
    SELECT ?item ?rankvalue WHERE {
      ?item p:P13723 ?stmt .
      ?stmt ps:P13723 ?rankvalue .
      FILTER NOT EXISTS { ?stmt pq:P459 ?_ }
    }
    ORDER BY ?item
    LIMIT 1
    """
    results = sparql_query(query)
    if not results:
        print("No P13723 statements without P459 qualifier found.")
        return None

    item = results[0]["item"]["value"].split("/")[-1]
    rankvalue = results[0]["rankvalue"]["value"].split("/")[-1]
    return item, rankvalue


def get_statement_guid(session, item_qid, rank_value_qid):
    """Fetch the entity and find the GUID of the P13723 statement
    whose main value matches rank_value_qid and has no P459 qualifier."""
    r = session.get(
        WD_API,
        params={
            "action": "wbgetentities",
            "ids": item_qid,
            "props": "claims",
            "format": "json",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()

    entity = data.get("entities", {}).get(item_qid, {})
    claims = entity.get("claims", {}).get(TARGET_PROPERTY, [])

    for claim in claims:
        # Check main value matches
        mainsnak = claim.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value":
            continue
        dv = mainsnak.get("datavalue", {})
        if dv.get("type") != "wikibase-entityid":
            continue
        if dv["value"].get("id") != rank_value_qid:
            continue

        # Check no P459 qualifier already present
        qualifiers = claim.get("qualifiers", {})
        if QUALIFIER_PROPERTY in qualifiers:
            continue

        return claim["id"]

    return None


def wd_login():
    """Log in to Wikidata and return (session, csrf_token)."""
    user = os.environ.get("MW_BOTNAME")
    password = os.environ.get("BOT_TOKEN")
    if not user or not password:
        print("ERROR: MW_BOTNAME and BOT_TOKEN environment variables are required.")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    # Step 1: Get login token
    r = session.get(
        WD_API,
        params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
        timeout=60,
    )
    r.raise_for_status()
    login_token = r.json()["query"]["tokens"]["logintoken"]

    # Step 2: Login
    r = session.post(
        WD_API,
        data={
            "action": "login",
            "lgname": user,
            "lgpassword": password,
            "lgtoken": login_token,
            "format": "json",
        },
        timeout=60,
    )
    r.raise_for_status()
    login_result = r.json()
    if login_result.get("login", {}).get("result") != "Success":
        print(f"Login failed: {json.dumps(login_result, indent=2)}")
        sys.exit(1)
    print(f"Logged in as {login_result['login']['lgusername']}")

    # Step 3: Get CSRF token
    r = session.get(
        WD_API,
        params={"action": "query", "meta": "tokens", "format": "json"},
        timeout=60,
    )
    r.raise_for_status()
    csrf = r.json()["query"]["tokens"]["csrftoken"]
    return session, csrf


def set_qualifier(session, csrf, statement_guid, property_id, value_qid):
    """Add a qualifier to an existing statement via wbsetqualifier."""
    snak_value = json.dumps({
        "entity-type": "item",
        "numeric-id": int(value_qid[1:]),  # strip 'Q'
        "id": value_qid,
    })

    r = session.post(
        WD_API,
        data={
            "action": "wbsetqualifier",
            "claim": statement_guid,
            "property": property_id,
            "snaktype": "value",
            "value": snak_value,
            "token": csrf,
            "bot": 1,
            "summary": "adding qualifier",
            "format": "json",
        },
        timeout=60,
    )
    r.raise_for_status()
    result = r.json()

    if "error" in result:
        print(f"API error: {json.dumps(result['error'], indent=2)}")
        return False

    print(f"Success: {json.dumps(result, indent=2)}")
    return True


def main():
    print("=== Wikidata Qualifier Test Edit ===\n")

    # Step 1: Find a target
    print("Step 1: Finding a P13723 statement without P459 qualifier...")
    target = find_one_missing_qualifier()
    if target is None:
        print("Nothing to do — all P13723 statements already have P459 qualifiers.")
        return

    item_qid, rank_value_qid = target
    print(f"  Target: {item_qid} → P13723 → {rank_value_qid}")
    print(f"  https://www.wikidata.org/wiki/{item_qid}")

    # Step 2: Login
    print("\nStep 2: Logging in to Wikidata...")
    session, csrf = wd_login()

    # Step 3: Get the statement GUID
    print("\nStep 3: Fetching statement GUID...")
    guid = get_statement_guid(session, item_qid, rank_value_qid)
    if guid is None:
        print("  Could not find matching statement (may already have qualifier).")
        return
    print(f"  Statement GUID: {guid}")

    # Step 4: Apply the qualifier
    print(f"\nStep 4: Adding {QUALIFIER_PROPERTY} → {QUALIFIER_VALUE} qualifier...")
    success = set_qualifier(session, csrf, guid, QUALIFIER_PROPERTY, QUALIFIER_VALUE)

    if success:
        print(f"\nDone! Check: https://www.wikidata.org/wiki/{item_qid}")
    else:
        print("\nEdit failed — see error above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
