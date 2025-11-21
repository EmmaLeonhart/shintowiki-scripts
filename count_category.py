#!/usr/bin/env python3
import urllib.parse, mwclient

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

cat = s.pages["Category:Pages with files linked by ill"]
count = 0
pages = []

for pg in cat:
    if pg.namespace == 0:  # mainspace only
        count += 1
        pages.append(pg.name)

print(f"Total pages in category: {count}\n")
print("Pages:")
for p in pages:
    print(f"  - {p}")
