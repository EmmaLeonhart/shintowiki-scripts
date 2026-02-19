#!/usr/bin/env python3
"""
merge_duplicates.py
===================
Reads qid_duplicates.csv (QID, Page1, Page2).
For each row:
1. Append to Page1: {{moved from|Page2}} + "==merged content==\n" + Page2's content
2. Replace Page2 with: {{moved to|Page1}} + #REDIRECT [[Page1]]
3. Overwrite QID redirect to point to Page1
"""

import csv, time, io, sys
import mwclient
from mwclient.errors import APIError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
THROTTLE = 1.5
CSV_FILE = "qid_duplicates.csv"

site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent='MergeDuplicatesBot/1.0 (User:Immanuelle; shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}", flush=True)

print("=" * 70, flush=True)
print("MERGE DUPLICATE QID PAGES", flush=True)
print("=" * 70, flush=True)

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

total = 0
merged = 0
errors = 0

for row in rows:
    if len(row) < 3:
        continue
    qid, page1_name, page2_name = row[0].strip(), row[1].strip(), row[2].strip()

    if qid.upper() == "QID":
        continue

    total += 1
    print(f"\n[{total}] {qid}: [[{page1_name}]] <- [[{page2_name}]]", flush=True)

    try:
        p1 = site.pages[page1_name]
        p2 = site.pages[page2_name]

        if not p1.exists:
            print(f"  ! Page1 [[{page1_name}]] does not exist, skipping", flush=True)
            errors += 1
            continue

        if not p2.exists:
            print(f"  ! Page2 [[{page2_name}]] does not exist, skipping", flush=True)
            errors += 1
            continue

        text1 = p1.text()
        text2 = p2.text()
    except Exception as e:
        print(f"  ! Error reading pages: {e}", flush=True)
        errors += 1
        continue

    # Step 1: Update Page1 - append moved from + merged content
    new_text1 = text1.rstrip() + "\n\n"
    new_text1 += f"{{{{moved from|{page2_name}}}}}\n"
    new_text1 += "==merged content==\n"
    new_text1 += text2.rstrip() + "\n"

    try:
        p1.save(new_text1, summary=f"Bot: merge content from [[{page2_name}]]")
        print(f"  + Updated [[{page1_name}]]", flush=True)
    except Exception as e:
        print(f"  ! Error saving Page1: {e}", flush=True)
        errors += 1
        continue

    time.sleep(THROTTLE)

    # Step 2: Replace Page2 with moved to + redirect
    new_text2 = f"{{{{moved to|{page1_name}}}}}\n#REDIRECT [[{page1_name}]]"

    try:
        p2.save(new_text2, summary=f"Bot: redirect to [[{page1_name}]] (merged)")
        print(f"  + Redirected [[{page2_name}]] -> [[{page1_name}]]", flush=True)
    except Exception as e:
        print(f"  ! Error saving Page2: {e}", flush=True)
        errors += 1
        continue

    time.sleep(THROTTLE)

    # Step 3: Overwrite QID redirect to point to Page1
    qid_page = site.pages[qid]
    redirect_text = f"#REDIRECT [[{page1_name}]]"

    try:
        qid_page.save(redirect_text, summary=f"Bot: redirect {qid} -> [[{page1_name}]]")
        print(f"  + {qid} -> [[{page1_name}]]", flush=True)
    except Exception as e:
        print(f"  ! Error saving QID redirect: {e}", flush=True)

    time.sleep(THROTTLE)
    merged += 1

print("\n" + "=" * 70, flush=True)
print(f"DONE - {total} pairs processed, {merged} merged, {errors} errors", flush=True)
print("=" * 70, flush=True)
