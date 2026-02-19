#!/usr/bin/env python3
import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

site = mwclient.Site('shinto.miraheze.org', path='/w/')
site.login('Immanuelle', '[REDACTED_SECRET_2]')

result = site.api('undelete',
                 title='Ōarahiko Shrine',
                 reason='Restoring for retry',
                 token=site.get_token('delete'))
print(result)
