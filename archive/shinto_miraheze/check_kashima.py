#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

# Check Kashima Jingu
pg = s.pages["Kashima Jingu"]
text = pg.text()

print("Checking page: Kashima Jingu\n")

# Look for ill templates with File:
ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
ill_matches = list(re.finditer(ill_pattern, text))

print(f"Still has {len(ill_matches)} {{{{ill|File:...}}}} templates\n")

if ill_matches:
    for i, m in enumerate(ill_matches):
        print(f"  {i+1}. {m.group(0)[:100]}")

# Look for proper File syntax
file_pattern = r'\[\[File:[^\]]*?\]\]'
file_matches = list(re.finditer(file_pattern, text))

print(f"\nHas {len(file_matches)} [[File:...]] links\n")
