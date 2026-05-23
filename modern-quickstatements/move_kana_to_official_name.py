"""
move_kana_to_official_name.py
=============================
Move standalone P1814 (name in kana) statements into a P1814 qualifier on
the Old Japanese (ojp-hani) P1448 (official name) statement, for Disputed
Shikinaisha items, via the Wikidata API.

Background — Wikidata bot request 2026-02-26 (secondary ask):
  https://www.wikidata.org/wiki/Wikidata:Bot_requests
  An earlier mass edit moved each shrine's "name in kana" from a top-level
  P1814 statement into a P1814 qualifier of the ojp-hani official name, but
  missed many P31=Q135038714 (Disputed Shikinaisha or Shikigeisha) items.
  For each missed item this script:
    1. moves each standalone top-level P1814 statement into a P1814 qualifier
       on the single ojp-hani P1448 statement, with カミノヤシロ appended
       (the Old Japanese reading of 神社; matches append_kaminoyashiro_kana.py);
    2. removes the now-redundant standalone P1814 statement.

  Kana values are moved verbatim — placeholder dashes (e.g. "イハツタノ-",
  "-ニシ") are preserved, not interpreted.

Ambiguity handling: an item is SKIPPED (and reported to stdout) when it has
0 or >1 ojp-hani P1448 statements — there is no single official name to
attach the qualifier to (e.g. Q135039223 has two). Those are left for a human.

Idempotency: the standalone-statement removal drops the item out of the
SPARQL universe (which filters on `p:P1814`); a qualifier whose value already
exists on the target statement is not re-added.

Environment variables:
    MW_BOTNAME  — Wikidata bot-password username (e.g. "EmmaBot@BotName")
    BOT_TOKEN   — Wikidata bot-password token

Flags:
    --dry-run     — fetch + report planned edits without writing (no creds needed)
    --max-edits N — override the per-run API-write cap (default 50)
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

DISPUTED_SHIKINAISHA = "Q135038714"  # Disputed Shikinaisha or Shikigeisha
OFFICIAL_NAME_PROP = "P1448"         # official name (monolingualtext, ojp-hani)
KANA_PROP = "P1814"                  # name in kana (string)
OFFICIAL_NAME_LANG = "ojp-hani"
SUFFIX = "カミノヤシロ"               # Old Japanese reading of 神社

# Each item costs 1 add-qualifier + 1 remove-statement per standalone P1814
# (~2 writes). 50/run keeps it gentle and finite (~155 items → a few days).
MAX_EDITS = 50
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
    """Count Disputed Shikinaisha items that still have a standalone P1814 statement."""
    query = f"""
    SELECT (COUNT(DISTINCT ?item) AS ?total) WHERE {{
      ?item wdt:P31 wd:{DISPUTED_SHIKINAISHA} ;
            p:{KANA_PROP} ?s .
    }}
    """
    rows = sparql_query(query)
    return int(rows[0]["total"]["value"]) if rows else None


def find_target_items(limit):
    """Find Disputed Shikinaisha items that have a standalone top-level P1814 statement."""
    query = f"""
    SELECT DISTINCT ?item WHERE {{
      ?item wdt:P31 wd:{DISPUTED_SHIKINAISHA} ;
            p:{KANA_PROP} ?s .
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


def find_ojp_official_name(claims):
    """Return a list of ojp-hani P1448 claims (monolingualtext)."""
    out = []
    for claim in claims.get(OFFICIAL_NAME_PROP, []):
        ms = claim.get("mainsnak", {})
        if ms.get("snaktype") != "value":
            continue
        dv = ms.get("datavalue", {})
        if dv.get("type") != "monolingualtext":
            continue
        if dv["value"].get("language") == OFFICIAL_NAME_LANG:
            out.append(claim)
    return out


def existing_kana_qualifiers(target_claim):
    """Set of existing P1814 string qualifier values on the target P1448 claim."""
    vals = set()
    for snak in target_claim.get("qualifiers", {}).get(KANA_PROP, []):
        if snak.get("snaktype") == "value" and snak.get("datavalue", {}).get("type") == "string":
            vals.add(snak["datavalue"]["value"])
    return vals


def is_katakana_reading(value):
    """True if the value is an Old-Japanese katakana reading (the kind the bot
    request targets), False for modern hiragana readings.

    The standalone P1814 set on these items is mixed: katakana OJ readings
    (e.g. タケミナカタトミノ-) alongside modern hiragana readings (e.g.
    いめじんじゃはちまんぐう, which already contains じんじゃ=神社 in modern reading).
    Appending カミノヤシロ — the *Old Japanese* reading of 神社 — only makes sense
    for the katakana ones, so any value containing a hiragana character is
    rejected (and reported), as is a value with no katakana at all."""
    has_hiragana = any("぀" <= ch <= "ゟ" for ch in value)
    has_katakana = any("゠" <= ch <= "ヿ" for ch in value)
    return has_katakana and not has_hiragana


def standalone_kana_statements(claims):
    """Return [(guid, value)] for each top-level string P1814 statement."""
    out = []
    for claim in claims.get(KANA_PROP, []):
        ms = claim.get("mainsnak", {})
        if ms.get("snaktype") != "value":
            continue
        dv = ms.get("datavalue", {})
        if dv.get("type") != "string":
            continue
        out.append((claim["id"], dv["value"]))
    return out


def wd_login():
    """Log in to Wikidata and return (session, csrf_token), or (None, None) if no creds."""
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


SUMMARY = ("move name in kana from statement to P1814 qualifier of ojp-hani official "
           "name + append カミノヤシロ — [[Wikidata:Bot requests]] 2026-02-26")


def add_kana_qualifier(session, csrf, target_guid, value):
    """Add a new P1814 string qualifier to the target statement (no snakhash → create)."""
    r = session.post(WD_API, data={
        "action": "wbsetqualifier",
        "claim": target_guid,
        "property": KANA_PROP,
        "snaktype": "value",
        "value": json.dumps(value),
        "token": csrf, "bot": 1, "summary": SUMMARY, "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        raise RateLimitError(f"429 Too Many Requests: {r.url}")
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, result["error"].get("info", str(result["error"]))
    return True, "ok"


def remove_statement(session, csrf, guid):
    """Remove a top-level statement by GUID."""
    r = session.post(WD_API, data={
        "action": "wbremoveclaims",
        "claim": guid,
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
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and report planned edits without writing (no creds needed).")
    parser.add_argument("--max-edits", type=int, default=MAX_EDITS,
                        help=f"Per-run API-write cap (default {MAX_EDITS}).")
    args = parser.parse_args()
    max_edits = args.max_edits

    print(f"=== Move standalone P1814 kana -> ojp-hani P1448 qualifier (+{SUFFIX}) "
          f"for {DISPUTED_SHIKINAISHA} ({'DRY RUN' if args.dry_run else f'{max_edits} writes'}) ===\n")

    remaining = count_remaining()
    if remaining is not None:
        print(f"Items still carrying a standalone P1814 statement: {remaining}")
    if remaining == 0:
        print("Nothing to do.")
        return

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
    skipped = []              # (qid, reason) — no single ojp-hani official name
    skipped_has_qualifier = 0 # ojp-hani P1448 already has a P1814 qualifier → part 1's domain
    skipped_modern = []       # (qid, values) — no qualifier and no katakana OJ reading at all

    for item in items:
        if edits >= max_edits:
            break
        claims = get_entity_claims(session, item)
        targets = find_ojp_official_name(claims)
        standalone = standalone_kana_statements(claims)
        if not standalone:
            continue
        if len(targets) != 1:
            reason = f"{len(targets)} ojp-hani P1448 official names (need exactly 1)"
            skipped.append((item, reason))
            print(f"SKIP {item}: {reason}")
            continue

        target = targets[0]
        target_guid = target["id"]
        existing = existing_kana_qualifiers(target)

        # If the ojp-hani official name ALREADY has a P1814 katakana qualifier,
        # that is part 1's domain (append_kaminoyashiro_kana.py appends カミノヤシロ
        # to the existing qualifier). Leave the whole item alone — INCLUDING its
        # normal top-level modern (hiragana) reading. Part 2 only SEEDS a missing
        # qualifier; moving a standalone in here would create a duplicate.
        if existing:
            skipped_has_qualifier += 1
            continue

        # No qualifier yet: move the standalone Old-Japanese KATAKANA reading in.
        katakana = [(g, v) for g, v in standalone if is_katakana_reading(v)]
        if not katakana:
            # No qualifier AND no katakana OJ reading anywhere — only a modern
            # reading exists; genuinely needs a human / modern ja official name.
            skipped_modern.append((item, [v for _, v in standalone]))
            continue

        for guid, value in katakana:
            if edits >= max_edits:
                break
            desired = value + SUFFIX
            # 1) Add the qualifier (unless an equivalent already exists)
            if desired in existing or value in existing:
                print(f"[{edits + 1}] {item}  qualifier {desired!r} already present — add skipped")
            else:
                print(f"[{edits + 1}/{max_edits}] {item}  add P1814 qualifier {desired!r} "
                      f"(from statement {value!r})")
                if args.dry_run:
                    edits += 1
                else:
                    ok, msg = add_kana_qualifier(session, csrf, target_guid, desired)
                    if ok:
                        edits += 1
                        existing.add(desired)
                    else:
                        print(f"  FAIL (add): {msg}")
                        failed += 1
                        continue  # don't remove the source statement if the move failed
                    time.sleep(THROTTLE)
            if edits >= max_edits:
                break
            # 2) Remove the now-redundant standalone statement
            print(f"[{edits + 1}/{max_edits}] {item}  remove standalone P1814 statement {value!r}")
            if args.dry_run:
                edits += 1
            else:
                ok, msg = remove_statement(session, csrf, guid)
                if ok:
                    edits += 1
                else:
                    print(f"  FAIL (remove): {msg}")
                    failed += 1
                time.sleep(THROTTLE)

    label = "would write" if args.dry_run else "writes"
    print(f"\n=== Results: {edits} {label}, {failed} failed, "
          f"{len(skipped)} ambiguous (manual), "
          f"{skipped_has_qualifier} left to part 1 (qualifier already exists), "
          f"{len(skipped_modern)} modern-only (no OJ reading) ===")
    if skipped:
        print("\nAmbiguous — need a human (0 or >1 ojp-hani official name):")
        for qid, reason in skipped:
            print(f"  https://www.wikidata.org/wiki/{qid} — {reason}")
    if skipped_modern:
        print("\nNo qualifier and no Old-Japanese katakana reading anywhere — only a "
              "modern reading exists; needs a modern ja official name (not this op):")
        for qid, values in skipped_modern:
            print(f"  https://www.wikidata.org/wiki/{qid} — {values!r}")
    # Note: items whose ojp-hani P1448 already has a P1814 qualifier are NOT a
    # problem — append_kaminoyashiro_kana.py (part 1) appends カミノヤシロ to that
    # qualifier, and their top-level modern reading is left as-is. They are
    # counted above only for transparency.


if __name__ == "__main__":
    main()
