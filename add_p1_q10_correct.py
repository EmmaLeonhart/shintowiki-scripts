#!/usr/bin/env python3
"""
add_p1_q10_correct.py
======================
Add P1 Q10 claim to ALL lexemes L1-L75 using the CONFIRMED WORKING method.
Based on comprehensive API testing that showed claims work in dict format.
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

# ═══════════════════════════════════════════════════════════════════════════
# LOGIN & TOKENS
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("AUTHENTICATION")
print("=" * 80)

try:
    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
    login_token = r.json()['query']['tokens']['logintoken']

    r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
    if r.json().get('login', {}).get('result') != 'Success':
        print("✗ Login failed")
        sys.exit(1)
    print("✓ Logged in")

    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
    csrf_token = r.json()['query']['tokens']['csrftoken']
    print("✓ Got CSRF token\n")
except Exception as e:
    print(f"✗ Auth failed: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# ADD P1 Q10 TO ALL LEXEMES L1-L75 (USING CONFIRMED WORKING FORMAT)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("ADDING P1 Q10 TO ALL LEXEMES (USING WORKING METHOD)")
print("=" * 80)
print()

success_count = 0
failed = []
skipped = []
already_has = []

# The claim structure that WORKS (dict format with property keys)
p1_q10_claim = {
    'mainsnak': {
        'snaktype': 'value',
        'property': 'P1',
        'datavalue': {
            'value': {
                'entity-type': 'item',
                'numeric-id': 10
            },
            'type': 'wikibase-entityid'
        }
    },
    'type': 'statement',
    'rank': 'normal'
}

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"
    print(f"Processing {lex_id}...", end=" ", flush=True)

    try:
        # Fetch current lexeme to check if P1 Q10 already exists
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': lex_id,
            'format': 'json'
        })
        result = r.json()

        if 'entities' not in result or lex_id not in result['entities']:
            print(f"✗ (not found)")
            skipped.append(lex_id)
            continue

        entity = result['entities'][lex_id]

        # Check if it's an error (missing entity)
        if 'missing' in entity:
            print(f"✗ (not found)")
            skipped.append(lex_id)
            continue

        # Check if P1 Q10 already exists
        claims = entity.get('claims', {})
        if isinstance(claims, dict) and 'P1' in claims:
            # Check if Q10 is already in P1 claims
            for claim in claims['P1']:
                value = claim.get('mainsnak', {}).get('datavalue', {}).get('value', {})
                if isinstance(value, dict) and value.get('numeric-id') == 10:
                    print(f"✓ (already has P1 Q10)")
                    already_has.append(lex_id)
                    success_count += 1
                    time.sleep(0.2)
                    continue

        # Build edit data using DICT FORMAT (which we confirmed works)
        edit_data = {
            'claims': {
                'P1': [p1_q10_claim]
            }
        }

        # Send to API
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': lex_id,
            'data': json.dumps(edit_data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            error_info = result['error'].get('info', result['error'].get('code'))
            print(f"✗ ({error_info[:40]})")
            failed.append(lex_id)
        elif 'success' in result and result['success']:
            entity = result.get('entity', {})
            claims = entity.get('claims', {})

            # Check if claim appeared in response
            if isinstance(claims, dict) and 'P1' in claims and len(claims['P1']) > 0:
                print(f"✓ (added)")
                success_count += 1

                # Verify persistence with fetch
                time.sleep(0.2)
                r = session.get(API_URL, params={
                    'action': 'wbgetentities',
                    'ids': lex_id,
                    'format': 'json'
                })
                verify = r.json()

                if lex_id in verify.get('entities', {}):
                    saved_claims = verify['entities'][lex_id].get('claims', {})
                    if isinstance(saved_claims, dict) and 'P1' in saved_claims and len(saved_claims['P1']) > 0:
                        # Confirmed persistent
                        pass
                    else:
                        print(f"     ⚠ WARNING: claim did NOT persist")
                        failed.append(lex_id)
                        success_count -= 1
            else:
                print(f"✗ (no claims in response)")
                failed.append(lex_id)
        else:
            print(f"✗ (no success indicator)")
            failed.append(lex_id)

        time.sleep(0.3)

    except Exception as e:
        print(f"✗ ({str(e)[:40]})")
        failed.append(lex_id)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✓ Successfully added P1 Q10: {success_count}")
if already_has:
    print(f"⟳ Already had P1 Q10: {len(already_has)}")
if failed:
    print(f"✗ Failed: {', '.join(failed)}")
if skipped:
    print(f"⊘ Skipped (not found): {', '.join(skipped)}")

print()
total_processed = success_count + len(already_has)
if total_processed >= 74:
    print(f"SUCCESS! P1 Q10 has been added to all (or almost all) lexemes!")
    print(f"Total with P1 Q10: {total_processed}/75")
else:
    print(f"PARTIAL SUCCESS: {total_processed}/75 lexemes have P1 Q10")
