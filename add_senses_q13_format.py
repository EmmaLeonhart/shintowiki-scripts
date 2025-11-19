#!/usr/bin/env python3
"""
add_senses_q13_format.py
========================
Add senses to lexemes using Q13 as the sense identifier.
Format: L{num}-Q13 instead of L{num}-S1
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
# LOGIN
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
# ADD SENSES WITH Q13 IDENTIFIER
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("ADDING SENSES WITH Q13 IDENTIFIER")
print("=" * 80)
print()

success_count = 0
failed = []
skipped = []

for lex_num in range(1, 76):
    lex_id = f"L{lex_num}"
    sense_id = f"{lex_id}-Q13"

    print(f"Processing {lex_id}...", end=" ", flush=True)

    try:
        # Build sense data with Q13 as identifier
        edit_data = {
            'senses': {
                sense_id: {
                    'glosses': {
                        'en': {
                            'language': 'en',
                            'value': f'Sense for {lex_id}'
                        }
                    }
                }
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
        elif 'entity' in result:
            entity = result.get('entity', {})
            senses = entity.get('senses', {})

            if senses:
                print(f"✓ (sense added)")
                success_count += 1

                # Verify persistence
                time.sleep(0.2)
                r = session.get(API_URL, params={
                    'action': 'wbgetentities',
                    'ids': lex_id,
                    'format': 'json'
                })
                verify = r.json()

                if lex_id in verify.get('entities', {}):
                    saved_senses = verify['entities'][lex_id].get('senses', [])
                    if isinstance(saved_senses, (list, dict)) and saved_senses:
                        # Verified
                        pass
                    else:
                        print(f"     ⚠ WARNING: sense did NOT persist")
                        failed.append(lex_id)
                        success_count -= 1
            else:
                print(f"✗ (no senses in response)")
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
print(f"✓ Successfully added senses (Q13): {success_count}")
if failed:
    print(f"✗ Failed: {', '.join(failed)}")
if skipped:
    print(f"⊘ Skipped: {', '.join(skipped)}")

print()
if success_count >= 73:
    print(f"SUCCESS! Q13 senses added to {success_count}/75 lexemes!")
else:
    print(f"PARTIAL SUCCESS: {success_count}/75 lexemes updated with Q13 senses")
