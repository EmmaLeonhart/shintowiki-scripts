#!/usr/bin/env python3
"""
add_wikidata_to_ill_templates.py
================================
For pages in [[Category:Pages linked to Wikidata]]:
1. Find all {{ill|...}} templates without WD= parameter
2. Extract language codes and page titles
3. Query Wikidata for each language's Wikipedia article
4. Add WD= parameter with the QID
5. If no wikidatas work, add |comment=no wikipedias work
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, re, requests
from mwclient.errors import APIError

CATEGORY = "Pages linked to Wikidata"
THROTTLE = 0.5
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Language code to Wikipedia language mapping
LANG_MAP = {
    'ru': 'ruwiki',
    'zh': 'zhwiki',
    'ja': 'jawiki',
    'de': 'dewiki',
    'en': 'enwiki',
    'fr': 'frwiki',
    'es': 'eswiki',
    'it': 'itwiki',
    'pt': 'ptwiki',
    'pl': 'plwiki',
    'ko': 'kowiki',
    'ar': 'arwiki',
    'nl': 'nlwiki',
    'tr': 'trwiki',
    'fa': 'fawiki',
}

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

# ─── query wikidata ───────────────────────────────────────────────

def get_qid_from_wikipedia(lang_code: str, page_title: str) -> str:
    """Query Wikidata to get QID from a Wikipedia page"""
    try:
        # Map language code to Wikidata site parameter
        wiki_site = LANG_MAP.get(lang_code)
        if not wiki_site:
            return None

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "format": "json",
            "redirects": "1"
        }

        # Query the specific language Wikipedia
        wiki_api = f"https://{lang_code}.wikipedia.org/w/api.php"
        response = requests.get(wiki_api, params=params, timeout=10)
        response.raise_for_status()

        pages = response.json().get("query", {}).get("pages", {})
        if not pages:
            return None

        page = next(iter(pages.values()), None)
        if page and "pageprops" in page:
            qid = page["pageprops"].get("wikibase_item")
            return qid

        return None

    except Exception as e:
        print(f"      [DEBUG] Error querying {lang_code}:{page_title}: {str(e)}")
        return None

# ─── parse ill template ────────────────────────────────────────────

def parse_ill_template(template_text: str):
    """Parse {{ill|...}} template and extract parameters"""
    # Remove the {{ill| and final }}
    content = template_text[6:-2]  # Remove '{{ill|' and '}}'

    # Split by | but need to be careful with nested templates
    parts = []
    current = ""
    depth = 0
    for char in content:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        elif char == '|' and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    if current:
        parts.append(current)

    # Parse the parameters
    params = {}
    lang_entries = []

    for i, part in enumerate(parts):
        if '=' in part:
            key, value = part.split('=', 1)
            params[key.strip()] = value.strip()
        elif i == 0:
            params['title'] = part.strip()
        else:
            # Language entries: lang|title
            if '|' in part:
                lang, title = part.split('|', 1)
                lang_entries.append((lang.strip(), title.strip()))

    return params, lang_entries

# ─── reconstruct ill template ──────────────────────────────────────

def reconstruct_ill_template(params: dict, lang_entries: list) -> str:
    """Reconstruct the {{ill|...}} template with new parameters"""
    parts = [params.get('title', '')]

    for lang, title in lang_entries:
        parts.append(f"{lang}|{title}")

    # Add other parameters in order
    for key in sorted(params.keys()):
        if key != 'title':
            parts.append(f"{key}={params[key]}")

    return "{{ill|" + "|".join(parts) + "}}"

# ─── main loop ────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in")

    # Get all pages in the category
    cat = s.pages[f"Category:{CATEGORY}"]

    if not cat.exists:
        print(f"[ERROR] Category '{CATEGORY}' does not exist")
        return

    print(f"[INFO] Processing pages in Category:{CATEGORY}")

    count = 0
    for pg in cat:
        # Only process main namespace articles
        if pg.namespace != 0:
            continue

        try:
            print(f"Processing: {pg.name}")
            text = pg.text()

            # Find all {{ill|...}} templates without WD=
            ill_pattern = r'\{\{ill\|[^{}]*?\}\}'
            matches = re.finditer(ill_pattern, text)

            updated = False
            new_text = text

            for match in matches:
                template_text = match.group(0)

                # Skip if already has WD= parameter
                if 'WD=' in template_text or 'wd=' in template_text:
                    print(f"  [SKIP] template already has WD parameter")
                    continue

                print(f"  [INFO] Processing template: {template_text[:80]}...")

                params, lang_entries = parse_ill_template(template_text)

                # Query wikidata for each language
                found_qids = []
                for lang, title in lang_entries:
                    qid = get_qid_from_wikipedia(lang, title)
                    if qid:
                        found_qids.append(qid)
                        print(f"    [OK] {lang}:{title} -> {qid}")
                    else:
                        print(f"    [NOT FOUND] {lang}:{title}")

                # Update the template
                if found_qids:
                    # Use the first QID, but mention if multiple found
                    if len(set(found_qids)) > 1:
                        # Multiple different QIDs - add comment
                        qid_list = ",".join(set(found_qids))
                        params['WD'] = qid_list
                        print(f"  [MULTIPLE] Using QIDs: {qid_list}")
                    else:
                        params['WD'] = found_qids[0]

                    new_template = reconstruct_ill_template(params, lang_entries)
                    new_text = new_text.replace(template_text, new_template, 1)
                    updated = True
                else:
                    # No wikidatas found - add comment
                    params['comment'] = 'no wikipedias work'
                    new_template = reconstruct_ill_template(params, lang_entries)
                    new_text = new_text.replace(template_text, new_template, 1)
                    updated = True

            if updated:
                try:
                    pg.save(new_text, summary="Bot: Add wikidata to ill templates")
                    count += 1
                    print(f"  [DONE] updated page")
                except APIError as e:
                    print(f"  [FAILED] save failed: {e.code}")

            time.sleep(THROTTLE)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

    print(f"\nTotal pages updated: {count}")

if __name__=='__main__':
    main()
