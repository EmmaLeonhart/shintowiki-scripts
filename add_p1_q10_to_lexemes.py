#!/usr/bin/env python3
"""
add_p1_q10_to_lexemes.py
=======================
Add P1 Q10 claim to all existing lexemes (L1-L75).

P1 Q10 appears to be a test property linking to Q10.
This will help determine if claims can be added via modification vs creation.
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
# ADD P1 Q10 TO ALL LEXEMES
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("ADDING P1 Q10 CLAIM TO LEXEMES")
print("=" * 80)
print()

# Test on a few first
test_lexemes = ['L68', 'L69', 'L70', 'L71', 'L75']

success_count = 0
failed = []

for lex_id in test_lexemes:
    print(f"Processing {lex_id}...", end=" ", flush=True)

    try:
        # Fetch current lexeme
        r = session.get(API_URL, params={
            'action': 'query',
            'titles': f'Lexeme:{lex_id}',
            'prop': 'revisions',
            'rvprop': 'content',
            'format': 'json'
        })
        pages = r.json()['query']['pages']
        page_id = list(pages.keys())[0]

        if 'revisions' not in pages[page_id]:
            print(f"✗ (not found)")
            failed.append(lex_id)
            continue

        current_content = pages[page_id]['revisions'][0]['*']
        current_lexeme = json.loads(current_content)

        # Build claim data
        claim = {
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

        # Get existing claims or create new list
        # NOTE: Aelaki stores claims as a list [], not dict with property keys
        existing_claims = current_lexeme.get('claims', [])
        if isinstance(existing_claims, dict):
            # If it's a dict (shouldn't be on Aelaki), convert to list
            existing_claims = []

        # Add P1 claim to the list
        existing_claims.append(claim)

        # Build edit data
        edit_data = {
            'claims': existing_claims
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
            print(f"✗ ({result['error'].get('info', 'unknown error')})")
            failed.append(lex_id)
        elif 'success' in result and result['success']:
            entity = result.get('entity', {})
            claims = entity.get('claims', [])

            if isinstance(claims, list) and len(claims) > 0:
                p1_count = len(claims)
                print(f"✓ (claims in response: {p1_count})")
                success_count += 1

                # Verify persistence
                time.sleep(0.5)
                r = session.get(API_URL, params={
                    'action': 'query',
                    'titles': f'Lexeme:{lex_id}',
                    'prop': 'revisions',
                    'rvprop': 'content',
                    'format': 'json'
                })
                pages = r.json()['query']['pages']
                page_id = list(pages.keys())[0]
                saved_content = pages[page_id]['revisions'][0]['*']
                saved_lexeme = json.loads(saved_content)

                saved_claims = saved_lexeme.get('claims', [])
                if isinstance(saved_claims, list) and len(saved_claims) > 0:
                    print(f"     ✓ Verified: {len(saved_claims)} claims persisted")
                else:
                    print(f"     ✗ FAILED: claims did NOT persist")
                    failed.append(lex_id)
                    success_count -= 1
            else:
                print(f"✗ (no claims in response)")
                failed.append(lex_id)
        else:
            print(f"✗ (no success indicator)")
            failed.append(lex_id)

        time.sleep(1)

    except Exception as e:
        print(f"✗ ({e})")
        failed.append(lex_id)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✓ Successfully added P1 Q10: {success_count}")
if failed:
    print(f"✗ Failed: {', '.join(failed)}")
print()

if success_count > 0:
    print("SUCCESS! Claims CAN be added to existing lexemes via modification.")
    print("This means:")
    print("  - Claims work for EXISTING lexemes")
    print("  - Claims fail for NEW lexeme creation")
    print("  - The claims infrastructure works, but creation has issues")
elif success_count == 0:
    print("FAILED. Claims cannot be added even to existing lexemes.")
    print("This means:")
    print("  - Claims infrastructure is completely broken")
    print("  - Even modification doesn't work")
