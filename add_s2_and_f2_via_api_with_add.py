#!/usr/bin/env python3
"""
Add S2 Sense and F2 Form via API using "add" syntax
====================================================
Try using the "add": "" syntax in the JSON payload
which should tell Wikibase to auto-generate the ID.
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

print("Testing 'add' syntax for creating new senses and forms...")
print()

# Test with L1
lex_id = 'L1'
print(f"Attempting to add S2 sense and F2 form to {lex_id} using 'add' syntax...")
print()

# Try using "add" syntax
edit_data = {
    'senses': [{
        'add': '',
        'glosses': {
            'en': {
                'language': 'en',
                'value': 'Second sense via add syntax'
            }
        }
    }],
    'forms': [{
        'add': '',
        'representations': {
            'mis': {
                'language': 'mis',
                'value': 'form2-via-add'
            }
        },
        'grammaticalFeatures': [],
        'claims': []
    }]
}

r = session.post(API_URL, data={
    'action': 'wbeditentity',
    'id': lex_id,
    'data': json.dumps(edit_data),
    'token': csrf_token,
    'format': 'json'
})

result = r.json()

print("Response:")
if 'error' in result:
    print(f"✗ Error: {result['error'].get('code')}")
    print(f"  {result['error'].get('info')}")
elif 'entity' in result:
    entity = result['entity']
    senses = entity.get('senses', [])
    forms = entity.get('forms', [])
    print(f"✓ Success!")
    print(f"  Senses: {len(senses)}")
    for sense in senses:
        print(f"    - {sense.get('id')}")
    print(f"  Forms: {len(forms)}")
    for form in forms:
        print(f"    - {form.get('id')}")
else:
    print(f"? Unexpected response:")
    print(json.dumps(result, indent=2)[:500])
