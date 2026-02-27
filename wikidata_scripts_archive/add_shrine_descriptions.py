#!/usr/bin/env python3
"""
add_shrine_descriptions.py
──────────────────────────
Log in to Wikidata and add an English description

    "Shinto shrine in <P131‑label>, Japan"

for every item that

  • is (an instance or subclass instance) of Shinto shrine (Q845945),  
  • has a P131 (located in) value whose English label we can read,  
  • **already has an English label**, and  
  • **has no English description yet**.

USAGE
─────
    python add_shrine_descriptions.py

DEPENDENCIES
────────────
    pip install requests simplejson
"""

import time, requests, simplejson as json
from urllib.parse import quote_plus

# ─────────── USER SETTINGS ──────────────────────────────────────────────
WD_USER = "EmmaBot@EmmaBotMisc"        # bot username
WD_PASS = "030akvvhf8b3f6fg7mpt85fo8rvp6d58"        # hard‑coded as requested
SUMMARY = "Bot: add description → 'Shinto shrine in <place>', applying this only to Shrines already having english labels, to help disambiguate them"
SLEEP   = 1.5                                       # seconds between writes
# ─────────────────────────────────────────────────────────────────────────

SPARQL_URL = "https://query.wikidata.org/sparql"
API_URL    = "https://www.wikidata.org/w/api.php"
HEADERS    = {
    "User-Agent": "ShrineDescBot/0.2 (https://www.wikidata.org/wiki/User:EmmaBot)",
    "Accept": "application/sparql-results+json"
}

# Items that…
#   • are (instances of) Shinto shrine,
#   • have P131 with an English label,
#   • HAVE an English *label*,
#   • HAVE NO English *description*.
QUERY = """
SELECT ?item ?locLabel WHERE {
  ?item (wdt:P31/wdt:P279*) wd:Q845945 ;
        wdt:P131 ?loc .

  # Must already have an English *label*
  ?item rdfs:label ?enLabel .
  FILTER (LANG(?enLabel) = "en")

  # Must NOT yet have an English *description*
  FILTER NOT EXISTS {
    ?item schema:description ?desc .
    FILTER (LANG(?desc) = "en")
  }

  # Get the English label of the P131 place
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
    ?loc rdfs:label ?locLabel .
  }
}
"""

# ─────────── HELPERS ────────────────────────────────────────────────────
def sparql(query: str):
    r = requests.get(
        SPARQL_URL,
        headers=HEADERS,
        params={"query": query, "format": "json"}
    )
    r.raise_for_status()
    return r.json()["results"]["bindings"]

def login(user: str, pwd: str):
    session = requests.Session()

    # 1) login token
    r1 = session.post(API_URL, data={
        "action": "query", "meta": "tokens", "type": "login",
        "format": "json"
    }, headers=HEADERS)
    token = r1.json()["query"]["tokens"]["logintoken"]

    # 2) log in
    r2 = session.post(API_URL, data={
        "action": "login", "lgname": user, "lgpassword": pwd,
        "lgtoken": token, "format": "json"
    }, headers=HEADERS)
    if r2.json()["login"]["result"] != "Success":
        raise RuntimeError("Login failed: " + r2.text)

    # 3) CSRF token
    r3 = session.post(API_URL, data={
        "action": "query", "meta": "tokens", "format": "json"
    }, headers=HEADERS)
    csrf = r3.json()["query"]["tokens"]["csrftoken"]
    return session, csrf

def set_description(session, csrf, qid: str, desc: str):
    payload = {
        "action": "wbeditentity",
        "id": qid,
        "data": json.dumps({
            "descriptions": {
                "en": {"language": "en", "value": desc}
            }
        }, ensure_ascii=False),
        "token": csrf,
        "format": "json",
        "summary": SUMMARY,
        "bot": 1
    }
    r = session.post(API_URL, data=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json()

# ─────────── MAIN ───────────────────────────────────────────────────────
def main():
    print("🔍 Querying SPARQL…")
    rows = sparql(QUERY)
    print(f"→ {len(rows)} candidate items")

    session, csrf = login(WD_USER, WD_PASS)
    print("✅ Logged in")

    for b in rows:
        qid = b["item"]["value"].split("/")[-1]      # e.g. Q12345
        loc = b.get("locLabel", {}).get("value")
        if not loc:
            print(f"• {qid}: missing P131 label, skip")
            continue

        new_desc = f"Shinto shrine in {loc}, Japan"
        try:
            result = set_description(session, csrf, qid, new_desc)
            if result.get("success") == 1:
                print(f"✓ {qid}: {new_desc}")
            else:
                print(f"⚠️  {qid}: API returned {result}")
        except Exception as e:
            print(f"✗ {qid}: {e}")
        time.sleep(SLEEP)

    print("🏁 Done")

if __name__ == "__main__":
    main()
