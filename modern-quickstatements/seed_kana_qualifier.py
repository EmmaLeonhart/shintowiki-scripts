"""
seed_kana_qualifier.py
======================
Op A of the カミノヤシロ kana pipeline (Wikidata bot request 2026-02-26),
ADD-ONLY — it never removes anything.

For Disputed Shikinaisha items (P31=Q135038714) whose single Old-Japanese
(ojp-hani) P1448 official name has NO P1814 qualifier yet, but which carry the
Old-Japanese reading as a top-level KATAKANA P1814 statement, copy that katakana
reading onto the official name as a P1814 qualifier (raw, no suffix).

This is deliberately split from the destructive half. The three ops are each
independently safe under random / drip execution:
  * seed_kana_qualifier.py (this)        — add the katakana qualifier (ADD-ONLY)
  * append_kaminoyashiro_kana.py (part1) — append カミノヤシロ to katakana qualifiers
  * remove_redundant_kana_statement.py   — remove the top-level katakana ONLY
                                           once a matching qualifier is confirmed
Because nothing here removes the source statement, there is no path where the
top-level reading is lost before its qualifier exists. The raw katakana is added
(not katakana+カミノヤシロ) so part 1 owns the suffix uniformly across all
ojp-hani katakana qualifiers, seeded or pre-existing.

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


def is_katakana_reading(value):
    """True for an Old-Japanese katakana reading; False for modern hiragana etc.
    Rejects any value containing a hiragana char, or with no katakana at all."""
    has_hiragana = any("぀" <= ch <= "ゟ" for ch in value)
    has_katakana = any("゠" <= ch <= "ヿ" for ch in value)
    return has_katakana and not has_hiragana


def find_target_items(limit):
    """Q135038714 items with a top-level P1814 and an ojp-hani P1448 that has NO
    P1814 qualifier yet (the seed candidates)."""
    query = f"""
    SELECT DISTINCT ?item WHERE {{
      ?item wdt:P31 wd:{DISPUTED_SHIKINAISHA} ;
            p:{KANA_PROP} ?ts .
      ?item p:{OFFICIAL_NAME_PROP} ?st .
      ?st ps:{OFFICIAL_NAME_PROP} ?on . FILTER(LANG(?on) = "{OFFICIAL_NAME_LANG}")
      FILTER NOT EXISTS {{ ?st pq:{KANA_PROP} ?q }}
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


def find_ojp_official_name(claims):
    out = []
    for claim in claims.get(OFFICIAL_NAME_PROP, []):
        ms = claim.get("mainsnak", {})
        if ms.get("snaktype") != "value":
            continue
        dv = ms.get("datavalue", {})
        if dv.get("type") == "monolingualtext" and dv["value"].get("language") == OFFICIAL_NAME_LANG:
            out.append(claim)
    return out


def existing_kana_qualifiers(target_claim):
    vals = set()
    for snak in target_claim.get("qualifiers", {}).get(KANA_PROP, []):
        if snak.get("snaktype") == "value" and snak.get("datavalue", {}).get("type") == "string":
            vals.add(snak["datavalue"]["value"])
    return vals


def standalone_kana_values(claims):
    """Top-level P1814 string values."""
    out = []
    for claim in claims.get(KANA_PROP, []):
        ms = claim.get("mainsnak", {})
        if ms.get("snaktype") == "value" and ms.get("datavalue", {}).get("type") == "string":
            out.append(ms["datavalue"]["value"])
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


SUMMARY = ("seed P1814 katakana qualifier on ojp-hani official name from the "
           "top-level name in kana — [[Wikidata:Bot requests]] 2026-02-26")


def add_kana_qualifier(session, csrf, target_guid, value):
    r = session.post(WD_API, data={
        "action": "wbsetqualifier", "claim": target_guid, "property": KANA_PROP,
        "snaktype": "value", "value": json.dumps(value),
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

    print(f"=== Seed P1814 katakana qualifier (ADD-ONLY) for {DISPUTED_SHIKINAISHA} "
          f"({'DRY RUN' if args.dry_run else f'{max_edits} edits'}) ===\n")

    items = find_target_items(max_edits)
    if not items:
        print("No seed candidates (every ojp-hani official name already has a P1814 qualifier).")
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
    skipped_ambiguous = []
    skipped_no_katakana = []

    for item in items:
        if edits >= max_edits:
            break
        claims = get_entity_claims(session, item)
        targets = find_ojp_official_name(claims)
        if len(targets) != 1:
            skipped_ambiguous.append((item, f"{len(targets)} ojp-hani P1448 names"))
            continue
        target = targets[0]
        existing = existing_kana_qualifiers(target)
        if existing:
            # Qualifier already present — not a seed candidate (SPARQL should have
            # excluded it; re-check against live data). Leave to part 1 / op C.
            continue
        katakana = [v for v in standalone_kana_values(claims) if is_katakana_reading(v)]
        if not katakana:
            skipped_no_katakana.append((item, standalone_kana_values(claims)))
            continue
        for value in dict.fromkeys(katakana):  # de-dup, preserve order
            if edits >= max_edits:
                break
            if value in existing:
                continue
            print(f"[{edits + 1}/{max_edits}] {item}  add P1814 qualifier {value!r} (raw katakana)")
            if args.dry_run:
                edits += 1
                existing.add(value)
                continue
            ok, msg = add_kana_qualifier(session, csrf, target["id"], value)
            if ok:
                edits += 1
                existing.add(value)
            else:
                print(f"  FAIL: {msg}")
                failed += 1
            time.sleep(THROTTLE)

    label = "would add" if args.dry_run else "added"
    print(f"\n=== Results: {edits} qualifiers {label}, {failed} failed, "
          f"{len(skipped_ambiguous)} ambiguous, {len(skipped_no_katakana)} no-katakana ===")
    for qid, reason in skipped_ambiguous:
        print(f"  AMBIGUOUS https://www.wikidata.org/wiki/{qid} — {reason}")
    for qid, vals in skipped_no_katakana:
        print(f"  NO-KATAKANA https://www.wikidata.org/wiki/{qid} — {vals!r} (needs a modern ja name, not this op)")


if __name__ == "__main__":
    main()
