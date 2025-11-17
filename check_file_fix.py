#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

# Check Obata Nagatsuka Kofun
pg = s.pages["Obata Nagatsuka Kofun"]
text = pg.text()

print("Checking page: Obata Nagatsuka Kofun\n")

# Look for ill templates with File:
ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
ill_matches = list(re.finditer(ill_pattern, text))

print(f"Still has {len(ill_matches)} {{{{ill|File:...}}}} templates\n")

if ill_matches:
    for i, m in enumerate(ill_matches[:3]):
        print(f"  {i+1}. {m.group(0)[:80]}")

# Look for proper File syntax
file_pattern = r'\[\[File:[^\]]*?\]\]'
file_matches = list(re.finditer(file_pattern, text))

print(f"\nHas {len(file_matches)} [[File:...]] links\n")

if file_matches:
    for i, m in enumerate(file_matches[:3]):
        print(f"  {i+1}. {m.group(0)[:80]}")
