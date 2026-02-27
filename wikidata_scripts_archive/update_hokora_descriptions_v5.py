#!/usr/bin/env python3
"""
update_shrine_descriptions_v5.py
────────────────────────────────
Add an English description

    "Shinto shrine in <Prefecture>, Japan"

for every item that

  • is (instance/sub‑instance) of Shinto shrine (Q1442984)
  • has a P131 chain that reaches a Japanese prefecture (Q50337)
  • **already has an English *label***
  • **has NO English *description*** yet

Old provinces (Q860290) are ignored because the query stops at the first
prefecture node.

Requires:  requests, simplejson   (pip install requests simplejson)
"""

import time, requests, simplejson as json
from collections import defaultdict

# ─── CONFIG ─────────────────────────────────────────────────────────────
BOT_USER = "EmmaBot@EmmaBotMisc"
BOT_PASS = "3c5akegiqjk7sbnhscl059ihusi0bo4e"
SUMMARY  = "Bot: adding short description based on location'"
PAUSE    = 1.5                                   # seconds between edits
UA       = "ShrineDescBot/0.5 (User:EmmaBot)"
SPARQL   = "https://query.wikidata.org/sparql"
API      = "https://www.wikidata.org/w/api.php"
BATCH    = 5_000                                 # SPARQL LIMIT per slice
RETRIES  = 3                                     # WDQS retry attempts
# ─────────────────────────────────────────────────────────────────────────

QUERY_TEMPLATE = """
SELECT ?item ?prefLabel WHERE {{
  # Shinto shrine (instance‑of or subclass‑instance)
  ?item (wdt:P31/wdt:P279*) wd:Q1442984 ;
        wdt:P131+ ?pref .

  # Prefecture of Japan
  ?pref wdt:P31 wd:Q50337 .

  # MUST have an English label
  ?item rdfs:label ?enLabel .
  FILTER (LANG(?enLabel) = "en")

  # MUST NOT already have an English description
  FILTER NOT EXISTS {{
    ?item schema:description ?desc .
    FILTER (LANG(?desc) = "en")
  }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT {limit}
OFFSET {offset}
"""

def sparql_rows(limit: int, offset: int):
    query = QUERY_TEMPLATE.format(limit=limit, offset=offset)
    for attempt in range(1, RETRIES + 1):
        r = requests.post(
            SPARQL,
            headers={
                "User-Agent": UA,
                "Accept": "application/sparql-results+json"
            },
            data={"query": query, "format": "json"},
            timeout=60,
        )
        ctype = r.headers.get("Content-Type", "")
        if "application/sparql-results+json" not in ctype:
            wait = 5 * attempt
            print(f"⚠️  WDQS non‑JSON reply (try {attempt}/{RETRIES}); "
                  f"sleep {wait}s …")
            time.sleep(wait)
            continue
        try:
            return r.json()["results"]["bindings"]
        except json.JSONDecodeError as e:
            wait = 5 * attempt
            print(f"⚠️  JSON decode failed (try {attempt}/{RETRIES}): {e}; "
                  f"sleep {wait}s …")
            time.sleep(wait)
    raise RuntimeError("WDQS failed after multiple attempts")

def login(user, pwd):
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    token = s.post(API, data={
        "action":"query","meta":"tokens","type":"login","format":"json"
    }).json()["query"]["tokens"]["logintoken"]

    if s.post(API, data={
        "action":"login","lgname":user,"lgpassword":pwd,
        "lgtoken":token,"format":"json"
    }).json()["login"]["result"] != "Success":
        raise RuntimeError("Login failed")

    csrf = s.post(API, data={
        "action":"query","meta":"tokens","format":"json"
    }).json()["query"]["tokens"]["csrftoken"]

    return s, csrf

def edit_desc(s, csrf, qid, text):
    data = json.dumps(
        {"descriptions":{"en":{"language":"en","value":text}}},
        ensure_ascii=False
    )
    r = s.post(API, data={
        "action":"wbeditentity","id":qid,"data":data,
        "token":csrf,"bot":1,"summary":SUMMARY,"format":"json"
    }, timeout=60)
    r.raise_for_status()
    return r.json()

# ─── MAIN ───────────────────────────────────────────────────────────────
def main():
    sess, csrf = login(BOT_USER, BOT_PASS)
    print("✅ Logged in")

    offset = 0
    total  = 0
    while True:
        rows = sparql_rows(BATCH, offset)
        if not rows:
            break

        # item → prefecture label (take first)
        tgt = defaultdict(str)
        for b in rows:
            qid  = b["item"]["value"].split("/")[-1]
            pref = b["prefLabel"]["value"]
            if not tgt[qid]:
                tgt[qid] = pref

        print(f"🧮 Batch {offset // BATCH + 1}: {len(tgt)} items")
        for qid, pref in tgt.items():
            new_desc = f"Shinto shrine in {pref}, Japan"
            try:
                out = edit_desc(sess, csrf, qid, new_desc)
                if out.get("success") == 1:
                    print(f"✓ {qid}: {new_desc}")
                    total += 1
                else:
                    print(f"⚠️  {qid}: {out}")
            except Exception as e:
                print(f"✗ {qid}: {e}")
            time.sleep(PAUSE)

        offset += BATCH

    print(f"🏁 Done – {total} descriptions added.")

if __name__ == "__main__":
    main()
