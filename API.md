# API access patterns

This document records exactly how each external service is accessed across this codebase. The reason many old scripts are kept around is that the correct working patterns needed to be preserved — this document replaces that need.

---

## Table of contents

1. [shinto.miraheze.org (mwclient)](#1-shintomirahezeorg--mwclient)
2. [Wikidata (requests — read-only)](#2-wikidata--requests-read-only)
3. [Wikipedia language editions (requests — read-only)](#3-wikipedia-language-editions--requests-read-only)
4. [Wikimedia Commons (mwclient — bot login)](#4-wikimedia-commons--mwclient-bot-login)
5. [Wiktionary (mwclient — bot login)](#5-wiktionary--mwclient-bot-login)
6. [Authentication summary](#6-authentication-summary)
7. [Rate limiting reference](#7-rate-limiting-reference)
8. [Not used in this codebase](#8-not-used-in-this-codebase)

---

## 1. shinto.miraheze.org — mwclient

**This is the primary pattern.** Every active script that edits the wiki uses this.

### Connection + login

```python
import mwclient

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "EmmaBot"
PASSWORD  = "[REDACTED_SECRET_1]"    # some old scripts have "[REDACTED_SECRET_1]"

site = mwclient.Site(
    WIKI_URL,
    path=WIKI_PATH,
    clients_useragent="BotName/1.0 (User:EmmaBot; shinto.miraheze.org)"
)
site.login(USERNAME, PASSWORD)
```

### Verify login (robust across mwclient versions)

```python
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).")
```

### User-agent strings seen in working scripts

```
CategoryQidRedirectBot/1.0 (User:EmmaBot; shinto.miraheze.org)
IllFixerBot/1.0 (User:EmmaBot; shinto.miraheze.org)
EmmaBotCategoryWikidataBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot)
EmmaBotInterwikiBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot)
EmmaBotCategoryBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot)
```

### Core operations

```python
# Read a page
page = site.pages["Page title"]
text = page.text()
exists = page.exists

# Save / edit a page
page.save(new_text, summary="Bot: edit summary here")

# Check and handle safe save (edit conflicts, deleted pages)
def safe_save(page, text, summary):
    if not page.exists:
        return False
    try:
        current = page.text()
    except Exception:
        current = None
    if current is not None and current.rstrip() == text.rstrip():
        return False   # nothing changed
    try:
        page.save(text, summary=summary)
        return True
    except mwclient.errors.APIError as e:
        if e.code == "editconflict":
            print(f"Edit conflict on [[{page.name}]] – skipping")
            return False
        raise

# Iterate all pages in a namespace
for page in site.allpages(namespace=14):      # 14 = Category
    ...

# Iterate all pages starting from a title (for resuming)
for page in site.allpages(namespace=14, start="SomeTitle"):
    ...

# Iterate members of a category
cat = site.categories["Category name"]
for page in cat:
    print(page.name, page.namespace)

# Filter category members by namespace
cat_pages = [p for p in site.categories["Pages linked to Wikidata"] if p.namespace == 14]

# Direct API call
result = site.api('query', meta='userinfo')
result = site.api('query', list='embeddedin', eititle='Template:Foo', eilimit='max')
```

### Namespace numbers

| Namespace | Number |
|-----------|--------|
| Main (articles) | 0 |
| Talk | 1 |
| Category | 14 |
| Category Talk | 15 |
| Template | 10 |
| File | 6 |

### Throttling pattern

```python
import time
THROTTLE = 1.5   # seconds between edits — standard for Miraheze

time.sleep(THROTTLE)   # call after every page.save()
```

### Windows Unicode fix (always include on Windows)

```python
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

## 2. Wikidata — requests (read-only)

All Wikidata reads use plain `requests` — no login needed.

### Entity data (fastest for single items)

```python
import requests

HEADERS = {"User-Agent": "BotName/1.0 (User:EmmaBot; shinto.miraheze.org)"}

def get_entity(qid: str) -> dict:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()["entities"][qid]

entity = get_entity("Q12345")
labels    = entity.get("labels", {})
sitelinks = entity.get("sitelinks", {})
enwiki    = sitelinks.get("enwiki", {}).get("title")
```

### wbgetentities API (batch or targeted)

```python
def get_entities(qids: list[str], props="labels|sitelinks") -> dict:
    r = requests.get(
        "https://www.wikidata.org/w/api.php",
        params={
            "action":    "wbgetentities",
            "ids":       "|".join(qids),
            "props":     props,
            "languages": "en",
            "format":    "json",
        },
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("entities", {})
```

### SPARQL queries

```python
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

def sparql_query(query: str) -> list[dict]:
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["results"]["bindings"]

# Example: find all Shinto shrines with coordinates
results = sparql_query("""
    SELECT ?item ?itemLabel ?lat ?lon WHERE {
      ?item wdt:P31/wdt:P279* wd:Q845945 .
      ?item p:P625 ?coord .
      ?coord psv:P625 ?coordNode .
      ?coordNode wikibase:geoLatitude  ?lat .
      ?coordNode wikibase:geoLongitude ?lon .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
    }
""")
```

### Get QID for a Wikipedia page

```python
def get_wikidata_qid(lang: str, title: str) -> str | None:
    r = requests.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop":   "pageprops",
            "format": "json",
        },
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    for pid, page in pages.items():
        if int(pid) > 0:
            return page.get("pageprops", {}).get("wikibase_item")
    return None
```

---

## 3. Wikipedia language editions — requests (read-only)

Used to resolve interwiki links back to Wikidata QIDs, and to verify page existence.

### Check if a Wikipedia category has a Wikidata item

```python
def query_wikipedia_for_wikidata(lang_code: str, category_title: str) -> list[str]:
    """Returns list of QIDs found for the category on that Wikipedia."""
    url = f"https://{lang_code}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": f"Category:{category_title.replace(' ', '_')}",
        "prop":   "pageprops",
        "format": "json",
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    qids = []
    for pid, page in pages.items():
        if int(pid) > 0 and "pageprops" in page:
            qid = page["pageprops"].get("wikibase_item")
            if qid:
                qids.append(qid.upper())
    return list(set(qids))
```

### Read another wiki's page (mwclient, read-only, no login)

```python
en_site = mwclient.Site("en.wikipedia.org", path="/w/",
                         clients_useragent=BOT_USER_AGENT)
# No site.login() — read-only access works without it
page = en_site.pages["Some article"]
text = page.text()
```

### Languages used in this codebase

Common language codes seen: `en`, `ja`, `de`, `zh`, `ko`, `fr`, `ru`, `nl`, `it`, `es`, `pt`, `sv`, `fi`, `pl`, `hu`, `ar`, `id`, `vi`, `tr`

---

## 4. Wikimedia Commons — mwclient (bot login)

Used for editing Commons category pages (adding shrine ranking categories etc.).

### Connection + login

```python
COMMONS_USERNAME = "EmmaBot@EmmaBotCommonsBot"
COMMONS_PASSWORD = "rctsl2fbuo3qa0ngj1q2eur5ookdbjir"   # bot password

commons = mwclient.Site("commons.wikimedia.org", path="/w/",
                         clients_useragent="EmmaBotCommonsBot/1.0")
commons.login(COMMONS_USERNAME, COMMONS_PASSWORD)
```

**Note:** The `@BotName` format is a MediaWiki bot password — the part before `@` is the account username, the part after is the bot name registered at `Special:BotPasswords`.

### Operations seen

```python
page = commons.pages["Category:Some Commons Category"]
text = page.text()
page.save(new_text, summary="Bot: add category")
```

**Throttle:** 10 seconds between edits (Commons is stricter).

---

## 5. Wiktionary — mwclient (bot login)

Used for adding `{{wikidata lexeme|LXXXXX}}` templates to Wiktionary entries.

### Connection + login

```python
BOT_USERNAME = "EmmaBotBot@Bot"
BOT_PASSWORD  = "hljht8jdeh1p1562gke2tmj7hkqg9hkf"

wikt = mwclient.Site("en.wiktionary.org", path="/w/",
                      clients_useragent="WiktionaryLexemeBot/1.0 (User:EmmaBot) Python/mwclient")
wikt.login(BOT_USERNAME, BOT_PASSWORD)
```

For Japanese Wiktionary:
```python
jawikt = mwclient.Site("ja.wiktionary.org", path="/w/",
                        clients_useragent=USER_AGENT)
jawikt.login(BOT_USERNAME, BOT_PASSWORD)
```

### SPARQL for lexeme lookup

```python
def find_lexeme(lemma: str, lang_qid: str = "Q1860", pos_qid: str = "Q1084") -> str | None:
    """Find a Wikidata lexeme QID for a given lemma + language + POS."""
    query = f"""
    SELECT ?lexeme WHERE {{
      ?lexeme dct:language wd:{lang_qid} ;
              wikibase:lemma "{lemma}"@en ;
              wikibase:lexicalCategory wd:{pos_qid} .
    }} LIMIT 1
    """
    results = sparql_query(query)
    if results:
        return results[0]["lexeme"]["value"].split("/")[-1]   # e.g. "L12345"
    return None
```

---

## 6. Authentication summary

| Service | Library | Auth type | Account format |
|---------|---------|-----------|----------------|
| shinto.miraheze.org | mwclient | Username + password | `EmmaBot` |
| commons.wikimedia.org | mwclient | Bot password | `EmmaBot@EmmaBotCommonsBot` |
| en.wiktionary.org | mwclient | Bot password | `EmmaBotBot@Bot` |
| ja.wiktionary.org | mwclient | Bot password | `EmmaBotBot@Bot` |
| wikidata.org | requests | None (public read) | User-Agent header only |
| *.wikipedia.org | requests | None (public read) | User-Agent header only |

**Bot passwords** (`Special:BotPasswords`) are separate from the main account password — they're scoped to specific permissions and can be revoked independently. This is the correct mechanism for bot access to Wikimedia wikis.

---

## 7. Rate limiting reference

| Target | Throttle | Notes |
|--------|----------|-------|
| shinto.miraheze.org edits | 1.5 s | Standard for all active scripts |
| shinto.miraheze.org reads | none | Reading doesn't count against limits |
| commons.wikimedia.org edits | 10 s | Commons is stricter |
| Wikidata / Wikipedia API reads | 0.3–0.5 s | Polite crawling |
| SPARQL queries | 1.0 s | query.wikidata.org has per-IP limits |
| HTTP 429 response | 60 s wait | Back-off before retry |
| Script startup delay (some) | 30 min | Race-condition avoidance between concurrent scripts |

General rule for Miraheze: stay under ~40 edits/minute. 1.5 s per edit is comfortably under that.

---

## 8. Not used in this codebase

- **pywikibot** — zero imports anywhere. All wiki access is via mwclient or raw requests.
- **OAuth** — not used. mwclient handles session cookies from username/password login internally.
- **pramana.dev** — referenced in planning/vision but no actual API calls implemented yet.
- **Direct database / SQL** — not used.
- **MediaWiki XML dump parsing** — some old import scripts used XML files locally, but not via API.

---

## Minimal working template

Copy this to start a new shintowiki bot script:

```python
"""
script_name.py
==============
One-line description of what this does.
"""
import re, time, io, sys
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "EmmaBot"
PASSWORD  = "[REDACTED_SECRET_1]"
THROTTLE  = 1.5
BOT_UA    = "BotName/1.0 (User:EmmaBot; shinto.miraheze.org)"

site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=BOT_UA)
site.login(USERNAME, PASSWORD)
print("Logged in as", USERNAME, flush=True)


def main():
    pages = site.allpages(namespace=0)   # or site.categories["Some Cat"]
    for page in pages:
        text = page.text()
        # ... do stuff ...
        new_text = text  # modified
        if new_text != text:
            page.save(new_text, summary="Bot: description of change")
            time.sleep(THROTTLE)


if __name__ == "__main__":
    main()
```
