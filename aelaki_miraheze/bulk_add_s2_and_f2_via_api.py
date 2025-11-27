#!/usr/bin/env python3
"""
Bulk Add S2 Sense and F2 Form to ALL Lexemes
=============================================
Use the "add": "" syntax to auto-generate and add new senses and forms.
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
print("BULK ADD S2 SENSE AND F2 FORM TO ALL LEXEMES")
print("=" * 80)
print()

success = []
failed = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"

    print(f"Adding S2/F2 to {lex_id:15}", end=" ", flush=True)

    try:
        # Use "add": "" syntax to auto-generate sense and form IDs
        edit_data = {
            'senses': [{
                'add': '',
                'glosses': {
                    'en': {
                        'language': 'en',
                        'value': f'Second sense for {lex_id}'
                    }
                }
            }],
            'forms': [{
                'add': '',
                'representations': {
                    'mis': {
                        'language': 'mis',
                        'value': f'form2-{lex_id}'
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
            senses = entity.get('senses', [])
            forms = entity.get('forms', [])

            # Check if we have at least 2 senses and 2 forms
            if len(senses) >= 2 and len(forms) >= 2:
                print(f"✓")
                success.append(lex_id)
            else:
                print(f"✗ (not added: {len(senses)}S/{len(forms)}F)")
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
print(f"✓ Added S2/F2: {len(success)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  Failed lexemes: {', '.join(failed)}")

print()
if len(success) >= 73:
    print(f"SUCCESS! {len(success)}/75 lexemes now have S2 and F2!")
else:
    print(f"Partial: {len(success)}/75 lexemes updated")
