"""
template_cleanup_bot.py
=======================
Scans all templates (ns=10) on Shinto Wiki and:
 1. Deletes any template page that is unused and has no English interwiki.
 2. Redirects unused templates that have an [[en:Template:…]] interwiki to that English template with a bucket category.

Templates with local usage (transclusions or backlinks) are skipped.

Configure USERNAME/PASSWORD, then run:
    python template_cleanup_bot.py
"""
import re
import time
import mwclient
from mwclient.errors import APIError

# ─── CONFIGURATION ─────────────────────────────────────────────────
WIKI_URL   = 'shinto.miraheze.org'
WIKI_PATH  = '/w/'
USERNAME   = 'Immanuelle'
PASSWORD   = '[REDACTED_SECRET_1]'
THROTTLE   = 0.5  # seconds between operations

# ─── CONNECT & LOGIN ───────────────────────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)
#print(f"Logged in as {site.userinfo.get('name')}")

# ─── HELPERS ───────────────────────────────────────────────────────

def safe_save(page, text, summary):
    try:
        current = page.text()
    except Exception:
        return False
    if current.rstrip() == text.rstrip():
        return False
    try:
        page.save(text, summary=summary)
        return True
    except APIError as e:
        if e.code == 'editconflict':
            print(f"! Edit conflict on [[{page.name}]]; skipped.")
            return False
        print(f"! APIError on [[{page.name}]]: {e.code}")
    except Exception as e:
        print(f"! Error saving [[{page.name}]]: {e}")
    return False


def has_local_usage(page):
    try:
        for _ in page.embeddedin(limit=1):
            return True
    except Exception:
        pass
    try:
        for _ in page.backlinks(limit=1):
            return True
    except Exception:
        pass
    return False

EN_IWIKI_RE = re.compile(r"\[\[en:Template:([^\]|]+)")

# ─── PROCESS SINGLE TEMPLATE ───────────────────────────────────────
def process_template(page):
    title = page.name  # 'Template:Foo'
    print(f"Processing [[{title}]]...")
    if has_local_usage(page):
        print("  • In use locally; skipped.")
        return
    text = page.text()
    m = EN_IWIKI_RE.search(text)
    if m:
        target = m.group(1).replace(' ', '_')
        bucket = target[0].upper() if target else ''
        stub = (
            f"#redirect [[en:Template:{target}]]\n"
            f"[[Category:automatic wikipedia template redirects {bucket}]]"
        )
        if safe_save(page, stub, "Bot: redirect unused template to en:"):
            print(f"  • Redirected to en:Template:{target}")
        else:
            print(f"  ! Failed to redirect [[{title}]]")
    else:
        try:
            page.delete(reason="Bot: delete unused template", watch=False)
            print(f"  • Deleted unused [[{title}]]")
        except APIError as e:
            print(f"  ! Delete failed [[{title}]]: {e.code}")

# ─── MAIN LOOP ────────────────────────────────────────────────────
def main():
    count = 0
    for page in site.allpages(namespace=10):
        count += 1
        print(f"{count}.", end=' ')
        process_template(page)
        time.sleep(THROTTLE)
    print("All templates processed.")

if __name__ == '__main__':
    main()
