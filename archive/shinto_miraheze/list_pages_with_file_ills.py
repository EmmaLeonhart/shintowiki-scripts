#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

cat = s.pages["Category:Pages with files linked by ill"]

with open('pages_with_file_ills.txt', 'w', encoding='utf-8') as f:
    count = 0
    for pg in cat:
        if pg.namespace == 0:
            count += 1
            f.write(f"{count}. {pg.name}\n")

            # Check if it has file ills
            text = pg.text()
            ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
            matches = list(re.finditer(ill_pattern, text))
            f.write(f"   File ills: {len(matches)}\n")

print(f"Written to pages_with_file_ills.txt")
