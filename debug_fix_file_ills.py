#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

# Test on Gekū Sando which should have 2 file ills
pg = s.pages["Gekū Sando"]
text = pg.text()

ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
matches = list(re.finditer(ill_pattern, text))

print(f"Found {len(matches)} file ill templates\n")

for i, match in enumerate(matches):
    template_text = match.group(0)
    print(f"Template {i+1}:")
    print(f"  Content (first 150 chars): {repr(template_text[:150])}")

    # Extract filename
    content = template_text[6:-2]
    parts = content.split('|')
    print(f"  Parts[0]: {repr(parts[0])}")
    print(f"  Starts with 'File:'? {parts[0].startswith('File:')}")
    print()
