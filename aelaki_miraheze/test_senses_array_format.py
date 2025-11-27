#!/usr/bin/env python3
"""
test_senses_array_format.py
===========================
Test adding senses using ARRAY format (like L61/L62 return them).
L61 and L62 return senses as an array, not a dict - this might be the key!
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

# Login
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']
r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

print("=" * 80)
print("TESTING SENSES WITH ARRAY FORMAT")
print("=" * 80)
print()

test_lex = 'L75'

# Test 1: Array format with full structure (like L61-S1)
print("Test 1: Add sense as ARRAY with full structure (matching L61/L62 format)")
print("-" * 80)

edit_data = {
    'senses': [
        {
            'id': f'{test_lex}-S1',
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'Test sense from array'
                }
            }
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': test_lex,
        'data': json.dumps(edit_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'entity' in result:
        senses = result['entity'].get('senses', {})
        if senses:
            print(f"✓ SUCCESS - senses in response!")
            print(f"  Type: {type(senses)}")
            print(f"  Count: {len(senses)}")
            print(f"  Data: {json.dumps(senses, indent=2)[:200]}")
        else:
            print(f"✗ No senses in response")
    elif 'error' in result:
        print(f"✗ Error: {result['error'].get('code')}")
        print(f"  Info: {result['error'].get('info')}")
    else:
        print(f"✗ Unexpected: {list(result.keys())}")
except Exception as e:
    print(f"✗ Exception: {e}")

print()
time.sleep(0.5)

# Test 2: Array format without explicit ID
print("Test 2: Array format without ID (auto-gen)")
print("-" * 80)

edit_data = {
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'Auto ID sense'
                }
            }
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': test_lex,
        'data': json.dumps(edit_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'entity' in result:
        senses = result['entity'].get('senses', {})
        if senses:
            print(f"✓ SUCCESS")
        else:
            print(f"✗ No senses in response")
    elif 'error' in result:
        print(f"✗ Error: {result['error'].get('code')}")
    else:
        print(f"✗ Unexpected")
except Exception as e:
    print(f"✗ Exception: {str(e)[:50]}")

print()
time.sleep(0.5)

# Test 3: Mixed - array with string gloss
print("Test 3: Array with string gloss (no language wrapper)")
print("-" * 80)

edit_data = {
    'senses': [
        {
            'id': f'{test_lex}-S3',
            'glosses': {
                'en': 'Simple string gloss'
            }
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': test_lex,
        'data': json.dumps(edit_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'entity' in result:
        senses = result['entity'].get('senses', {})
        if senses:
            print(f"✓ SUCCESS")
        else:
            print(f"✗ No senses in response")
    elif 'error' in result:
        print(f"✗ Error: {result['error'].get('code')}")
    else:
        print(f"✗ Unexpected")
except Exception as e:
    print(f"✗ Exception: {str(e)[:50]}")

print()
time.sleep(0.5)

# Test 4: Multiple senses in array
print("Test 4: Multiple senses in array")
print("-" * 80)

edit_data = {
    'senses': [
        {
            'id': f'{test_lex}-S4a',
            'glosses': {'en': 'First sense'}
        },
        {
            'id': f'{test_lex}-S4b',
            'glosses': {'en': 'Second sense'}
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'id': test_lex,
        'data': json.dumps(edit_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()

    if 'entity' in result:
        senses = result['entity'].get('senses', {})
        if senses:
            print(f"✓ SUCCESS - {len(senses)} senses")
        else:
            print(f"✗ No senses")
    elif 'error' in result:
        print(f"✗ Error: {result['error'].get('code')}")
    else:
        print(f"✗ Unexpected")
except Exception as e:
    print(f"✗ Exception: {str(e)[:50]}")

print()
print("=" * 80)
print("VERIFICATION: Check L75 current state")
print("=" * 80)
print()

try:
    r = session.get(API_URL, params={
        'action': 'wbgetentities',
        'ids': test_lex,
        'format': 'json'
    })
    result = r.json()

    if 'entities' in result and test_lex in result['entities']:
        entity = result['entities'][test_lex]
        senses = entity.get('senses', [])
        print(f"L75 senses count: {len(senses)}")
        print(f"Type: {type(senses)}")
        if senses:
            print("\nSense details:")
            for i, sense in enumerate(list(senses)[:3]):
                print(f"  {i+1}. ID: {sense.get('id')}, Glosses: {sense.get('glosses', {})}")
except Exception as e:
    print(f"✗ Verification failed: {e}")
