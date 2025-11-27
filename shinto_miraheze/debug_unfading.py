#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = 'https://shinto.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit('/api.php',1)[0]+'/')
s.login(USERNAME,PASSWORD)

pg = s.pages['Unfading Flower']
text = pg.text()

ill_pattern = r'\{\{ill\|(?:[^{}])*?\}\}'
matches = list(re.finditer(ill_pattern, text))

print(f'Found {len(matches)} ill templates\n')

for i, m in enumerate(matches[:5]):
    template = m.group(0)
    print(f'TEMPLATE {i+1}:')
    print(template)

    # Now let's analyze the structure
    content = template[6:-2]  # Remove {{ill| and }}
    parts = content.split('|')
    print(f'Parts ({len(parts)}): {parts[:10]}')  # Show first 10 parts
    print()
