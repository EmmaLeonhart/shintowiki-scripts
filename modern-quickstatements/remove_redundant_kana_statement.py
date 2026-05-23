"""
remove_redundant_kana_statement.py
==================================
Op C of the カミノヤシロ kana pipeline (Wikidata bot request 2026-02-26),
REMOVE-ONLY — it never adds anything.

For Disputed Shikinaisha items (P31=Q135038714): when an Old-Japanese (ojp-hani)
P1448 official name ALREADY carries a P1814 katakana qualifier, AND the same
katakana reading also sits as a redundant top-level P1814 statement, remove the
top-level statement (the reading now lives on the official name).

CRITICAL SAFETY: a removal fires ONLY when a matching qualifier is confirmed
present on the live entity. The match tolerates part 1's suffix — a top-level
reading T is considered covered if some qualifier equals T or T+カミノヤシロ (i.e.
qualifier with カミノヤシロ stripped == T). So this is safe in any execution order
relative to seed_kana_qualifier.py (op A) and append_kaminoyashiro_kana.py
(part 1): the top-level can never be removed unless its reading is already on the
official name. Modern hiragana top-level readings never match a katakana
qualifier and are left untouched.

Environment: MW_BOTNAME, BOT_TOKEN.  Flags: --dry-run, --max-edits N (default 50).
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

DISPUTED_SHIKINAISHA = "Q135038714"
OFFICIAL_NAME_PROP = "P1448"
KANA_PROP = "P1814"
OFFICIAL_NAME_LANG = "ojp-hani"
SUFFIX = "カミノヤシロ"
MAX_EDITS = 50
THROTTLE = 1.5


class RateLimitError(Exception):
    """Raised when a 429 Too Many Requests response is received."""


def sparql_query(query, retries=3):
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


def find_target_items(limit):
    """Q135038714 items that have a top-level P1814 AND an ojp-hani P1448 which
    already carries a P1814 qualifier (the only items where a removal could fire)."""
    query = f"""
    SELECT DISTINCT ?item WHERE {{
      ?item wdt:P31 wd:{DISPUTED_SHIKINAISHA} ;
            p:{KANA_PROP} ?ts .
      ?item p:{OFFICIAL_NAME_PROP} ?st .
      ?st ps:{OFFICIAL_NAME_PROP} ?on . FILTER(LANG(?on) = "{OFFICIAL_NAME_LANG}") .
      ?st pq:{KANA_PROP} ?q .
    }}
    ORDER BY ?item
    LIMIT {limit}
    """
    return [r["item"]["value"].split("/")[-1] for r in sparql_query(query)]


def get_entity_claims(session, qid):
    r = session.get(WD_API, params={
        "action": "wbgetentities", "ids": qid, "props": "claims", "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        raise RateLimitError(f"429 Too Many Requests: {r.url}")
    r.raise_for_status()
    return r.json().get("entities", {}).get(qid, {}).get("claims", {})


def ojp_qualifier_readings(claims):
    """Set of readings 'covered' by a katakana P1814 qualifier on ANY ojp-hani
    P1448. For a qualifier value q, both q and (q minus a trailing カミノヤシロ)
    count, so a top-level reading matches whether or not part 1 has run yet."""
    covered = set()
    for claim in claims.get(OFFICIAL_NAME_PROP, []):
        ms = claim.get("mainsnak", {})
        dv = ms.get("datavalue", {})
        if ms.get("snaktype") != "value" or dv.get("type") != "monolingualtext":
            continue
        if dv["value"].get("language") != OFFICIAL_NAME_LANG:
            continue
        for snak in claim.get("qualifiers", {}).get(KANA_PROP, []):
            if snak.get("snaktype") == "value" and snak.get("datavalue", {}).get("type") == "string":
                q = snak["datavalue"]["value"]
                covered.add(q)
                if q.endswith(SUFFIX):
                    covered.add(q[: -len(SUFFIX)])
    return covered


def standalone_kana_statements(claims):
    """[(guid, value)] for each top-level string P1814 statement."""
    out = []
    for claim in claims.get(KANA_PROP, []):
        ms = claim.get("mainsnak", {})
        if ms.get("snaktype") == "value" and ms.get("datavalue", {}).get("type") == "string":
            out.append((claim["id"], ms["datavalue"]["value"]))
    return out


def wd_login():
    user = os.environ.get("MW_BOTNAME")
    password = os.environ.get("BOT_TOKEN")
    if not user or not password:
        missing = [n for n, v in (("MW_BOTNAME", user), ("BOT_TOKEN", password)) if not v]
        print(f"SKIPPED: {', '.join(missing)} not set")
        return None, None
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    r = session.get(WD_API, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}, timeout=60)
    r.raise_for_status()
    login_token = r.json()["query"]["tokens"]["logintoken"]
    r = session.post(WD_API, data={"action": "login", "lgname": user, "lgpassword": password, "lgtoken": login_token, "format": "json"}, timeout=60)
    r.raise_for_status()
    if r.json().get("login", {}).get("result") != "Success":
        print(f"Login failed: {json.dumps(r.json(), indent=2)}")
        return None, None
    print(f"Logged in as {r.json()['login']['lgusername']}")
    r = session.get(WD_API, params={"action": "query", "meta": "tokens", "format": "json"}, timeout=60)
    r.raise_for_status()
    return session, r.json()["query"]["tokens"]["csrftoken"]


SUMMARY = ("remove redundant top-level name in kana (already a qualifier of the "
           "ojp-hani official name) — [[Wikidata:Bot requests]] 2026-02-26")


def remove_statement(session, csrf, guid):
    r = session.post(WD_API, data={
        "action": "wbremoveclaims", "claim": guid,
        "token": csrf, "bot": 1, "summary": SUMMARY, "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        raise RateLimitError(f"429 Too Many Requests: {r.url}")
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, result["error"].get("info", str(result["error"]))
    return True, "ok"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-edits", type=int, default=MAX_EDITS)
    args = parser.parse_args()
    max_edits = args.max_edits

    print(f"=== Remove redundant top-level P1814 (REMOVE-ONLY) for {DISPUTED_SHIKINAISHA} "
          f"({'DRY RUN' if args.dry_run else f'{max_edits} edits'}) ===\n")

    items = find_target_items(max_edits)
    if not items:
        print("Nothing to do (no items with both a P1814 qualifier and a top-level P1814).")
        return
    print(f"{len(items)} candidate items\n")

    if args.dry_run:
        session = requests.Session()
        session.headers.update({"User-Agent": UA})
        csrf = None
    else:
        session, csrf = wd_login()
        if not session:
            return

    edits = 0
    failed = 0
    for item in items:
        if edits >= max_edits:
            break
        claims = get_entity_claims(session, item)
        covered = ojp_qualifier_readings(claims)
        if not covered:
            continue  # qualifier vanished since SPARQL — never remove without it
        for guid, value in standalone_kana_statements(claims):
            if edits >= max_edits:
                break
            if value not in covered:
                continue  # not covered by a qualifier → keep it (e.g. modern reading)
            print(f"[{edits + 1}/{max_edits}] {item}  remove redundant top-level P1814 {value!r} "
                  f"(already a qualifier of the ojp-hani official name)")
            if args.dry_run:
                edits += 1
                continue
            ok, msg = remove_statement(session, csrf, guid)
            if ok:
                edits += 1
            else:
                print(f"  FAIL: {msg}")
                failed += 1
            time.sleep(THROTTLE)

    label = "would remove" if args.dry_run else "removed"
    print(f"\n=== Results: {edits} top-level statements {label}, {failed} failed ===")


if __name__ == "__main__":
    main()
