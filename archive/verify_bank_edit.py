#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick script to verify the bank edit."""

import mwclient
import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

USER_AGENT = 'WiktionaryLexemeBot/1.0 (User:Immanuelle) Python/mwclient'

site = mwclient.Site('en.wiktionary.org', clients_useragent=USER_AGENT)

page = site.pages['bank']
wikitext = page.text()

# Find all instances of the lexeme template
lexeme_templates = re.findall(r'\{\{wikidata lexeme\|L\d+\}\}', wikitext)

print(f"Found {len(lexeme_templates)} lexeme template(s):")
for template in lexeme_templates:
    print(f"  - {template}")

# Check the latest revision
revisions = list(page.revisions(limit=1))
if revisions:
    latest = revisions[0]
    print(f"\nLatest revision:")
    print(f"  User: {latest.get('user', 'Unknown')}")
    print(f"  Comment: {latest.get('comment', 'No comment')[:200]}")

# Show context around first template
if lexeme_templates:
    first_match = re.search(r'(===\s*\w+\s*===.*?\{\{wikidata lexeme\|L\d+\}\}.*?\n)', wikitext, re.DOTALL)
    if first_match:
        print(f"\nContext of first template:")
        print("=" * 60)
        snippet = first_match.group(1)[:400]
        print(snippet)
        print("=" * 60)
