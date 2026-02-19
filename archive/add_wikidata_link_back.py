#!/usr/bin/env python3
import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

site = mwclient.Site('shinto.miraheze.org', path='/w/')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

page = site.pages['Ōarahiko Shrine']
content = page.text()

# Add wikidata link at the end if not present
if '{{wikidata link|Q11438675}}' not in content:
    content += '\n{{wikidata link|Q11438675}}'
    page.save(content, summary='Add wikidata link back')
    print("Added wikidata link")
else:
    print("Already has wikidata link")
