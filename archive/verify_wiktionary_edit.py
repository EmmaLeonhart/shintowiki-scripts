#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick script to verify the Wiktionary edit."""

import mwclient
import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

USER_AGENT = 'WiktionaryLexemeBot/1.0 (User:Immanuelle) Python/mwclient'

site = mwclient.Site('en.wiktionary.org', clients_useragent=USER_AGENT)

page = site.pages['hydrogen']
wikitext = page.text()

# Find the English Noun section
english_match = re.search(r'==\s*English\s*==', wikitext)
if english_match:
    english_start = english_match.end()
    next_l2 = re.search(r'\n==\s*[^=]+\s*==', wikitext[english_start:])
    if next_l2:
        english_end = english_start + next_l2.start()
    else:
        english_end = len(wikitext)

    english_section = wikitext[english_start:english_end]

    # Find Noun section and print it
    noun_match = re.search(r'===\s*Noun\s*===', english_section)
    if noun_match:
        noun_start = noun_match.start()
        next_l3 = re.search(r'\n===', english_section[noun_match.end():])
        if next_l3:
            noun_end = noun_match.end() + next_l3.start()
        else:
            noun_end = len(english_section)

        noun_section = english_section[noun_start:noun_end]
        print("English Noun section:")
        print("=" * 60)
        print(noun_section[:500])  # Print first 500 chars
        print("=" * 60)

        # Check for the template
        if '{{wikidata lexeme|L8005}}' in noun_section:
            print("\n✓ Template successfully added!")
        else:
            print("\n✗ Template not found")

# Check the latest revision
revisions = list(page.revisions(limit=1))
if revisions:
    latest = revisions[0]
    print(f"\nLatest revision:")
    print(f"  User: {latest.get('user', 'Unknown')}")
    print(f"  Comment: {latest.get('comment', 'No comment')}")
