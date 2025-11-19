#!/usr/bin/env python3
"""
add_p1_q10_all_lexemes.py
=========================
Add P1 Q10 claim to ALL lexemes L1-L75 using Wikibase API.
Uses the correct claims structure (list format on Aelaki).
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
# ADD P1 Q10 TO ALL LEXEMES L1-L75
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("ADDING P1 Q10 TO ALL LEXEMES")
print("=" * 80)
print()

success_count = 0
failed = []
skipped = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"
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
            skipped.append(lex_id)
            continue

        current_content = pages[page_id]['revisions'][0]['*']
        current_lexeme = json.loads(current_content)

        # Build claim data following Aelaki's list format
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

        # Get existing claims (list format)
        existing_claims = current_lexeme.get('claims', [])
        if not isinstance(existing_claims, list):
            existing_claims = []

        # Check if P1 Q10 already exists
        already_exists = False
        for existing_claim in existing_claims:
            claim_prop = existing_claim.get('mainsnak', {}).get('property', '')
            claim_value = existing_claim.get('mainsnak', {}).get('datavalue', {}).get('value', {})
            if claim_prop == 'P1' and claim_value.get('numeric-id') == 10:
                already_exists = True
                break

        if already_exists:
            print(f"✓ (already has P1 Q10)")
            success_count += 1
            continue

        # Add the claim
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
            print(f"✗ ({result['error'].get('info', 'error')})")
            failed.append(lex_id)
        elif 'success' in result and result['success']:
            entity = result.get('entity', {})
            claims = entity.get('claims', [])

            # Verify in response
            if isinstance(claims, list) and len(claims) > 0:
                print(f"✓ (added)")
                success_count += 1

                # Verify persistence with fetch
                time.sleep(0.3)
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
                if not isinstance(saved_claims, list) or len(saved_claims) == 0:
                    print(f"     ⚠ WARNING: claim did NOT persist")
                    failed.append(lex_id)
                    success_count -= 1
            else:
                print(f"✗ (no claims in response)")
                failed.append(lex_id)
        else:
            print(f"✗ (no success)")
            failed.append(lex_id)

        time.sleep(0.5)

    except Exception as e:
        print(f"✗ ({str(e)[:50]})")
        failed.append(lex_id)

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✓ Successfully added P1 Q10: {success_count}")
if failed:
    print(f"✗ Failed: {', '.join(failed)}")
if skipped:
    print(f"⊘ Skipped (not found): {', '.join(skipped)}")

print()
if success_count == 75 or (success_count >= 73 and len(failed) <= 2):
    print("SUCCESS! P1 Q10 has been added to all (or almost all) lexemes!")
else:
    print(f"PARTIAL SUCCESS: {success_count}/75 lexemes updated")
