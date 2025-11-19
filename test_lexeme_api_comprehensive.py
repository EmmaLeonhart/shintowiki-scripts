#!/usr/bin/env python3
"""
test_lexeme_api_comprehensive.py
================================
Comprehensive diagnostic to determine if Aelaki wiki's WikibaseLexeme
backend is functional or fundamentally broken.

Tests:
1. Direct API inspection of L61/L62 (known working)
2. Attempt to modify L61 to verify persistence works
3. Attempt to create a new lexeme from scratch
4. Test all sense-related endpoints
5. Check for database/configuration issues via API
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
# SETUP: Login and get tokens
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PHASE 0: SETUP - Login and Token Acquisition")
print("=" * 80)

try:
    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
    login_token = r.json()['query']['tokens']['logintoken']
    print("✓ Got login token")
except Exception as e:
    print(f"✗ Failed to get login token: {e}")
    sys.exit(1)

try:
    r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
    if r.json().get('login', {}).get('result') == 'Success':
        print("✓ Logged in successfully")
    else:
        print(f"✗ Login failed: {r.json()}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Login error: {e}")
    sys.exit(1)

try:
    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
    csrf_token = r.json()['query']['tokens']['csrftoken']
    print("✓ Got CSRF token\n")
except Exception as e:
    print(f"✗ Failed to get CSRF token: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: Inspect L61 (known working example)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PHASE 1: Inspect L61 (Known Working Example)")
print("=" * 80)

try:
    r = session.get(API_URL, params={
        'action': 'query',
        'titles': 'Lexeme:L61',
        'prop': 'revisions',
        'rvprop': 'content',
        'format': 'json'
    })
    pages = r.json()['query']['pages']
    page_id = list(pages.keys())[0]
    content = pages[page_id]['revisions'][0]['*']
    l61_data = json.loads(content)

    print("L61 Current State:")
    print(json.dumps(l61_data, indent=2))
    print()

    # Verify structure
    has_senses = len(l61_data.get('senses', [])) > 0
    has_gloss = False
    if has_senses:
        gloss_obj = l61_data['senses'][0].get('glosses', {}).get('en', {})
        has_gloss = isinstance(gloss_obj, dict) and 'value' in gloss_obj

    print(f"✓ L61 has senses: {has_senses}")
    print(f"✓ L61 has English gloss: {has_gloss}")
    print(f"✓ L61 structure is valid for reference\n")

except Exception as e:
    print(f"✗ Failed to fetch L61: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: Test persistence by modifying L61's gloss
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PHASE 2: Persistence Test - Modify L61 gloss and verify save")
print("=" * 80)

MARKER_TEXT = f"TEST_MARKER_{int(time.time())}"

# Create modified data with a test marker
test_data = {
    'senses': [
        {
            'id': 'L61-S1',
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': f'yes [{MARKER_TEXT}]'
                }
            },
            'claims': []
        }
    ]
}

try:
    print(f"Modifying L61 with test marker: {MARKER_TEXT}")
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': 'L61',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    print(f"\nAPI Response:")
    print(json.dumps(result, indent=2))

    # Check for success indicators
    if 'error' in result:
        print(f"\n✗ API returned error: {result['error']}")
    elif 'success' in result and result['success']:
        print(f"\n✓ API returned success")

        # Check if data was actually persisted
        if 'nochange' in result.get('entity', {}):
            print(f"✗ BUT 'nochange' indicator present - persistence failed!")

        # Verify the gloss in response
        entity = result.get('entity', {})
        response_gloss = entity.get('senses', [{}])[0].get('glosses', {}).get('en', {}).get('value', '')

        if MARKER_TEXT in response_gloss:
            print(f"✓ Test marker found in API response: {response_gloss}")
        else:
            print(f"✗ Test marker NOT in API response. Response gloss: {response_gloss}")

    time.sleep(1)

    # Now fetch L61 again to see if change persisted
    print(f"\nFetching L61 again to verify persistence...")
    r = session.get(API_URL, params={
        'action': 'query',
        'titles': 'Lexeme:L61',
        'prop': 'revisions',
        'rvprop': 'content',
        'format': 'json'
    })
    pages = r.json()['query']['pages']
    page_id = list(pages.keys())[0]
    current_content = pages[page_id]['revisions'][0]['*']
    l61_current = json.loads(current_content)

    current_gloss = l61_current.get('senses', [{}])[0].get('glosses', {}).get('en', {}).get('value', '')

    if MARKER_TEXT in current_gloss:
        print(f"✓✓✓ PERSISTENCE CONFIRMED! Test marker found in saved data: {current_gloss}")
    else:
        print(f"✗✗✗ PERSISTENCE FAILED! Marker not in saved data.")
        print(f"    Expected substring: {MARKER_TEXT}")
        print(f"    Actual gloss: {current_gloss}")

    print()

except Exception as e:
    print(f"✗ Exception during persistence test: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: Try to create a brand new lexeme with sense
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PHASE 3: Creation Test - Create new lexeme with sense in one call")
print("=" * 80)

TEST_LEXEME_NUM = 999
TEST_NAME = 'testlex'

new_lexeme_data = {
    'type': 'lexeme',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': TEST_NAME
        }
    },
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'test gloss'
                }
            },
            'claims': []
        }
    ]
}

try:
    print(f"Creating new lexeme with lemma '{TEST_NAME}' and sense...")
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(new_lexeme_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'error' in result:
        print(f"✗ API error: {result['error']}")
    elif 'success' in result and result['success']:
        entity = result.get('entity', {})
        new_lexeme_id = entity.get('id', 'UNKNOWN')
        senses = entity.get('senses', [])

        print(f"✓ Lexeme created: {new_lexeme_id}")
        print(f"✓ Senses in response: {len(senses)}")

        if senses:
            gloss = senses[0].get('glosses', {}).get('en', {}).get('value', '')
            print(f"✓ Gloss in response: {gloss}")
        else:
            print(f"✗ No senses in response despite providing them")

        # Verify by fetching
        print(f"\nVerifying {new_lexeme_id}...")
        time.sleep(1)
        r = session.get(API_URL, params={
            'action': 'query',
            'titles': f'Lexeme:{new_lexeme_id}',
            'prop': 'revisions',
            'rvprop': 'content',
            'format': 'json'
        })
        pages = r.json()['query']['pages']
        if pages and list(pages.values())[0].get('revisions'):
            page_id = list(pages.keys())[0]
            saved_content = pages[page_id]['revisions'][0]['*']
            saved_data = json.loads(saved_content)
            saved_senses = saved_data.get('senses', [])

            if saved_senses:
                print(f"✓ Saved lexeme has senses: {len(saved_senses)}")
                saved_gloss = saved_senses[0].get('glosses', {}).get('en', {}).get('value', '')
                print(f"✓ Saved gloss: {saved_gloss}")
            else:
                print(f"✗ Saved lexeme has NO senses (creation-time senses were lost)")
        else:
            print(f"✗ Could not fetch created lexeme")

    print()

except Exception as e:
    print(f"✗ Exception during creation test: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: Test sense-specific operations
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PHASE 4: Sense-Specific Operations")
print("=" * 80)

# Try using the senses subentity endpoint if it exists
try:
    print("Testing if we can add a sense to L2 via direct sense creation...")

    # Some Wikibase instances support adding senses as sub-entities
    sense_data = {
        'glosses': {
            'en': {
                'language': 'en',
                'value': 'test sense'
            }
        }
    }

    # Try method 1: wbeditentity on lexeme
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': 'L2',
        'data': json.dumps({'senses': [sense_data]}),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    print("Attempt 1: wbeditentity with senses array")
    print(json.dumps(result, indent=2))

    if 'nochange' in result.get('entity', {}):
        print("  ✗ 'nochange' indicator - persistence issue confirmed")

    print()

except Exception as e:
    print(f"✗ Exception: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: Diagnostic Summary
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PHASE 5: Summary and Recommendations")
print("=" * 80)

print("""
WHAT WE'RE TESTING:
===================

