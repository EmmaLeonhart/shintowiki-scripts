"""
ill_draft_bot.py
================
Reads page titles from pages.txt and for each page:
 1. Scans all {{ill|…}} templates.
 2. For each template:
      - Appends |12=simple
      - Appends |13=User:Immanuelle/<first term>
      - If a "1=<value>" parameter exists, appends one more |13=User:Immanuelle/<value>
      - Appends |qq=
 3. Saves the page with summary: "Bot: add simplewiki draft link to ill templates"

Example:
  {{ill|example|ja|エックス}} \
  → {{ill|example|ja|エックス|12=simple|13=User:Immanuelle/example|qq=}}

For a template with a 1= param:
  {{ill|foo|ja|ふー|1=Bar}} \
  → {{ill|foo|ja|ふー|1=Bar|12=simple|13=User:Immanuelle/foo|13=User:Immanuelle/Bar|qq=}}

Configure credentials and list pages in pages.txt, then run:
    python ill_draft_bot.py
"""
import os
import sys
import time
import re
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ────────────────────────────────────────────────
PAGES_FILE  = 'pages.txt'      # list of page titles to process
WIKI_HOST   = 'shinto.miraheze.org'
WIKI_PATH   = '/w/'
USERNAME    = 'Immanuelle'
PASSWORD    = '[REDACTED_SECRET_1]'
THROTTLE    = 1.0              # seconds between edits

# ─── REGEX FOR ILL TEMPLATES ─────────────────────────────────────
ILL_RE = re.compile(r'{{\s*ill\s*\|([^}]+?)}}', re.IGNORECASE)

# ─── LOAD PAGE TITLES ─────────────────────────────────────────────
def load_titles(path):
    if not os.path.exists(path):
        open(path, 'w', encoding='utf-8').close()
        print(f"Created empty {path}; add page titles and re-run.")
        sys.exit(0)
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]

# ─── ILL TEMPLATE REPLACEMENT ────────────────────────────────────
def repl_ill(match):
    content = match.group(1)
    parts = [p.strip() for p in content.split('|') if p.strip()]
    if not parts:
        return match.group(0)

    new_parts = ['ill'] + parts
    # append simplewiki draft marker
    new_parts.append('12=simple')
    # first term link
    first_term = parts[0]
    new_parts.append(f"13=User:Immanuelle/{first_term}")
    # detect 1= parameter
    for p in parts:
        m = re.match(r"1=(.+)", p)
        if m:
            val1 = m.group(1).strip()
            new_parts.append(f"13=User:Immanuelle/{val1}")
            break
    # append empty qq param
    new_parts.append('qq=')
    return '{{' + '|'.join(new_parts) + '}}'

# ─── PROCESS SINGLE PAGE ─────────────────────────────────────────
def process_page(site, title):
    page = site.pages[title]
    if not page.exists:
        print(f"[[{title}]] does not exist; skipped.")
        return
    text = page.text()
    new_text = ILL_RE.sub(repl_ill, text)
    if new_text != text:
        try:
            page.save(new_text, summary='Bot: add simplewiki draft link to ill templates')
            print(f"✓ Updated [[{title}]]")
        except APIError as e:
            print(f"! APIError saving [[{title}]]: {e.code}")
        except Exception as e:
            print(f"! Error saving [[{title}]]: {e}")
    else:
        print(f"– No changes for [[{title}]]")

# ─── MAIN LOOP ───────────────────────────────────────────────────
def main():
    titles = load_titles(PAGES_FILE)
    site = mwclient.Site(WIKI_HOST, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    for idx, title in enumerate(titles, 1):
        print(f"{idx}/{len(titles)} → [[{title}]]")
        process_page(site, title)
        time.sleep(THROTTLE)
    print("Done.")

if __name__ == '__main__':
    main()
