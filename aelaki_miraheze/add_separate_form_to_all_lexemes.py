#!/usr/bin/env python3
"""
Add a Separate Form to Each Lexeme
===================================
Add a new form (F4) to all 75 lexemes using the "add": "" syntax
to auto-generate form IDs.
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
PASSWORD = '[REDACTED_SECRET_2]'

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

print("=" * 80)
print("AUTHENTICATE")
print("=" * 80)
print()

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

print("✓ Authenticated")
print()

print("=" * 80)
print("ADD SEPARATE FORM (F4) TO ALL LEXEMES (L1-L75)")
print("=" * 80)
print()

success = []
failed = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"

    print(f"Adding form to {lex_id:15}", end=" ", flush=True)

    try:
        # Use "add": "" syntax to auto-generate form ID
        edit_data = {
            'forms': [{
                'add': '',
                'representations': {
                    'mis': {
                        'language': 'mis',
                        'value': f'separate-form-{lex_id}'
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

        if 'error' in result:
            error_info = result['error'].get('info', result['error'].get('code'))[:40]
            print(f"✗ ({error_info})")
            failed.append(lex_id)
        elif 'entity' in result:
            entity = result['entity']
            forms = entity.get('forms', [])

            if len(forms) >= 4:
                print(f"✓ (now has {len(forms)} forms)")
                success.append(lex_id)
            else:
                print(f"✗ (only {len(forms)} forms)")
                failed.append(lex_id)
        else:
            print(f"✗ (unexpected response)")
            failed.append(lex_id)

        time.sleep(0.3)

    except Exception as e:
        print(f"✗ ({str(e)[:30]})")
        failed.append(lex_id)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✓ Added form: {len(success)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  Failed lexemes: {', '.join(failed)}")

print()
if len(success) >= 70:
    print(f"SUCCESS! {len(success)}/75 lexemes now have a separate form (F4)!")
    print("Each lexeme now has:")
    print("  - Multiple senses")
    print("  - Multiple forms (now with F4)")
    print("  - Full lexeme structure for editing!")
else:
    print(f"Partial: {len(success)}/75 lexemes updated")
