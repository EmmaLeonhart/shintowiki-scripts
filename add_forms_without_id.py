#!/usr/bin/env python3
"""
Add Forms Without Specifying ID
================================
Try creating forms by not specifying an ID - let Wikibase auto-generate it.
"""

import requests
import json
import sys
import io
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_1]'

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# Login
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']

r = session.post(API_URL, data={
    'action': 'login',
    'lgname': USERNAME,
    'lgpassword': PASSWORD,
    'lgtoken': login_token,
    'format': 'json'
})

r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

print("Testing form creation without specifying ID...")
print()

# Test with L1
lex_id = 'L1'
print(f"Attempting to create form without ID on {lex_id}...")

# Try form without ID (let Wikibase auto-generate)
form_data = {
    'representations': {
        'mis': {
            'language': 'mis',
            'value': 'form-test'
        }
    },
    'grammaticalFeatures': [],
    'claims': []
}

edit_data = {'forms': [form_data]}

r = session.post(API_URL, data={
    'action': 'wbeditentity',
    'id': lex_id,
    'data': json.dumps(edit_data),
    'token': csrf_token,
    'format': 'json'
})

result = r.json()

print("Response:")
print(json.dumps(result, indent=2)[:500])
