#!/usr/bin/env python3
"""
edit_a1_decan_real.py
=====================
ACTUALLY EDIT A1 Decan Lists page to test the script
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "format": "json",
            "redirects": "1"
        }

        wiki_api = f"https://{lang_code}.wikipedia.org/w/api.php"
        response = requests.get(wiki_api, params=params, headers=headers, timeout=10)
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
        print(f"Editing: {test_page}\n")
        pg = s.pages[test_page]

        if not pg.exists:
            print(f"[ERROR] Page does not exist")
            return

        text = pg.text()
        print(f"[INFO] Original page text length: {len(text)} characters\n")

        # Find all {{ill|...}} templates
        ill_pattern = r'\{\{ill\|(?:[^{}])*?\}\}'
        matches = list(re.finditer(ill_pattern, text))

        print(f"[INFO] Found {len(matches)} ill templates\n")

        if not matches:
            print(f"[SKIP] no ill templates found")
            return

        new_text = text
        updated_count = 0

        for match in matches:
            template_text = match.group(0)

            # Skip if already has WD= parameter
            if 'WD=' in template_text or 'wd=' in template_text:
                continue

            # Extract language-title pairs
            languages = extract_languages_from_ill(template_text)

            if not languages:
                continue

            # Query wikidata for each language
            found_qids = []
            for lang, title in languages:
                qid = get_qid_from_wikipedia(lang, title)
                if qid:
                    found_qids.append(qid)

            # Construct the new parameter to append
            if found_qids:
                qid_list = "|".join(set(found_qids))
                new_param = f"|WD={qid_list}"
            else:
                new_param = "|comment=no wikipedias work"

            # Replace in text
            new_template = template_text[:-2] + new_param + "}}"
            new_text = new_text.replace(template_text, new_template, 1)
            updated_count += 1
            print(f"[UPDATED] Template {updated_count}")

        print(f"\n[INFO] Total templates to update: {updated_count}")
        print(f"[INFO] New page text length: {len(new_text)} characters\n")

        if updated_count > 0:
            try:
                pg.save(new_text, summary="Bot: Add wikidata to ill templates")
                print(f"[SUCCESS] Page saved!")
            except APIError as e:
                print(f"[FAILED] save failed: {e.code}")

        time.sleep(THROTTLE)

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__=='__main__':
    main()
