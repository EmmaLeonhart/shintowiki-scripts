#!/usr/bin/env python3
"""
Simple test to check Japanese Wikipedia connection
"""

import sys
import io
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("Attempting to connect to Japanese Wikipedia...", flush=True)

try:
    # Try with timeout
    site = mwclient.Site('ja.wikipedia.org',
                         clients_useragent='ShikinaishaBotScript/1.0 (Contact: User on shinto.miraheze.org)')
    print("Connected successfully!", flush=True)

    # Try to fetch a simple page
    print("Attempting to fetch 式内社 page...", flush=True)
    page = site.pages['式内社']
    print(f"Page exists: {page.exists}", flush=True)

    if page.exists:
        text = page.text()
        print(f"Page length: {len(text)} characters", flush=True)
        print("Success!", flush=True)

except Exception as e:
    print(f"Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
