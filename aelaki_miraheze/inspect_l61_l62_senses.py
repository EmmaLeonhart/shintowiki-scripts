#!/usr/bin/env python3
"""
inspect_l61_l62_senses.py
=========================
Inspect the complete structure of senses in L61 and L62 (the working ones).
"""

import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# Login
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']
r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})

# Get L61 and L62
for lex_id in ['L61', 'L62']:
    print("=" * 80)
    print(f"{lex_id} COMPLETE SENSE STRUCTURE")
    print("=" * 80)
    print()

    r = session.get(API_URL, params={
        'action': 'wbgetentities',
        'ids': lex_id,
        'format': 'json'
    })
    result = r.json()

    if 'entities' in result and lex_id in result['entities']:
        entity = result['entities'][lex_id]
        senses = entity.get('senses', {})

        print(f"Senses count: {len(senses)}")
        print()
        print("Full sense structure:")
        print(json.dumps(senses, indent=2))
        print()
