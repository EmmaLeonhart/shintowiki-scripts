#!/usr/bin/env python3
"""
Add Forms to All Lexemes
========================
Attempt to add F2 form to all lexemes (L1-L69).
We'll try appending to the forms array using wbeditentity.
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
print("BULK ADD FORMS TO ALL LEXEMES (L1-L69)")
print("=" * 80)
print()

success = []
failed = []
already_had = []

for lex_num in range(1, 70):
    lex_id = f"L{lex_num}"

    print(f"Adding form F2 to {lex_id:15}", end=" ", flush=True)

    try:
        # Get current lexeme to check forms
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': lex_id,
            'format': 'json'
        })

        entity = r.json()['entities'].get(lex_id, {})
        current_forms = entity.get('forms', [])

        # Check if F2 already exists
        if any(f.get('id') == f'{lex_id}-F2' for f in current_forms):
            print(f"✓ (already exists)")
            already_had.append(lex_id)
            continue

        # Create new F2 form
        new_form = {
            'id': f'{lex_id}-F2',
            'representations': {
                'mis': {
                    'language': 'mis',
                    'value': f'form2-{lex_id}'
                }
            },
            'grammaticalFeatures': [],
            'claims': []
        }

        # Add to forms array
        updated_forms = list(current_forms) if isinstance(current_forms, list) else []
        updated_forms.append(new_form)

        # Send update
        edit_data = {'forms': updated_forms}

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

            # Check if F2 is in the response
            has_f2 = any(f.get('id') == f'{lex_id}-F2' for f in forms)
            if has_f2:
                print(f"✓ (created)")
                success.append(lex_id)
            else:
                print(f"✗ (silently dropped)")
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
print(f"✓ Created: {len(success)}")
if already_had:
    print(f"✓ Already existed: {len(already_had)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  Failed lexemes: {', '.join(failed)}")

print()
total = len(success) + len(already_had)
if total >= 68:
    print(f"SUCCESS! {total}/69 lexemes now have F2 forms!")
else:
    print(f"Partial: {len(success)}/69 F2 forms created successfully")
    if len(failed) > 0:
        print(f"Note: Forms may be silently discarded by the API (known limitation)")
