"""
append_kaminoyashiro_kana.py
============================
Append カミノヤシロ to the P1814 (name in kana) qualifier of Old Japanese
(ojp-hani) P1448 (official name) statements on shrine items, via the
Wikidata API (wbsetqualifier with snakhash), bypassing QuickStatements.

Background — Wikidata bot request 2026-02-26:
  https://www.wikidata.org/wiki/Wikidata:Bot_requests
  Old Japanese katakanizations of shrine names store the reading of the
  shrine name in a P1814 qualifier but omit the reading of 神社, which in
  Old Japanese is read カミノヤシロ (kami-no-yashiro). This script appends
  カミノヤシロ to each such qualifier value.

Data shape (verified against live Wikidata):
  - P1448 mainsnak is monolingualtext, language "ojp-hani".
  - P1814 qualifier is the *string* datatype (NOT monolingualtext).
  - A single P1448 statement may carry multiple P1814 qualifiers
    (alternate readings) — each is appended independently.

The edit modifies the existing qualifier in place by passing its snakhash
to wbsetqualifier, so no duplicate qualifier is created. Idempotent: a
qualifier whose value already ends in カミノヤシロ is skipped, and the SPARQL
universe shrinks as work progresses (STRENDS filter).

Environment variables:
    MW_BOTNAME  — Wikidata bot-password username (e.g. "EmmaBot@BotName")
    BOT_TOKEN   — Wikidata bot-password token

Flags:
    --dry-run   — fetch + report planned edits without writing (no creds needed)
    --max-edits N — override the per-run edit cap (default 50)
"""

import argparse
import io
import json
import os
import sys
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WD_API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

OFFICIAL_NAME_PROP = "P1448"   # official name (monolingualtext, ojp-hani)
KANA_QUALIFIER_PROP = "P1814"  # name in kana (string)
OFFICIAL_NAME_LANG = "ojp-hani"
SUFFIX = "カミノヤシロ"          # Old Japanese reading of 神社

# Capped at 50/day to sit alongside the existing daily wikidata jobs
# (submit_daily_batch 50 + test_wikidata_qualifier 50) under the
# once-per-day fire gate in cleanup-loop.yml.
MAX_EDITS = 50
# Wikidata API edits: 1.5s between writes (gentler than test_wikidata_qualifier's 1s).
THROTTLE = 1.5


class RateLimitError(Exception):
    """Raised when a 429 Too Many Requests response is received."""


