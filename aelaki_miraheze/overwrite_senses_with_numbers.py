#!/usr/bin/env python3
"""
Overwrite Senses with Numbers
==============================
For each lexeme L1-L69 that now has a sense, overwrite the gloss
so that L1's sense gloss is "1", L2's sense gloss is "2", etc.
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
print("BULK OVERWRITE SENSE GLOSSES WITH LEXEME NUMBERS")
print("=" * 80)
print()

success = []
failed = []

for lex_num in range(1, 70):
    lex_id = f"L{lex_num}"

    print(f"Updating {lex_id} sense gloss to '{lex_num}':       ", end=" ", flush=True)

    try:
        # Get current lexeme to get the sense ID
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': lex_id,
            'format': 'json'
        })

        entity = r.json()['entities'].get(lex_id, {})
        senses = entity.get('senses', [])

        if not senses:
            print(f"✗ (no senses found)")
            failed.append(lex_id)
            continue

        # Update each sense to have the lexeme number as the gloss
        updated_senses = []
        for sense in senses:
            updated_sense = {
                'id': sense.get('id'),
                'glosses': {
                    'en': {
                        'language': 'en',
                        'value': str(lex_num)
                    }
                },
                'claims': sense.get('claims', [])
            }
            updated_senses.append(updated_sense)

        # Send the update
        edit_data = {'senses': updated_senses}

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

            # Verify the gloss was updated
            if senses and senses[0].get('glosses', {}).get('en', {}).get('value') == str(lex_num):
                print(f"✓")
                success.append(lex_id)
            else:
                print(f"✗ (gloss not updated)")
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
print(f"✓ Updated: {len(success)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  Failed lexemes: {', '.join(failed)}")

print()
if len(success) >= 68:
    print(f"SUCCESS! {len(success)}/69 sense glosses updated to their lexeme numbers!")
else:
    print(f"Partial: {len(success)}/69 updates successful")
