#!/usr/bin/env python3
"""
Extract all {{ill|...}} templates containing "UNKNOWN" from pages in
[[Category:Wikidata generated shikinaisha pages]].
Output: unknown_ills.csv  (page, template)
"""

import re, csv, time, io, sys
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

site = mwclient.Site('shinto.miraheze.org', path='/w/',
                     clients_useragent='UnknownIllExtractor/1.0 (User:Immanuelle)')
site.login('Immanuelle', '[REDACTED_SECRET_2]')
print("Logged in", flush=True)

ILL_RE = re.compile(r'\{\{ill\|[^{}]*UNKNOWN[^{}]*\}\}', re.IGNORECASE)

cat = site.categories['Wikidata generated shikinaisha pages']
rows = []
total = 0

for page in cat:
    if page.namespace != 0:
        continue
    total += 1
    if total % 500 == 0:
        print(f"  scanned {total} pages, found {len(rows)} templates so far...", flush=True)

    try:
        text = page.text()
    except Exception as e:
        print(f"  ! Error reading {page.name}: {e}", flush=True)
        continue

    for m in ILL_RE.finditer(text):
        rows.append((page.name, m.group(0)))

    time.sleep(0.3)

outfile = "unknown_ills.csv"
with open(outfile, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(["Page", "Template"])
    w.writerows(rows)

print(f"\nDone — {total} pages scanned, {len(rows)} UNKNOWN templates found", flush=True)
print(f"Saved to {outfile}", flush=True)