def sparql_query(query, retries=3):
    """Run a SPARQL query against Wikidata. Retries on timeout; bails on 429."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=90,
            )
            if r.status_code == 429:
                print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
                raise RateLimitError(f"429 Too Many Requests: {r.url}")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except requests.exceptions.ReadTimeout:
            print(f"SPARQL timeout (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(10 * attempt)
            else:
                print("SPARQL endpoint timed out after all retries — exiting gracefully")
                return []


def count_remaining():
    """Count P1814 qualifiers on ojp-hani P1448 statements still missing the suffix."""
    query = f"""
    SELECT (COUNT(*) AS ?total) WHERE {{
      ?item p:{OFFICIAL_NAME_PROP} ?stmt .
      ?stmt ps:{OFFICIAL_NAME_PROP} ?officialName ;
            pq:{KANA_QUALIFIER_PROP} ?kanaName .
      FILTER(LANG(?officialName) = "{OFFICIAL_NAME_LANG}")
      FILTER(!STRENDS(STR(?kanaName), "{SUFFIX}"))
    }}
    """
    rows = sparql_query(query)
    if not rows:
        return None
    return int(rows[0]["total"]["value"])


def find_target_items(limit):
    """Find distinct items with an ojp-hani P1448 statement carrying a P1814
    qualifier that does not yet end in カミノヤシロ. Returns a list of QIDs."""
    query = f"""
    SELECT DISTINCT ?item WHERE {{
      ?item p:{OFFICIAL_NAME_PROP} ?stmt .
      ?stmt ps:{OFFICIAL_NAME_PROP} ?officialName ;
            pq:{KANA_QUALIFIER_PROP} ?kanaName .
      FILTER(LANG(?officialName) = "{OFFICIAL_NAME_LANG}")
      FILTER(!STRENDS(STR(?kanaName), "{SUFFIX}"))
    }}
    ORDER BY ?item
    LIMIT {limit}
    """
    results = sparql_query(query)
    return [r["item"]["value"].split("/")[-1] for r in results]


def get_entity_claims(session, qid):
    """Fetch claims for an entity."""
    r = session.get(
        WD_API,
        params={"action": "wbgetentities", "ids": qid, "props": "claims", "format": "json"},
        timeout=60,
    )
    if r.status_code == 429:
        print("FATAL: 429 Too Many Requests from Wikidata API — bailing")
        raise RateLimitError(f"429 Too Many Requests: {r.url}")
    r.raise_for_status()
    return r.json().get("entities", {}).get(qid, {}).get("claims", {})


def find_kana_targets(claims):
    """From an entity's claims, yield (statement_guid, snakhash, old_value, new_value)
    for every P1814 string qualifier on an ojp-hani P1448 statement that still
    needs the suffix appended."""
    targets = []
    for claim in claims.get(OFFICIAL_NAME_PROP, []):
        mainsnak = claim.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value":
            continue
        dv = mainsnak.get("datavalue", {})
        if dv.get("type") != "monolingualtext":
            continue
        if dv["value"].get("language") != OFFICIAL_NAME_LANG:
            continue

        guid = claim["id"]
        for snak in claim.get("qualifiers", {}).get(KANA_QUALIFIER_PROP, []):
            if snak.get("snaktype") != "value":
                continue
            qdv = snak.get("datavalue", {})
            if qdv.get("type") != "string":
                continue
            old_value = qdv.get("value", "")
            if old_value.endswith(SUFFIX):
                continue  # idempotent: already done
            targets.append((guid, snak["hash"], old_value, old_value + SUFFIX))
    return targets


def wd_login():
    """Log in to Wikidata and return (session, csrf_token). Returns (None, None)
    if credentials are absent (graceful skip, not an error)."""
    user = os.environ.get("MW_BOTNAME")
    password = os.environ.get("BOT_TOKEN")
    if not user or not password:
        missing = [n for n, v in (("MW_BOTNAME", user), ("BOT_TOKEN", password)) if not v]
        print(f"SKIPPED: {', '.join(missing)} not set")
        return None, None

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    r = session.get(WD_API, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json",
    }, timeout=60)
    r.raise_for_status()
    login_token = r.json()["query"]["tokens"]["logintoken"]

    r = session.post(WD_API, data={
        "action": "login", "lgname": user, "lgpassword": password,
        "lgtoken": login_token, "format": "json",
    }, timeout=60)
    r.raise_for_status()
    result = r.json()
    if result.get("login", {}).get("result") != "Success":
        print(f"Login failed: {json.dumps(result, indent=2)}")
        return None, None
    print(f"Logged in as {result['login']['lgusername']}")

    r = session.get(WD_API, params={
        "action": "query", "meta": "tokens", "format": "json",
    }, timeout=60)
    r.raise_for_status()
    csrf = r.json()["query"]["tokens"]["csrftoken"]
    return session, csrf


def set_string_qualifier(session, csrf, guid, snakhash, new_value):
    """Replace an existing string qualifier (identified by snakhash) with new_value."""
    r = session.post(WD_API, data={
        "action": "wbsetqualifier",
        "claim": guid,
        "property": KANA_QUALIFIER_PROP,
        "snakhash": snakhash,
        "snaktype": "value",
        "value": json.dumps(new_value),  # string datatype → JSON-encoded string
        "token": csrf,
        "bot": 1,
        "summary": "append カミノヤシロ (reading of 神社) to ojp-hani name in kana — "
                   "[[Wikidata:Bot requests]] 2026-02-26",
        "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        print("FATAL: 429 Too Many Requests from Wikidata API — bailing")
        raise RateLimitError(f"429 Too Many Requests: {r.url}")
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, result["error"].get("info", str(result["error"]))
    return True, "ok"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and report planned edits without writing (no creds needed).")
    parser.add_argument("--max-edits", type=int, default=MAX_EDITS,
                        help=f"Per-run edit cap (default {MAX_EDITS}).")
    args = parser.parse_args()
    max_edits = args.max_edits

    print(f"=== Append {SUFFIX} to ojp-hani P1814 kana qualifiers "
          f"({'DRY RUN' if args.dry_run else f'{max_edits} edits'}) ===\n")

    remaining = count_remaining()
    if remaining is not None:
        print(f"Qualifiers still missing {SUFFIX}: {remaining}")
    if remaining == 0:
        print("Nothing to do — all ojp-hani kana qualifiers already end in カミノヤシロ.")
        return

    # Fetch a few more items than the edit budget — some items contribute >1
    # qualifier, so item-count and edit-count diverge; the per-edit break
    # below enforces the real cap.
    print(f"\nFinding target items (up to {max_edits})...")
    items = find_target_items(max_edits)
    if not items:
        print("No target items returned by SPARQL.")
        return
    print(f"  {len(items)} candidate items")

    if args.dry_run:
        session = requests.Session()
        session.headers.update({"User-Agent": UA})
        csrf = None
    else:
        print("\nLogging in to Wikidata...")
        session, csrf = wd_login()
        if not session:
            return

    edits = 0
    failed = 0
    skipped_items = 0

    for item in items:
        if edits >= max_edits:
            break
        claims = get_entity_claims(session, item)
        targets = find_kana_targets(claims)
        if not targets:
            skipped_items += 1
            continue
        for guid, snakhash, old_value, new_value in targets:
            if edits >= max_edits:
                break
            print(f"[{edits + 1}/{max_edits}] {item}  {old_value!r} -> {new_value!r}")
            if args.dry_run:
                edits += 1
                continue
            ok, msg = set_string_qualifier(session, csrf, guid, snakhash, new_value)
            if ok:
                edits += 1
            else:
                print(f"  FAIL: {msg}")
                failed += 1
            time.sleep(THROTTLE)

    label = "would edit" if args.dry_run else "edited"
    print(f"\n=== Results: {edits} {label}, {failed} failed, "
          f"{skipped_items} items skipped (no remaining qualifier) ===")


if __name__ == "__main__":
    main()