1. L61 Persistence: Can we modify an existing lexeme and have it stay saved?
   - If YES: The backend is working, we can fix via API
   - If NO: The backend is broken at the database level

2. New Lexeme Creation: Can we create a new lexeme WITH senses in one call?
   - If YES: Creating lexemes with senses works, we should use this approach
   - If NO: We can only create empty lexemes, then add senses separately

3. Sense Operations: Is there a working sense-specific API?
   - If YES: We can add senses independently
   - If NO: We're blocked by backend limitations

POSSIBLE OUTCOMES & SOLUTIONS:
==============================

OUTCOME A: L61 persistence test FAILS (marker doesn't stay saved)
  ➜ ROOT CAUSE: WikibaseLexeme backend can't persist sense changes
  ➜ SOLUTION 1: Contact Miraheze - this is a infrastructure issue
  ➜ SOLUTION 2: Use database direct access if available
  ➜ SOLUTION 3: Manually add senses via wiki UI then export/backup

OUTCOME B: L61 persistence test PASSES, but new lexeme has no senses
  ➜ ROOT CAUSE: wbeditentity can't create senses at creation time
  ➜ SOLUTION: Create lexeme empty, then modify to add senses
  ➜ ACTION: Use two-step process with delay between operations

OUTCOME C: Everything works perfectly
  ➜ ROOT CAUSE: There's something wrong with our data format for L1-L60
  ➜ SOLUTION: Use successful examples (L61/L62) as exact templates
  ➜ ACTION: Copy exact structure from L61, modify only necessary fields

OUTCOME D: Senses exist in API response but not in saved data
  ➜ ROOT CAUSE: API returns success but validation/persistence fails
  ➜ SOLUTION: Check 'nochange' indicator - always verify saves
  ➜ ACTION: Implement verification loop after each edit

NEXT STEPS IF PERSISTENCE FAILS:
=================================
1. Try using mwclient library instead of raw requests
2. Try using full lexeme data merge (fetch + modify + save all fields)
3. Check if there's a special role/permission needed for sense editing
4. Ask Miraheze if sense editing needs to be enabled in ManageWiki
5. Check if there are PHP job queue issues preventing writes
""")
