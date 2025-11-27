#!/usr/bin/env python3
"""
test_a1_decan.py
================
Test the corrected script on A1 Decan Lists page - SHOW RESULTS ONLY, NO EDITS
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, re, requests
from mwclient.errors import APIError

THROTTLE = 0.5

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
        params = {
            "action": "query",
            "titles": page_title,
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "format": "json",
            "redirects": "1"
        }

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

    except Exception:
        return None

# ─── extract language and title from ill template ──────────────────

def extract_languages_from_ill(template_text: str):
    """Extract language codes and titles from {{ill|...}} template"""
    languages = []
    content = template_text[6:-2]
    parts = content.split('|')

    i = 1
    while i < len(parts):
        part = parts[i]

        if '=' not in part and len(part) <= 3 and part.isalpha():
            lang_code = part
            if i + 1 < len(parts) and '=' not in parts[i + 1]:
                title = parts[i + 1]
                languages.append((lang_code, title))
                i += 2
            else:
                i += 1
        else:
            i += 1

    return languages

# ─── main loop ────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in\n")

    test_page = "A1 Decan Lists"

    try:
        print(f"Testing on: {test_page}\n")
        pg = s.pages[test_page]

        if not pg.exists:
            print(f"[ERROR] Page does not exist")
            return

        text = pg.text()
        print(f"[INFO] Page text length: {len(text)} characters\n")

        # Find all {{ill|...}} templates
        ill_pattern = r'\{\{ill\|(?:[^{}])*?\}\}'
        matches = list(re.finditer(ill_pattern, text))

        print(f"[INFO] Found {len(matches)} ill templates\n")

        if not matches:
            print(f"[SKIP] no ill templates found")
            return

        template_count = 0
        for i, match in enumerate(matches):
            template_text = match.group(0)
            template_count += 1
            print(f"{'='*100}")
            print(f"TEMPLATE {template_count}:")
            print(f"{'='*100}")
            print(f"\nORIGINAL:")
            print(f"{template_text}\n")

            # Skip if already has WD= parameter
            if 'WD=' in template_text or 'wd=' in template_text:
                print(f"[SKIP] already has WD parameter\n")
                continue

            # Extract language-title pairs
            languages = extract_languages_from_ill(template_text)
            print(f"EXTRACTED LANGUAGES: {languages}\n")

            # Query wikidata for each language
            found_qids = []
            for lang, title in languages:
                qid = get_qid_from_wikipedia(lang, title)
                if qid:
                    found_qids.append(qid)
                    print(f"  [OK] {lang}:{title} -> {qid}")
                else:
                    print(f"  [NOT FOUND] {lang}:{title}")

            # Show what would be added
            print(f"\nPARAMETER TO ADD:")
            if found_qids:
                new_param = f"|WD={found_qids[0]}"
                print(f"{new_param}")
            else:
                new_param = "|comment=no wikipedias work"
                print(f"{new_param}")

            # Show the new template
            new_template = template_text[:-2] + new_param + "}}"
            print(f"\nNEW TEMPLATE:")
            print(f"{new_template}\n")

            # Verify content preserved
            original_parts = template_text[6:-2].split('|')[:8]  # First 8 parts
            preserved = all(part in new_template for part in original_parts)
            if preserved:
                print(f"[CHECK] Original content preserved: YES\n")
            else:
                print(f"[CHECK] Original content preserved: NO (ERROR!)\n")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__=='__main__':
    main()
