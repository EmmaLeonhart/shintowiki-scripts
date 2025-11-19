#!/usr/bin/env python3
"""
test_wikibase_items.py
======================
Test creating and editing regular Wikibase ITEMS (not lexemes) on Aelaki.
Create items, add properties, see what actually works on this installation.
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
# TEST 1: Create a simple item (Q)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 1: Create a simple Wikibase ITEM (Q item)")
print("=" * 80)

item_data = {
    'type': 'item',
    'labels': {
        'en': {
            'language': 'en',
            'value': 'Test Item 1'
        }
    },
    'descriptions': {
        'en': {
            'language': 'en',
            'value': 'A test item to verify Wikibase functionality'
        }
    }
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'item',
        'data': json.dumps(item_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'error' in result:
        print(f"✗ Error: {result['error']}")
        test1_qid = None
    elif 'entity' in result:
        test1_qid = result['entity'].get('id')
        print(f"✓ Created: {test1_qid}")
        print(f"  Labels: {result['entity'].get('labels', {})}")
        print(f"  Descriptions: {result['entity'].get('descriptions', {})}\n")
    else:
        print(f"✗ Unexpected response: {json.dumps(result, indent=2)}\n")
        test1_qid = None
except Exception as e:
    print(f"✗ Exception: {e}\n")
    test1_qid = None

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Create an item with a property/claim
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 2: Create item WITH a property/claim")
print("=" * 80)

item_with_claim = {
    'type': 'item',
    'labels': {
        'en': {
            'language': 'en',
            'value': 'Test Item 2 (with claim)'
        }
    },
    'claims': [
        {
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
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'item',
        'data': json.dumps(item_with_claim),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'error' in result:
        print(f"✗ Error: {result['error']}")
        test2_qid = None
    elif 'entity' in result:
        test2_qid = result['entity'].get('id')
        claims = result['entity'].get('claims', [])
        print(f"✓ Created: {test2_qid}")
        print(f"  Claims in response: {len(claims) if isinstance(claims, (list, dict)) else 0}")
        print(f"  Full entity: {json.dumps(result['entity'], indent=2)}\n")
    else:
        print(f"✗ Unexpected response\n")
        test2_qid = None
except Exception as e:
    print(f"✗ Exception: {e}\n")
    test2_qid = None

# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: Modify an existing item (add a claim)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 3: Modify existing item (add a claim)")
print("=" * 80)

if test1_qid:
    # Add a claim to test1_qid
    claim_data = {
        'claims': [
            {
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
        ]
    }

    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': test1_qid,
            'data': json.dumps(claim_data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            print(f"✗ Error: {result['error']}")
        elif 'entity' in result:
            claims = result['entity'].get('claims', [])
            print(f"✓ Modified: {test1_qid}")
            print(f"  Claims in response: {len(claims) if isinstance(claims, (list, dict)) else 0}")
            print(f"  Full entity: {json.dumps(result['entity'], indent=2)}\n")
        else:
            print(f"✗ Unexpected response\n")
    except Exception as e:
        print(f"✗ Exception: {e}\n")
else:
    print("⊘ Skipped (couldn't create test1_qid)\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: Create a property (P item)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 4: Create a PROPERTY (P item)")
print("=" * 80)

property_data = {
    'type': 'property',
    'datatype': 'wikibase-item',
    'labels': {
        'en': {
            'language': 'en',
            'value': 'test property'
        }
    },
    'descriptions': {
        'en': {
            'language': 'en',
            'value': 'A test property'
        }
    }
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'property',
        'data': json.dumps(property_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'error' in result:
        print(f"✗ Error: {result['error']}")
    elif 'entity' in result:
        prop_id = result['entity'].get('id')
        print(f"✓ Created property: {prop_id}")
        print(f"  Type: {result['entity'].get('type')}")
        print(f"  Datatype: {result['entity'].get('datatype')}\n")
    else:
        print(f"✗ Unexpected response\n")
except Exception as e:
    print(f"✗ Exception: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("SUMMARY")
print("=" * 80)

print("""
This test checks basic Wikibase functionality on Aelaki:

1. Create simple item (label + description only)
   - This is the most basic operation

2. Create item with claims during creation
   - Tests if properties persist during creation

3. Add claims to existing item
   - Tests if we can modify items to add properties

4. Create a new property (P item)
   - Tests if we can create custom properties

Results show which operations work on this installation.
Regular items (Q) and properties (P) behave differently than lexemes.
""")
