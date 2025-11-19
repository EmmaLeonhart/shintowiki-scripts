#!/usr/bin/env python3
"""
Add Dummy Senses Via API
========================
Use the bulk API to add dummy senses to all lexemes that don't have them.
We know the API can modify existing senses (L61 works), so let's try to
force-add new senses via incremental updates.
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
print("BULK ADD DUMMY SENSES TO ALL LEXEMES")
print("=" * 80)
print()

success = []
failed = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"

    print(f"Adding sense to {lex_id:15}", end=" ", flush=True)

    try:
        # Create dummy sense for this lexeme
        sense_data = {
            'id': f'{lex_id}-S1',
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': f'Sense for {lex_id}'
                }
            },
            'claims': []
        }

        # Build edit data with just the sense
        edit_data = {
            'senses': [sense_data]
        }

        # Try to add the sense via API
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

            # Check if the sense actually appeared
            if isinstance(senses, list) and len(senses) > 0:
                has_our_sense = any(s.get('id') == f'{lex_id}-S1' for s in senses)
                if has_our_sense:
                    print(f"✓ (created)")
                    success.append(lex_id)
                else:
                    print(f"✗ (not in response)")
                    failed.append(lex_id)
            else:
                print(f"✗ (no senses in response)")
                failed.append(lex_id)
        else:
            print(f"✗ (unexpected response)")
            failed.append(lex_id)

        time.sleep(0.5)

    except Exception as e:
        print(f"✗ ({str(e)[:30]})")
        failed.append(lex_id)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✓ Created: {len(success)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  Failed lexemes: {', '.join(failed)}")

print()
if len(success) >= 73:
    print(f"SUCCESS! {len(success)}/75 lexemes now have senses!")
else:
    print(f"Partial: {len(success)}/75 sense additions successful")
