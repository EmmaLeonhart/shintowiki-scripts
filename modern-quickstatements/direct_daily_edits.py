"""Execute QuickStatements v1 lines directly via the Wikidata API.

Fallback for when the QuickStatements API is unavailable. Randomly
selects up to 100 lines from the atomic QS files and executes them
via the Wikidata API with random 1-5 minute intervals between edits.

Environment variables:
    MW_BOTNAME  - Wikidata bot-password username (e.g. "EmmaBot@BotName")
    BOT_TOKEN   - Wikidata bot-password token
"""

import io
import json
import os
import random
import sys
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WD_API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

MAX_EDITS = 100
MIN_DELAY = 60   # 1 minute
MAX_DELAY = 300  # 5 minutes

# Same files as submit_daily_batch.py
ATOMIC_FILES = [
    "modern_shrine_ranking_qualifiers.txt",
    "p4656_jawiki_references.txt",
    "p958_qualifiers.txt",
    "remove_shikinai_hiteisha.txt",
    "remove_shikinaisha.txt",
    "p11250_miraheze_links.txt",
]


def read_all_lines():
    """Read all non-empty lines from all atomic QS files."""
    lines = []
    for filepath in ATOMIC_FILES:
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
    return lines


def parse_qs_value(raw):
    """Parse a QS v1 value token into a Wikidata API-compatible value."""
    if raw.startswith("Q"):
        return {"type": "entity", "value": {"entity-type": "item", "numeric-id": int(raw[1:]), "id": raw}}
    if raw.startswith('"') and raw.endswith('"'):
        return {"type": "string", "value": raw[1:-1]}
    if raw in ("novalue", "somevalue"):
        return {"type": raw}
    return {"type": "unknown", "value": raw}


def split_qs_parts(line):
    """Split a QS v1 line by | respecting quoted strings."""
    parts = []
    current = []
    in_quotes = False
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
        elif char == '|' and not in_quotes:
            parts.append(''.join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current))
    return parts


def parse_qs_line(line):
    """Parse a QS v1 line into structured components."""
    line = line.strip()
    if not line:
        return None

    is_removal = line.startswith("-")
    if is_removal:
        line = line[1:]

    parts = split_qs_parts(line)
    if len(parts) < 3:
        return None

    entity = parts[0]
    prop = parts[1]
    value = parse_qs_value(parts[2])

    qualifiers = []
    references = []

    i = 3
    while i + 1 < len(parts):
        p = parts[i]
        v = parse_qs_value(parts[i + 1])
        if p.startswith("S"):
            references.append((f"P{p[1:]}", v))
        else:
            qualifiers.append((p, v))
        i += 2

    return {
        "entity": entity,
        "property": prop,
        "value": value,
        "qualifiers": qualifiers,
        "references": references,
        "is_removal": is_removal,
    }


def value_to_api_json(parsed_value):
    """Convert a parsed value to the JSON string expected by wbcreateclaim/wbsetqualifier."""
    if parsed_value["type"] == "entity":
        return json.dumps(parsed_value["value"])
    if parsed_value["type"] == "string":
        return json.dumps(parsed_value["value"])
    return json.dumps(parsed_value.get("value", ""))


def wd_login():
    """Log in to Wikidata and return (session, csrf_token)."""
    user = os.environ.get("MW_BOTNAME")
    password = os.environ.get("BOT_TOKEN")
    if not user or not password:
        missing = []
        if not user:
            missing.append("MW_BOTNAME")
        if not password:
            missing.append("BOT_TOKEN")
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


