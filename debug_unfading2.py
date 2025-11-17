#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = 'https://shinto.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_1]'

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit('/api.php',1)[0]+'/')
s.login(USERNAME,PASSWORD)

pg = s.pages['Unfading Flower']
text = pg.text()

ill_pattern = r'\{\{ill\|(?:[^{}])*?\}\}'
matches = list(re.finditer(ill_pattern, text))

print(f'Found {len(matches)} ill templates\n')

for i, m in enumerate(matches[:3]):
    template = m.group(0)
    print(f'TEMPLATE {i+1}: {template}')
    print()

    # Analyze: What if "every|8=en" means:
    # - Use the title from part[0] (or labeled parameter)
    # - Use language "en" because 8=en
    # - The number 8 refers to which language?

    content = template[6:-2]
    parts = content.split('|')

    print(f'  parts[0] (title): {parts[0]}')

    # Look for language codes (patterns like 8=en, 12=...)
    languages_found = []
    for j, part in enumerate(parts[1:], 1):
        if '=' in part:
            key, val = part.split('=', 1)
            # Check if value looks like a language code
            if len(val) <= 3 and val.isalpha():
                print(f'  parts[{j}]: {key}={val} -> Language code: {val}')
                languages_found.append((val, parts[0]))

    print(f'  Languages extracted: {languages_found}')
    print()
