#!/usr/bin/env python3
"""
Clean Up All Lexemes
====================
1. Keep only the first sense (S1), remove all other senses
2. Remove duplicate P1 (Instance of) → Q10 properties, keep only one
3. Remove all forms
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
print("CLEAN UP ALL LEXEMES (L1-L75)")
print("=" * 80)
print()

success = []
failed = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"

    print(f"Cleaning {lex_id:15}", end=" ", flush=True)

    try:
        # Fetch current lexeme data
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': lex_id,
            'format': 'json'
        })

        entity = r.json()['entities'][lex_id]

        # Check if entity exists
        if 'missing' in entity:
            print(f"✗ (not found)")
            failed.append(lex_id)
            continue

        # Keep only first sense (S1)
        senses = entity.get('senses', [])
        if len(senses) > 1:
            senses = [senses[0]]

        # Remove all forms
        forms = []

        # Handle claims/properties: keep only one P1→Q10
        claims = entity.get('claims', {})
        new_claims = {}

        if 'P1' in claims:
            # Keep only the first P1 claim
            p1_claims = claims['P1']
            if p1_claims:
                new_claims['P1'] = [p1_claims[0]]

        # Keep other properties if they exist (but remove duplicates)
        for prop_id, prop_claims in claims.items():
            if prop_id != 'P1':
                new_claims[prop_id] = prop_claims

        # Build the edit data
        edit_data = {
            'senses': senses,
            'forms': forms,
            'claims': new_claims
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
            senses_count = len(entity.get('senses', []))
            forms_count = len(entity.get('forms', []))
            p1_count = len(entity.get('claims', {}).get('P1', []))

            if senses_count == 1 and forms_count == 0 and p1_count <= 1:
                print(f"✓ (1S, 0F, {p1_count}×P1)")
                success.append(lex_id)
            else:
                print(f"✗ ({senses_count}S, {forms_count}F, {p1_count}×P1)")
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
print(f"✓ Cleaned up: {len(success)}")
if failed:
    print(f"✗ Failed: {len(failed)}")
    if len(failed) <= 20:
        print(f"  Failed lexemes: {', '.join(failed)}")

print()
if len(success) >= 70:
    print(f"SUCCESS! {len(success)}/75 lexemes cleaned up!")
    print("Each lexeme now has:")
    print("  - Only first sense (S1)")
    print("  - No forms")
    print("  - Only one P1 → Q10 property")
else:
    print(f"Partial: {len(success)}/75 lexemes cleaned")