def find_claim(session, entity, prop, parsed_value):
    """Find an existing claim on entity matching property and value. Returns claim GUID or None."""
    r = session.get(WD_API, params={
        "action": "wbgetentities", "ids": entity, "props": "claims", "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        return None
    r.raise_for_status()

    claims = r.json().get("entities", {}).get(entity, {}).get("claims", {}).get(prop, [])
    for claim in claims:
        mainsnak = claim.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value":
            continue
        dv = mainsnak.get("datavalue", {})

        if parsed_value["type"] == "entity":
            if dv.get("value", {}).get("id") == parsed_value["value"].get("id"):
                return claim["id"]
        elif parsed_value["type"] == "string":
            if dv.get("value") == parsed_value["value"]:
                return claim["id"]
    return None


def execute_removal(session, csrf, parsed):
    """Remove a claim matching the given property and value."""
    guid = find_claim(session, parsed["entity"], parsed["property"], parsed["value"])
    if not guid:
        return False, "Claim not found for removal"
    r = session.post(WD_API, data={
        "action": "wbremoveclaims", "claim": guid,
        "token": csrf, "bot": 1, "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"API error: {result['error'].get('info', str(result['error']))}"
    return True, "Removed"


def execute_create_claim(session, csrf, entity, prop, parsed_value):
    """Create a new claim. Returns (success, message, claim_guid)."""
    snaktype = "value"
    if parsed_value["type"] in ("novalue", "somevalue"):
        snaktype = parsed_value["type"]

    data = {
        "action": "wbcreateclaim", "entity": entity,
        "property": prop, "snaktype": snaktype,
        "token": csrf, "bot": 1, "format": "json",
    }
    if snaktype == "value":
        data["value"] = value_to_api_json(parsed_value)

    r = session.post(WD_API, data=data, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests", None
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"API error: {result['error'].get('info', str(result['error']))}", None
    guid = result.get("claim", {}).get("id")
    return True, "Created", guid


def execute_set_qualifier(session, csrf, guid, prop, parsed_value):
    """Add a qualifier to an existing claim."""
    snaktype = "value"
    if parsed_value["type"] in ("novalue", "somevalue"):
        snaktype = parsed_value["type"]

    data = {
        "action": "wbsetqualifier", "claim": guid,
        "property": prop, "snaktype": snaktype,
        "token": csrf, "bot": 1, "format": "json",
    }
    if snaktype == "value":
        data["value"] = value_to_api_json(parsed_value)

    r = session.post(WD_API, data=data, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"Qualifier error: {result['error'].get('info', str(result['error']))}"
    return True, "Qualifier added"


def execute_set_reference(session, csrf, guid, ref_pairs):
    """Add a reference group to an existing claim."""
    ref_snaks = {}
    for r_prop, r_val in ref_pairs:
        snak = {"snaktype": "value", "property": r_prop}
        if r_val["type"] == "entity":
            snak["datavalue"] = {"type": "wikibase-entityid", "value": r_val["value"]}
        else:
            snak["datavalue"] = {"type": "string", "value": r_val["value"]}
        ref_snaks.setdefault(r_prop, []).append(snak)

    r = session.post(WD_API, data={
        "action": "wbsetreference", "statement": guid,
        "snaks": json.dumps(ref_snaks),
        "token": csrf, "bot": 1, "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"Reference error: {result['error'].get('info', str(result['error']))}"
    return True, "Reference added"


def execute_line(session, csrf, parsed):
    """Execute a single parsed QS v1 line via Wikidata API."""
    if parsed["is_removal"]:
        return execute_removal(session, csrf, parsed)

    entity = parsed["entity"]
    prop = parsed["property"]
    value = parsed["value"]
    has_qualifiers = bool(parsed["qualifiers"])
    has_references = bool(parsed["references"])

    if not has_qualifiers and not has_references:
        # Simple claim creation
        ok, msg, _ = execute_create_claim(session, csrf, entity, prop, value)
        return ok, msg

    # Find existing claim, or create one
    guid = find_claim(session, entity, prop, value)
    if not guid:
        ok, msg, guid = execute_create_claim(session, csrf, entity, prop, value)
        if not ok:
            return False, msg
        time.sleep(1)

    # Add qualifiers
    for q_prop, q_val in parsed["qualifiers"]:
        ok, msg = execute_set_qualifier(session, csrf, guid, q_prop, q_val)
        if not ok:
            return False, msg
        time.sleep(0.5)

    # Add references
    if has_references:
        ok, msg = execute_set_reference(session, csrf, guid, parsed["references"])
        if not ok:
            return False, msg

    return True, "Done"


def main():
    print("=== Direct Wikidata API Edits (QS fallback) ===\n")

    all_lines = read_all_lines()
    if not all_lines:
        print("No QS lines found in any atomic file. Nothing to do.")
        return

    # Randomly select up to MAX_EDITS lines
    selected = random.sample(all_lines, min(MAX_EDITS, len(all_lines)))
    print(f"Selected {len(selected)} random lines from {len(all_lines)} available\n")

    session, csrf = wd_login()
    if not session:
        return

    succeeded = 0
    failed = 0

    for i, line in enumerate(selected, 1):
        parsed = parse_qs_line(line)
        if not parsed:
            print(f"[{i}/{len(selected)}] SKIP: Could not parse: {line}")
            failed += 1
            continue

        action = "REMOVE" if parsed["is_removal"] else "EDIT"
        print(f"[{i}/{len(selected)}] {action}: {line}")

        try:
            success, msg = execute_line(session, csrf, parsed)
            if success:
                print(f"  OK: {msg}")
                succeeded += 1
            else:
                print(f"  FAIL: {msg}")
                failed += 1
                if "429" in msg:
                    print("  Rate-limited — stopping further edits")
                    break
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

        # Random delay 60-300 seconds between edits
        if i < len(selected):
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            print(f"  Waiting {delay}s before next edit...", flush=True)
            time.sleep(delay)

    print(f"\n=== Results: {succeeded} succeeded, {failed} failed ===")


if __name__ == "__main__":
    main()
