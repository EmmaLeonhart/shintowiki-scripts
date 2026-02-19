#!/usr/bin/env python3
"""
create_qid_redirects.py
=======================
For every page in [[Category:Pages linked to Wikidata]]:
1. Extract QID from {{wikidata link|QNNN}}
2. Create/overwrite page titled "QNNN" as #REDIRECT [[Page Name]]
3. Log all QID→page mappings to qid_redirects.csv for duplicate checking
"""

import re, csv, time, io, sys
import mwclient
from mwclient.errors import APIError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
CATEGORY = "Pages linked to Wikidata"
THROTTLE = 1.5
CSV_FILE = "qid_redirects.csv"

site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent='QidRedirectBot/1.0 (User:Immanuelle; shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}", flush=True)

WD_LINK_RE = re.compile(r'\{\{wikidata link\|(Q\d+)\}\}', re.IGNORECASE)

cat = site.categories[CATEGORY]
total = 0
created = 0
skipped = 0
rows = []

csvf = open(CSV_FILE, 'w', newline='', encoding='utf-8')
writer = csv.writer(csvf)
writer.writerow(["QID", "Page"])

print("=" * 70, flush=True)
print(f"CREATE QID REDIRECTS from [[Category:{CATEGORY}]]", flush=True)
print("=" * 70, flush=True)

for page in cat:
    if page.namespace != 0:
        continue

    total += 1
    page_name = page.name

    try:
        text = page.text()
    except Exception as e:
        print(f"[{total}] {page_name} — ERROR reading: {e}", flush=True)
        continue

    match = WD_LINK_RE.search(text)
    if not match:
        skipped += 1
        if total % 200 == 0:
            print(f"[{total}] {page_name} — no wikidata link, skipping", flush=True)
        continue

    qid = match.group(1)

    # Log to CSV
    writer.writerow([qid, page_name])
    csvf.flush()

    # Create/overwrite the QID redirect page
    redirect_text = f"#REDIRECT [[{page_name}]]"
    qid_page = site.pages[qid]

    try:
        qid_page.save(redirect_text, summary=f"Bot: redirect {qid} → [[{page_name}]]")
        created += 1
        print(f"[{total}] {qid} → [[{page_name}]]", flush=True)
    except APIError as e:
        print(f"[{total}] {qid} — APIError: {e.code}", flush=True)
    except Exception as e:
        if "429" in str(e):
            print(f"[{total}] Rate limited, waiting 60s...", flush=True)
            time.sleep(60)
            try:
                qid_page.save(redirect_text, summary=f"Bot: redirect {qid} → [[{page_name}]]")
                created += 1
                print(f"[{total}] {qid} → [[{page_name}]] (retry)", flush=True)
            except Exception as e2:
                print(f"[{total}] {qid} — still failing: {e2}", flush=True)
        else:
            print(f"[{total}] {qid} — ERROR: {e}", flush=True)

    time.sleep(THROTTLE)

csvf.close()

print("\n" + "=" * 70, flush=True)
print(f"DONE — {total} pages scanned, {created} redirects created, {skipped} skipped (no QID)", flush=True)
print(f"CSV saved to {CSV_FILE}", flush=True)
print("=" * 70, flush=True)
