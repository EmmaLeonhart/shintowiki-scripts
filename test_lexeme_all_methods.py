#!/usr/bin/env python3
"""
test_lexeme_all_methods.py
===========================
Comprehensive test of ALL Wikibase Lexeme API methods to determine
exactly which operations work and which fail.

Tests:
1. wbladdsense (dedicated sense creation endpoint)
2. wbladdform (dedicated form creation endpoint)
3. wbeditentity (general entity edit endpoint)
4. Direct JSON payload modifications

This is the "final authority" test to diagnose Lexeme backend capability.
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

# ═══════════════════════════════════════════════════════════════════════════
# LOGIN & TOKENS
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("AUTHENTICATION & SETUP")
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
# TEST 1: Create a test lexeme
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 1: Create Test Lexeme (L-debug-test-1)")
print("=" * 80)

test_lexeme_id = None

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps({
            'type': 'lexeme',
            'language': 'Q1',
            'lexicalCategory': 'Q4',
            'lemmas': {
                'mis': {
                    'language': 'mis',
                    'value': 'debugtest'
                }
            }
        }),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'error' in result:
        print(f"✗ Error: {result['error']}")
    else:
        test_lexeme_id = result.get('entity', {}).get('id')
        print(f"✓ Created: {test_lexeme_id}")
        print(f"  Response: {json.dumps(result['entity'], indent=2)}\n")

except Exception as e:
    print(f"✗ Exception: {e}\n")

if not test_lexeme_id:
    print("Cannot continue without lexeme")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Try wbladdsense endpoint
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print(f"TEST 2: Add Sense via wbladdsense to {test_lexeme_id}")
print("=" * 80)

try:
    print("Payload:")
    print(f"  action: wbladdsense")
    print(f"  lexemeId: {test_lexeme_id}")
    print(f"  glosses: {{\"en\":{{\"language\":\"en\",\"value\":\"test meaning\"}}}}")

    r = session.post(API_URL, data={
        'action': 'wbladdsense',
        'lexemeId': test_lexeme_id,
        'glosses': json.dumps({'en': {'language': 'en', 'value': 'test meaning'}}),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    print(f"\nResponse:")
    print(json.dumps(result, indent=2))

    if 'error' in result:
        print(f"\n✗ wbladdsense failed: {result['error']}")
    elif 'success' in result:
        sense_id = result.get('sense', {}).get('id')
        print(f"\n✓ wbladdsense succeeded")
        print(f"  Sense ID: {sense_id}")
        print(f"  Success: {result.get('success')}")

    print()

except Exception as e:
    print(f"✗ Exception: {e}\n")

# Wait and verify
time.sleep(1)
try:
    r = session.get(API_URL, params={
        'action': 'query',
        'titles': f'Lexeme:{test_lexeme_id}',
        'prop': 'revisions',
        'rvprop': 'content',
        'format': 'json'
    })
    pages = r.json()['query']['pages']
    if pages and list(pages.values())[0].get('revisions'):
        content = pages[list(pages.keys())[0]]['revisions'][0]['*']
        lexeme = json.loads(content)
        senses = lexeme.get('senses', [])
        if senses:
            print(f"✓ Sense persisted! Current senses: {len(senses)}")
            print(f"  Sense content: {json.dumps(senses[0], indent=2)}\n")
        else:
            print(f"✗ Sense NOT persisted. Lexeme has {len(senses)} senses.\n")
except Exception as e:
    print(f"  (could not verify: {e})\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: Try wbladdform endpoint
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print(f"TEST 3: Add Form via wbladdform to {test_lexeme_id}")
print("=" * 80)

try:
    print("Payload:")
    print(f"  action: wbladdform")
    print(f"  lexemeId: {test_lexeme_id}")
    print(f"  representation: {{\"mis\":\"debugtest-form\"}}")

    r = session.post(API_URL, data={
        'action': 'wbladdform',
        'lexemeId': test_lexeme_id,
        'representation': json.dumps({'mis': 'debugtest-form'}),
        'features': json.dumps([]),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    print(f"\nResponse:")
    print(json.dumps(result, indent=2))

    if 'error' in result:
        print(f"\n✗ wbladdform failed: {result['error']}")
    elif 'success' in result:
        form_id = result.get('form', {}).get('id')
        print(f"\n✓ wbladdform succeeded")
        print(f"  Form ID: {form_id}")
        print(f"  Success: {result.get('success')}")

    print()

except Exception as e:
    print(f"✗ Exception: {e}\n")

# Wait and verify
time.sleep(1)
try:
    r = session.get(API_URL, params={
        'action': 'query',
        'titles': f'Lexeme:{test_lexeme_id}',
        'prop': 'revisions',
        'rvprop': 'content',
        'format': 'json'
    })
    pages = r.json()['query']['pages']
    if pages and list(pages.values())[0].get('revisions'):
        content = pages[list(pages.keys())[0]]['revisions'][0]['*']
        lexeme = json.loads(content)
        forms = lexeme.get('forms', [])
        if forms:
            print(f"✓ Form persisted! Current forms: {len(forms)}")
            print(f"  Form content: {json.dumps(forms[0], indent=2)}\n")
        else:
            print(f"✗ Form NOT persisted. Lexeme has {len(forms)} forms.\n")
except Exception as e:
    print(f"  (could not verify: {e})\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: Try wbeditentity with sense modification
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print(f"TEST 4: Modify {test_lexeme_id} senses via wbeditentity JSON")
print("=" * 80)

try:
    print("Payload:")
    print(f"  action: wbeditentity")
    print(f"  id: {test_lexeme_id}")
    print(f"  data: {{\"senses\":[{{\"glosses\":{{\"en\":{{\"language\":\"en\",\"value\":\"modified test\"}}}}}}]")

    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': test_lexeme_id,
        'data': json.dumps({
            'senses': [
                {
                    'glosses': {
                        'en': {
                            'language': 'en',
                            'value': 'modified test meaning'
                        }
                    },
                    'claims': []
                }
            ]
        }),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    print(f"\nResponse:")
    print(json.dumps(result, indent=2))

    if 'error' in result:
        print(f"\n✗ wbeditentity failed: {result['error']}")
    elif 'success' in result:
        print(f"\n✓ wbeditentity succeeded")
        if 'nochange' in result.get('entity', {}):
            print(f"  WARNING: 'nochange' indicator present - may not have persisted")

    print()

except Exception as e:
    print(f"✗ Exception: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)

print(f"""
Test Lexeme: {test_lexeme_id}

Methods tested:
1. wbladdsense endpoint - for dedicated sense creation
2. wbladdform endpoint - for dedicated form creation
3. wbeditentity endpoint - for JSON-based modifications

Check the output above for:
- Whether each method returns "success"
- Whether the returned IDs are valid
- Whether the data persists after fetch (delayed verify)

DIAGNOSTIC INTERPRETATION:
==========================

IF ALL FAIL with error:
  → Lexeme extension not enabled or broken
  → Contact Miraheze support

IF wbladdsense/wbladdform work but don't persist:
  → API accepts them but database write fails
  → Issue is in wb_sense / wb_form tables
  → Likely: Missing database schema or incomplete initialization

IF wbeditentity fails but modification of L61 works:
  → Can only modify existing senses, can't create new ones
  → Use the L61-template approach from working script

IF everything works perfectly:
  → There's something specific about L1-L60 data that's incompatible
  → Need to inspect L1-L60 structure vs L61-L62 structure
""")
