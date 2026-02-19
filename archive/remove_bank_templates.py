#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Remove the incorrectly added templates from bank."""

import mwclient
import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BOT_USERNAME = 'Immanuelle@ImmanuelleWiktionaryTest'
BOT_PASSWORD = 'qi6v2vi4s0p3bvr6d1lium2n2d7l4930'
USER_AGENT = 'WiktionaryLexemeBot/1.0 (User:Immanuelle) Python/mwclient'

site = mwclient.Site('en.wiktionary.org', clients_useragent=USER_AGENT)
site.login(BOT_USERNAME, BOT_PASSWORD)

page = site.pages['bank']
wikitext = page.text()

# Remove all {{wikidata lexeme|...}} templates
modified = re.sub(r'\n\{\{wikidata lexeme\|L\d+\}\}', '', wikitext)

if modified != wikitext:
    page.save(modified, summary='Removing incorrectly added lexeme templates (bot error - multiple POS sections should have been skipped)')
    print("✓ Removed templates from bank")
else:
    print("No changes needed")
