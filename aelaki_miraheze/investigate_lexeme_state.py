#!/usr/bin/env python3
"""
investigate_lexeme_state.py
============================
Investigate the actual state of lexemes on Aelaki.
Check which lexemes exist, their structure, and try senses on known working lexemes.
"""

import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

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
    print("✓ Logged in\n")

    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
    csrf_token = r.json()['query']['tokens']['csrftoken']
except Exception as e:
    print(f"✗ Auth failed: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# CHECK WHICH LEXEMES EXIST
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("CHECKING EXISTING LEXEMES")
print("=" * 80)
print()

# Test a range of lexeme IDs
test_lex_ids = [f'L{i}' for i in range(1, 11)] + [f'L{i}' for i in range(60, 76)]

existing_lexemes = []

for lex_id in test_lex_ids:
    try:
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': lex_id,
            'format': 'json'
        })
        result = r.json()

        if 'entities' in result and lex_id in result['entities']:
            entity = result['entities'][lex_id]

            if 'missing' not in entity:
                lemmas = entity.get('lemmas', {})
                lemma_str = list(lemmas.values())[0].get('value', '?') if lemmas else 'NO_LEMMA'
                senses = entity.get('senses', {})
                sense_count = len(senses) if isinstance(senses, (dict, list)) else 0

                print(f"{lex_id}: Lemma='{lemma_str}', Senses={sense_count}")
                existing_lexemes.append(lex_id)
    except Exception as e:
        pass

print()
print(f"Found {len(existing_lexemes)} existing lexemes: {', '.join(existing_lexemes)}")
print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SENSES ON FIRST EXISTING LEXEME
# ═══════════════════════════════════════════════════════════════════════════

if existing_lexemes:
    test_lex = existing_lexemes[0]
    print("=" * 80)
    print(f"TESTING SENSE ADDITION ON {test_lex}")
    print("=" * 80)
    print()

    # Test 1: Proper sense format with English language
    print(f"Test 1: Add sense with proper English language specification")
    try:
        edit_data = {
            'senses': {
                f'{test_lex}-S1': {
                    'glosses': {
                        'en': {
                            'language': 'en',
                            'value': 'Test English gloss'
                        }
                    }
                }
            }
        }

        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': test_lex,
            'data': json.dumps(edit_data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            print(f"  ✗ Error: {result['error'].get('code')}")
            print(f"    Info: {result['error'].get('info', '')[:70]}")
        elif 'entity' in result:
            entity = result['entity']
            senses = entity.get('senses', {})
            if senses:
                print(f"  ✓ Success! {len(senses)} senses in response")
                # Print first sense structure
                first_sense_id = list(senses.keys())[0]
                first_sense = senses[first_sense_id]
                print(f"    Sense ID: {first_sense_id}")
                print(f"    Glosses: {first_sense.get('glosses', {})}")
            else:
                print(f"  ✗ Success response but no senses")
        else:
            print(f"  ✗ Unexpected response: {list(result.keys())}")
    except Exception as e:
        print(f"  ✗ Exception: {e}")

    print()

    # Test 2: Check what persisted
    print(f"Test 2: Verify {test_lex} current state after edit")
    try:
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': test_lex,
            'format': 'json'
        })
        result = r.json()

        if 'entities' in result and test_lex in result['entities']:
            entity = result['entities'][test_lex]
            senses = entity.get('senses', {})
            print(f"  Senses persisted: {len(senses) if isinstance(senses, (dict, list)) else 0}")
            if senses and isinstance(senses, dict):
                for sense_id, sense_data in list(senses.items())[:2]:
                    print(f"    {sense_id}: {sense_data.get('glosses', {})}")
    except Exception as e:
        print(f"  ✗ Query failed: {e}")

    print()

    # Test 3: Try different sense structure (minimal)
    print(f"Test 3: Add sense with minimal structure")
    try:
        edit_data = {
            'senses': {
                f'{test_lex}-S2': {
                    'glosses': {
                        'en': 'Just a string gloss'
                    }
                }
            }
        }

        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': test_lex,
            'data': json.dumps(edit_data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            print(f"  ✗ Error: {result['error'].get('code')}")
        elif 'entity' in result and result['entity'].get('senses'):
            print(f"  ✓ Success!")
        else:
            print(f"  ✗ No success or senses in response")
    except Exception as e:
        print(f"  ✗ Exception: {e}")

    print()

    # Test 4: Query L61 (the one we know has claims)
    print("=" * 80)
    print("DETAILED INSPECTION OF L61 (KNOWN WORKING LEXEME)")
    print("=" * 80)
    print()

    try:
        r = session.get(API_URL, params={
            'action': 'wbgetentities',
            'ids': 'L61',
            'format': 'json'
        })
        result = r.json()

        if 'entities' in result and 'L61' in result['entities']:
            L61 = result['entities']['L61']

            print("L61 Structure:")
            print(f"  ID: {L61.get('id')}")
            print(f"  Type: {L61.get('type')}")
            print(f"  Lemmas: {L61.get('lemmas', {})}")
            print(f"  Language: {L61.get('language')}")
            print(f"  Lexical Category: {L61.get('lexicalCategory')}")

            senses = L61.get('senses', {})
            print(f"  Senses: {len(senses) if isinstance(senses, (dict, list)) else 0}")
            if isinstance(senses, dict) and senses:
                print(f"    Sense IDs: {list(senses.keys())[:3]}")

            claims = L61.get('claims', {})
            print(f"  Claims: {list(claims.keys())}")

            forms = L61.get('forms', {})
            print(f"  Forms: {len(forms) if isinstance(forms, (dict, list)) else 0}")

            print()
            print("Raw JSON structure (first 500 chars):")
            print(json.dumps(L61, indent=2)[:500])
    except Exception as e:
        print(f"✗ Failed to inspect L61: {e}")
else:
    print("✗ No lexemes found to test with!")
