#!/usr/bin/env python3
"""
add_french_labels.py
────────────────────
For every Q134917280 instance that has an English label like "X Shrine" but no French label,
add a French label of the form "Sanctuaire de X" or "Sanctuaire d’X" (if X begins with vowel or h).

USAGE
─────
  python add_french_labels.py            # live
  python add_french_labels.py --dry      # preview only
  python add_french_labels.py --verbose  # chatty
"""

import argparse, json, random, time, sys, requests
from requests_toolbelt.utils import dump

# ─── config ─────────────────────────────────────────────────────────
BOT_USER = "Immanuelle@ImmanuelleMisc"
BOT_PASS = "3c5akegiqjk7sbnhscl059ihusi0bo4e"
WD_USER = BOT_USER
WD_PASS = BOT_PASS

WD_API = "https://www.wikidata.org/w/api.php"
WD_SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "ImmanuelleFrenchLabelBot/0.1 (https://wikidata.org/wiki/User:Immanuelle; mailto:immanuelleleonhart@gmail.com)"
}

# ────────────────────────────────────────────────────────────────────

S = requests.Session()
S.headers.update(HEADERS)
TOKEN = ""

# ─── Wikidata helpers ──────────────────────────────────────────────
def wd_login():
    global TOKEN
    t = S.get(WD_API, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}).json()
    S.post(WD_API, data={"action": "login", "lgname": WD_USER,
                         "lgpassword": WD_PASS, "lgtoken": t["query"]["tokens"]["logintoken"],
                         "format": "json"})
    TOKEN = S.get(WD_API, params={"action": "query", "meta": "tokens", "format": "json"}).json()["query"]["tokens"]["csrftoken"]

def wd_post(data):
    base = {"format": "json", "assert": "user", "bot": 1, "token": TOKEN, "maxlag": 10}
    r = S.post(WD_API, data={**base, **data}).json()
    return r

# ─── Label logic ────────────────────────────────────────────────────
def make_fr_label(en_label):
    base = en_label.replace(" Shrine", "")
    if base[0].lower() in "aeiouh":
        return f"Sanctuaire d’{base}"
    else:
        return f"Sanctuaire de {base}"

def add_french_label(qid, fr_label, verbose, dry):
    if dry and verbose:
        print(f"DRY → would add Lfr \"{fr_label}\" to {qid}")
        return "dry-run"

    r = wd_post({
        "action": "wbsetlabel",
        "id": qid,
        "language": "fr",
        "value": fr_label,
        "summary": "Bot: add French label from English"
    })

    if "error" in r:
        code = r["error"]["code"]
        if code in {"failed-save", "modification-failed", "unresolved-redirect"}:
            return code
        raise RuntimeError(r["error"])
    
    if verbose:
        print(f"✓ {qid} ← {fr_label}")
    time.sleep(1.2 + random.random())
    return "added"

# ─── Main logic ─────────────────────────────────────────────────────

def query_items():
    query = """SELECT ?item ?enLabel WHERE {
      ?item wdt:P31 wd:Q845945.
      ?item rdfs:label ?enLabel.
      FILTER(LANG(?enLabel) = "en")
      FILTER(REGEX(?enLabel, "^[A-Z][a-zA-Z-]+ Shrine$"))
      OPTIONAL { ?item rdfs:label ?frLabel. FILTER(LANG(?frLabel) = "fr") }
      FILTER(!BOUND(?frLabel))
    }"""

    try:
        resp = S.post(WD_SPARQL, data={"query": query, "format": "json"})
        data = dump.dump_all(resp)
        with open("sparql_debug.txt", "wb") as f:
            f.write(data)

        if resp.status_code != 200:
            print("⚠️ SPARQL endpoint error:", resp.status_code)
            print("Full request/response written to sparql_debug.txt")
            raise SystemExit(1)

        return [(b["item"]["value"].split("/")[-1], b["enLabel"]["value"])
                for b in resp.json()["results"]["bindings"]]

    except Exception as e:
        print("❌ SPARQL query failed:", e)
        raise SystemExit(1)



def main(dry=False, verbose=False):
    wd_login()
    items = query_items()
    added = skipped = 0

    for qid, en_label in items:
        fr_label = make_fr_label(en_label)
        result = add_french_label(qid, fr_label, verbose, dry)
        if result == "added":
            added += 1
        else:
            skipped += 1

    action = "would be added" if dry else "added"
    print(f"\n✅ {added} French label(s) {action}, {skipped} skipped.")

# ─── CLI ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="preview only")
    ap.add_argument("--verbose", action="store_true", help="print every action")
    args = ap.parse_args()
    try:
        main(dry=args.dry, verbose=args.verbose)
    except KeyboardInterrupt:
        sys.exit("aborted")
