#!/usr/bin/env python3
import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

site = mwclient.Site('shinto.miraheze.org', path='/w/')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

page = site.pages['Azusawakenomikoto Shrine']
page.delete(reason='Testing full history import')
print("Deleted Azusawakenomikoto Shrine")

# Also delete the Japanese page if it exists
ja_page = site.pages['阿豆佐和気命神社']
if ja_page.exists:
    ja_page.delete(reason='Cleanup')
    print("Deleted 阿豆佐和気命神社")
