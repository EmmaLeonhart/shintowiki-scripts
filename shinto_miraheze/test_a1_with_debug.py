#!/usr/bin/env python3
import urllib.parse, mwclient, re, requests
from mwclient.errors import APIError

API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

def get_qid_from_wikipedia(lang_code: str, page_title: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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

def extract_languages_from_ill(template_text: str):
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

s = site()
print("Logged in\n")

pg = s.pages["A1 Decan Lists"]
text = pg.text()

ill_pattern = r'\{\{ill\|(?:[^{}])*?\}\}'
matches = list(re.finditer(ill_pattern, text))

print(f"Found {len(matches)} ill templates\n")

# Test first 3 templates
for i, match in enumerate(matches[:3]):
    template_text = match.group(0)
    print(f"TEMPLATE {i+1}:")
    print(f"  Original: {template_text[:80]}...")

    languages = extract_languages_from_ill(template_text)
    print(f"  Languages: {languages}")

    found_qids = []
    for lang, title in languages:
        qid = get_qid_from_wikipedia(lang, title)
        if qid:
            found_qids.append(qid)
            print(f"    FOUND: {lang}:{title} -> {qid}")
        else:
            print(f"    NOT FOUND: {lang}:{title}")

    if found_qids:
        new_param = f"|WD={found_qids[0]}"
    else:
        new_param = "|comment=no wikipedias work"

    new_template = template_text[:-2] + new_param + "}}"
    print(f"  Would add: {new_param}")
    print()
