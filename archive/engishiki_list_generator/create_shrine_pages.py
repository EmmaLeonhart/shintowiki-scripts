#!/usr/bin/env python3
"""
create_shrine_pages.py

Creates individual shrine pages for all Shikinaisha entries.
- If page doesn't exist or has no wikidata link: create/overwrite with template
- If page exists with matching wikidata: skip
- If page exists with different wikidata: create alias (name, name (Province), name (Province 2), etc.)
"""

import os, re, time, argparse, requests, json
from html import escape

WIKI_API = "https://shinto.miraheze.org/w/api.php"
WD_API   = "https://www.wikidata.org/w/api.php"

USER = os.getenv("WIKI_USER") or "Immanuelle"
PASS = os.getenv("WIKI_PASS") or "[REDACTED_SECRET_2]"

S = requests.Session()
S.headers["User-Agent"] = "ShikinaishaPageBot/0.1"

# Cached Wikidata entities
_entity_cache = {}

def wiki_login() -> str:
    t = S.get(WIKI_API, params={
        "action": "query", "meta": "tokens",
        "type": "login", "format": "json"}).json()
    S.post(WIKI_API, data={
        "action": "login", "lgname": USER, "lgpassword": PASS,
        "lgtoken": t["query"]["tokens"]["logintoken"], "format": "json"})
    return S.get(WIKI_API, params={
        "action": "query", "meta": "tokens", "format": "json"}).json() \
             ["query"]["tokens"]["csrftoken"]

def wiki_get(title: str) -> str:
    """Get page content from wiki."""
    r = S.get(WIKI_API, params={
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "content", "format": "json"}).json()
    pages = r["query"]["pages"]
    page = next(iter(pages.values()))
    if "revisions" in page:
        return page["revisions"][0]["*"]
    return ""

def wiki_page_exists(title: str) -> bool:
    """Check if a page exists."""
    r = S.get(WIKI_API, params={
        "action": "query", "titles": title, "format": "json"}).json()
    pages = r["query"]["pages"]
    page = next(iter(pages.values()))
    return "missing" not in page

def wiki_edit(title: str, text: str, summary: str, token: str, dry: bool = False):
    """Edit a wiki page."""
    if dry:
        print(f"\n── {title} (preview) ──\n{text[:300]}…\n")
        return

    r = S.post(WIKI_API, data={
        "action": "edit", "title": title, "text": text, "token": token,
        "format": "json", "summary": summary, "bot": 1}).json()

    if "error" in r:
        raise RuntimeError(r["error"])

    print(f"[CREATED] {title}")

def get_entity_cached(qid: str) -> dict:
    """Get Wikidata entity with caching."""
    if qid in _entity_cache:
        return _entity_cache[qid]

    r = requests.get(WD_API, params={
        "action": "wbgetentities", "ids": qid, "format": "json"}).json()
    ent = r["entities"].get(qid, {})
    _entity_cache[qid] = ent
    return ent

def _lbl(ent: dict, qid: str = "") -> str:
    """Get label safely."""
    labels = ent.get("labels", {})
    if "en" in labels:
        return labels["en"]["value"]
    if labels:
        return next(iter(labels.values()))["value"]
    return qid

def extract_wikidata_qid(content: str) -> str | None:
    """Extract Wikidata QID from {{wikidata link|...}} template."""
    match = re.search(r"{{wikidata link\|([^}]+)}}", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def find_alias_name(base_name: str, province: str, existing_names: set) -> str:
    """Find a non-colliding alias name."""
    if base_name not in existing_names:
        return base_name

    # Try: "Name (Province)"
    alias = f"{base_name} ({province})"
    if alias not in existing_names:
        return alias

    # Try: "Name (Province 2)", "Name (Province 3)", etc.
    counter = 2
    while True:
        alias = f"{base_name} ({province} {counter})"
        if alias not in existing_names:
            return alias
        counter += 1

def get_shrine_name_for_page(qid: str) -> tuple[str, str]:
    """
    Get the best shrine name for creating a page.
    Returns (display_name, page_title)

    Priority:
    1. ShintoWiki P11250 if exists
    2. English Wikipedia sitelink
    3. English label
    """
    ent = get_entity_cached(qid)

    # Try P11250 (Miraheze article ID)
    for claim in ent.get("claims", {}).get("P11250", []):
        article_id = claim["mainsnak"]["datavalue"]["value"]
        if article_id.startswith("shinto:"):
            return (article_id[7:], article_id[7:])

    # Try English Wikipedia sitelink
    sitelinks = ent.get("sitelinks", {})
    if "enwiki" in sitelinks:
        title = sitelinks["enwiki"]["title"]
        return (title, title)

    # Fall back to English label
    label = _lbl(ent, qid)
    return (label, label)

def build_shrine_page_content(shrine_name: str, province: str, qid: str, table_row: str) -> str:
    """Build the content for a shrine page."""
    content = f"""'''{shrine_name}''' is a shrine in the Engishiki Jinmyōchō. It is located in [[{province}]].

{table_row}

{{{{wikidata link|{qid}}}}}

[[Category:Shikinaisha in {province}]]
[[Category:Wikidata generated shikinaisha pages]]"""
    return content

def process_shrine(qid: str, shrine_name: str, province: str, table_row: str, token: str, dry: bool = False) -> tuple[str, str]:
    """
    Process a shrine and create/update its page.
    Returns (actual_page_name, status_message)
    """
    ent = get_entity_cached(qid)

    # Get the preferred page name
    pref_name, page_title = get_shrine_name_for_page(qid)

    # Check if page exists
    if wiki_page_exists(page_title):
        existing_content = wiki_get(page_title)
        existing_qid = extract_wikidata_qid(existing_content)

        if existing_qid == qid:
            # Page exists with matching Wikidata - skip
            return (page_title, "SKIP (matching wikidata)")
        else:
            # Page exists with different or no Wikidata - create alias
            existing_names = {page_title}
            alias_name = find_alias_name(shrine_name, province, existing_names)

            content = build_shrine_page_content(alias_name, province, qid, table_row)
            wiki_edit(alias_name, content, f"Bot: Create shrine page for {shrine_name}", token, dry)

            return (alias_name, "ALIAS_CREATED")
    else:
        # Page doesn't exist - create it
        content = build_shrine_page_content(pref_name, province, qid, table_row)
        wiki_edit(page_title, content, f"Bot: Create shrine page for {shrine_name}", token, dry)

        return (page_title, "CREATED")

# For now, this is the skeleton. We need to integrate it with the table generation
# to pass the full table row data to each shrine.

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="preview only")
    args = ap.parse_args()

    csrf = wiki_login()
    print("[INFO] Shrine page creation script ready")
    print("[INFO] This will be called from update_shikinaisha_lists_v3.py")
