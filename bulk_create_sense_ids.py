#!/usr/bin/env python3
"""
bulk_create_sense_ids.py
========================
BULK CREATE sense IDs on all lexemes by copying the L61/L62 working pattern.
Directly inject sense ID structure using the raw data that works on L61/L62.
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
r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

print("=" * 80)
print("BULK CREATING SENSE IDs USING L61/L62 WORKING PATTERN")
print("=" * 80)
print()

# L61 WORKING PATTERN (what we know works)
l61_pattern = {
    "senses": [
        {
            "id": "SENSE_ID_PLACEHOLDER",
            "glosses": {
                "en": {
                    "language": "en",
                    "value": "New sense"
                }
            },
            "claims": []
        }
    ]
}

success = []
failed = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"
    sense_id = f"{lex_id}-Q13"

    print(f"Creating sense ID {sense_id:15}", end=" ", flush=True)

    try:
        # Fetch current lexeme to get full structure
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': lex_id,
            'format': 'json'
        })
        result = r.json()

        if lex_id not in result.get('entities', {}):
            print("✗ (lexeme not found)")
            failed.append(lex_id)
            continue

        entity = result['entities'][lex_id]
        existing_senses = entity.get('senses', [])

        # Check if sense already exists
        if isinstance(existing_senses, list):
            for sense in existing_senses:
                if sense.get('id') == sense_id:
                    print("✓ (already exists)")
                    success.append(lex_id)
                    time.sleep(0.1)
                    continue

        # Prepare new senses array
        new_senses = list(existing_senses) if isinstance(existing_senses, list) else []

        # Create new sense using L61 pattern
        new_sense = {
            "id": sense_id,
            "glosses": {
                "en": {
                    "language": "en",
                    "value": f"Sense for {lex_id}"
                }
            },
            "claims": []
        }

        new_senses.append(new_sense)

        # Send edit
        edit_data = {'senses': new_senses}

        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': lex_id,
            'data': json.dumps(edit_data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            error_info = result['error'].get('info', result['error'].get('code'))[:30]
            print(f"✗ ({error_info})")
            failed.append(lex_id)
        elif 'entity' in result:
            entity = result['entity']
            senses = entity.get('senses', [])

            if isinstance(senses, list) and any(s.get('id') == sense_id for s in senses):
                print("✓ (created)")
                success.append(lex_id)
            else:
                print("✗ (not in response)")
                failed.append(lex_id)
        else:
            print("✗ (unexpected)")
            failed.append(lex_id)

        time.sleep(0.2)

    except Exception as e:
        print(f"✗ ({str(e)[:30]})")
        failed.append(lex_id)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✓ Created/Verified: {len(success)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  {', '.join(failed)}")

print()
if len(success) >= 74:
    print(f"SUCCESS! Sense IDs created on {len(success)}/75 lexemes!")
else:
    print(f"Partial: {len(success)}/75 sense IDs ready")
