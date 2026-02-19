#!/usr/bin/env python3
import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

site = mwclient.Site('shinto.miraheze.org', path='/w/')
site.login('Immanuelle', '[REDACTED_SECRET_2]')
page = site.pages['Azusawakenomikoto Shrine']
text = page.text()

# Remove the translated template to allow rerun
text = text.split('{{translated page|')[0].strip()
text = text.replace('[[Category:Automerged Japanese text]]', '').strip()

# Remove Japanese section
if '== Japanese Wikipedia content ==' in text:
    text = text.split('== Japanese Wikipedia content ==')[0].strip()

page.save(text, summary='Preparing for retest')
print('Cleaned up page')
