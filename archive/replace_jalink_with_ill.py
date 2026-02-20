#!/usr/bin/env python3
"""
replace_jalink_with_ill.py
==========================
Walks through all pages in [[Category:Wikidata generated shikinaisha pages]]
and replaces {{jalink|...}} templates with {{ill|...}} templates.

Transformation rules:
  {{jalink|X|QNNN|Y}}  →  {{ill|lt=X|QNNN|WD=QNNN|lt=Y}}
  {{jalink|X|QNNN}}    →  {{ill|lt=X|QNNN|WD=QNNN}}
  {{jalink|X}}          →  {{ill||lt=X|UNKNOWN}}
"""

import re
import time
import mwclient
from mwclient.errors import APIError
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────
WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
CATEGORY  = "Wikidata generated shikinaisha pages"
THROTTLE  = 1.5
EDIT_SUMMARY = "Bot: replace {{jalink}} with {{ill}} (structured parameters)"

# ─── CONNECT ────────────────────────────
site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent='JalinkReplacerBot/1.0 (User:Immanuelle; shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}", flush=True)

# ─── JALINK REPLACEMENT LOGIC ───────────

# Matches {{jalink|...}} — assumes no nested templates inside jalink params
JALINK_RE = re.compile(r'\{\{jalink\|([^{}]*)\}\}', re.IGNORECASE)


def transform_jalink(match):
    """Transform a single {{jalink|...}} match into {{ill|...}}."""
    inner = match.group(1)
    params = [p.strip() for p in inner.split('|')]

    if len(params) >= 3:
        # {{jalink|X|QID|Y}} → {{ill|lt=X|QID|WD=QID|lt=Y}}
        name, qid, display = params[0], params[1], params[2]
        return "{{ill|lt=" + name + "|" + qid + "|WD=" + qid + "|lt=" + display + "}}"

    elif len(params) == 2:
        name, qid = params[0], params[1]
        if qid.startswith('Q') and qid[1:].isdigit():
            # {{jalink|X|QID}} → {{ill|lt=X|QID|WD=QID}}
            return "{{ill|lt=" + name + "|" + qid + "|WD=" + qid + "}}"
        else:
            # Second param is not a QID — treat like 1-param case with unknown
            return "{{ill||lt=" + name + "|UNKNOWN}}"

    elif len(params) == 1:
        # {{jalink|X}} → {{ill||lt=X|UNKNOWN}}
        name = params[0]
        return "{{ill||lt=" + name + "|UNKNOWN}}"

    else:
        # Shouldn't happen, return unchanged
        return match.group(0)


def process_page(page):
    """Process a single page. Returns True if edited, False if skipped."""
    try:
        text = page.text()
    except Exception as e:
        print(f"  ! Error reading: {e}", flush=True)
        return False

    if not JALINK_RE.search(text):
        return False

    new_text = JALINK_RE.sub(transform_jalink, text)

    if new_text == text:
        return False

    # Count replacements for logging
    old_count = len(JALINK_RE.findall(text))

    try:
        page.save(new_text, summary=EDIT_SUMMARY)
        print(f"  ✓ Saved ({old_count} jalink(s) replaced)", flush=True)
        return True
    except APIError as e:
        print(f"  ! APIError saving: {e.code}", flush=True)
        return False
    except Exception as e:
        if "429" in str(e):
            print(f"  ! Rate limited, waiting 60s...", flush=True)
            time.sleep(60)
            try:
                page.save(new_text, summary=EDIT_SUMMARY)
                print(f"  ✓ Saved on retry ({old_count} jalink(s) replaced)", flush=True)
                return True
            except Exception as e2:
                print(f"  ! Still failing: {e2}", flush=True)
                return False
        print(f"  ! Error saving: {e}", flush=True)
        return False


# ─── MAIN LOOP ──────────────────────────

def main():
    print("=" * 70, flush=True)
    print(f"REPLACE {{{{jalink}}}} → {{{{ill}}}} in [[Category:{CATEGORY}]]", flush=True)
    print("=" * 70, flush=True)

    cat = site.categories[CATEGORY]

    total = 0
    edited = 0
    skipped = 0

    for page in cat:
        # Only process mainspace (namespace 0)
        if page.namespace != 0:
            continue

        total += 1
        print(f"\n[{total}] {page.name}", flush=True)

        if process_page(page):
            edited += 1
            time.sleep(THROTTLE)
        else:
            skipped += 1
            time.sleep(0.5)  # lighter throttle for skipped pages

    print("\n" + "=" * 70, flush=True)
    print(f"DONE — {total} pages scanned, {edited} edited, {skipped} skipped", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
