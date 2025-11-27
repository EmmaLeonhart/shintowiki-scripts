#!/usr/bin/env python3
"""
add_dutch_labels.py
────────────────────
For every Q845945 instance that has an English label like "X Shrine" but no Dutch label,
add a Dutch label of the form "X-schrijn".

USAGE
─────
  python add_dutch_labels.py            # live
  python add_dutch_labels.py --dry      # preview only
  python add_dutch_labels.py --verbose  # chatty
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
    "User-Agent": "ImmanuelleDutchLabelBot/0.1 (https://wikidata.org/wiki/User:Immanuelle; mailto:immanuelleleonhart@gmail.com)"
}

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
def make_nl_label(en_label):
    base = en_label.replace(" Shrine", "")
    return f"{base}-schrijn"

def add_dutch_label(qid, nl_label, verbose, dry):
    if dry and verbose:
        print(f"DRY → would add Lnl \"{nl_label}\" to {qid}")
        return "dry-run"

    r = wd_post({
        "action": "wbsetlabel",
        "id": qid,
        "language": "nl",
        "value": nl_label,
        "summary": "Bot: add Dutch label from English"
    })

    if "error" in r:
        code = r["error"]["code"]
        if code in {"failed-save", "modification-failed", "unresolved-redirect"}:
            return code
        raise RuntimeError(r["error"])

    if verbose:
        print(f"✓ {qid} ← {nl_label}")
    time.sleep(1.2 + random.random())
    return "added"

# ─── Main logic ─────────────────────────────────────────────────────
def query_items():
    query = """SELECT ?item ?enLabel WHERE {
      ?item wdt:P31 wd:Q845945.
      ?item rdfs:label ?enLabel.
      FILTER(LANG(?enLabel) = "en")
      FILTER(REGEX(?enLabel, "^[A-Z][a-zA-Z'’ -]+ Shrine$"))
      OPTIONAL { ?item rdfs:label ?nlLabel. FILTER(LANG(?nlLabel) = "nl") }
      FILTER(!BOUND(?nlLabel))
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
        nl_label = make_nl_label(en_label)
        result = add_dutch_label(qid, nl_label, verbose, dry)
        if result == "added":
            added += 1
        else:
            skipped += 1

    action = "would be added" if dry else "added"
    print(f"\n✅ {added} Dutch label(s) {action}, {skipped} skipped.")

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
