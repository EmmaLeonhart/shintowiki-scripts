#!/usr/bin/env python3
"""
add_wikidata_to_ill_templates_v2.py
===================================
For pages in [[Category:Pages linked to Wikidata]]:
1. Find all {{ill|...}} templates without WD= parameter
2. Extract language codes and page titles from the template
3. Query Wikidata for each language's Wikipedia article
4. APPEND ONLY |WD= or |comment= parameter before closing }}
5. NEVER modify or remove existing template content
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, re, requests
from mwclient.errors import APIError

CATEGORY = "Pages linked to Wikidata"
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

        # Query the specific language Wikipedia
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
    """
    Extract language codes and titles from {{ill|...}} template

    Template structure:
    {{ill|destination|lang1|title1|lang2|title2|...|key=value|...}}

    Positions:
    - Position 1 (unnamed): destination/default title
    - Positions 2-3, 4-5, 6-7, etc.: lang|title pairs (even=lang, odd=title)
    - Named params with numbers (1=, 12=, etc.) override positional params
    - Named params without numbers (lt=, WD=, etc.) are metadata, not language pairs

    If a title (odd position) is empty, use position 1 as fallback.

    Returns: list of (lang_code, title) tuples
    """
    languages = []

    # Remove the {{ill| and }}
    content = template_text[6:-2]

    # Split by | to get all parts
    parts = content.split('|')

    # Build a positional slots list, merging in numbered parameters
    slots = []
    numeric_params = {}

    # First pass: separate positional and named parameters
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            # Only collect numeric parameters (they override positional)
            if key.isdigit():
                numeric_params[int(key)] = value.strip()
        else:
            slots.append(part.strip())

    # Merge numeric parameters back into slots (they override positional)
    for idx, value in numeric_params.items():
        # idx is 1-indexed, but we'll keep slots 0-indexed for consistency
        while len(slots) < idx:
            slots.append("")
        slots[idx - 1] = value

    # Position 1 (index 0) is the destination/default title
    destination = slots[0] if slots else ""

    # Extract language pairs from positions 2, 4, 6, 8, etc. (indices 1, 3, 5, 7, etc.)
    i = 1
    while i < len(slots) - 1:
        lang_code = slots[i].strip().lower()
        title = slots[i + 1].strip() if i + 1 < len(slots) else ""

        # Language codes are primarily alphabetic (can have hyphens for variants)
        # Reject purely numeric strings (those are parameter keys, not language codes)
        is_lang_code = (
            len(lang_code) > 0 and
            not lang_code.isdigit() and  # not purely numeric
            (lang_code.isalpha() or '-' in lang_code)  # alphabetic or with hyphen (e.g., en-US)
        )

        if is_lang_code:
            # If title is empty, use destination as fallback
            if not title:
                title = destination
            languages.append((lang_code, title))
            i += 2
        else:
            # Not a language code, skip this pair
            i += 2

    return languages

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

            # Find all {{ill|...}} templates - non-greedy match
            # This pattern finds {{ill|...}} with no nested templates inside
            ill_pattern = r'\{\{ill\|(?:[^{}])*?\}\}'
            matches = list(re.finditer(ill_pattern, text))

            if not matches:
                print(f"  [SKIP] no ill templates found")
                continue

            updated = False
            new_text = text

            for match in matches:
                template_text = match.group(0)

                # Skip if already has WD= parameter
                if 'WD=' in template_text or 'wd=' in template_text:
                    print(f"  [SKIP] template already has WD parameter")
                    continue

                print(f"  [INFO] Processing template")

                # Extract language-title pairs
                languages = extract_languages_from_ill(template_text)

                if not languages:
                    print(f"    [NO LANGS] could not extract languages")
                    continue

                # Query wikidata for each language
                found_qids = []
                for lang, title in languages:
                    qid = get_qid_from_wikipedia(lang, title)
                    if qid:
                        found_qids.append(qid)
                        print(f"    [OK] {lang}:{title} -> {qid}")
                    else:
                        print(f"    [NOT FOUND] {lang}:{title}")

                # Construct the new parameter to append
                new_param = ""
                if found_qids:
                    # Use the first QID (they should all be the same ideally)
                    qid_list = "|".join(set(found_qids))
                    new_param = f"|WD={qid_list}"
                    print(f"  [ADD WD] {qid_list}")
                else:
                    # No wikidatas found
                    new_param = "|comment=no wikipedias work"
                    print(f"  [NO WD] adding comment")

                # IMPORTANT: Only append the new parameter before closing }}
                # Find the closing }} and insert before it
                new_template = template_text[:-2] + new_param + "}}"

                # Replace in text
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
