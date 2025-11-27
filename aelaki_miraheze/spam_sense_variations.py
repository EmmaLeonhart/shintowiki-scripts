#!/usr/bin/env python3
"""
spam_sense_variations.py
========================
SPAM different sense variations on L75 to find what actually works.
No caution - just try everything and see what sticks.
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

# Login
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']
r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

print("=" * 80)
print("SPAMMING SENSE VARIATIONS ON L75")
print("=" * 80)
print()

test_lex = 'L75'
working_methods = []

# VARIATION 1: Dict format with different sense ID formats
variations = [
    # Standard formats
    ("Dict: L75-S1", {'senses': {'L75-S1': {'glosses': {'en': 'test'}}}}),
    ("Dict: L75-Q13", {'senses': {'L75-Q13': {'glosses': {'en': 'test'}}}}),
    ("Dict: S1", {'senses': {'S1': {'glosses': {'en': 'test'}}}}),
    ("Dict: Q13", {'senses': {'Q13': {'glosses': {'en': 'test'}}}}),
    ("Dict: 1", {'senses': {'1': {'glosses': {'en': 'test'}}}}),

    # With language wrapper
    ("Dict: L75-S1 (full lang)", {'senses': {'L75-S1': {'glosses': {'en': {'language': 'en', 'value': 'test'}}}}}),
    ("Dict: L75-Q13 (full lang)", {'senses': {'L75-Q13': {'glosses': {'en': {'language': 'en', 'value': 'test'}}}}}),

    # Multiple senses
    ("Dict: L75-S1 + L75-S2", {'senses': {'L75-S1': {'glosses': {'en': 'test1'}}, 'L75-S2': {'glosses': {'en': 'test2'}}}}),

    # List formats
    ("List: Basic", {'senses': [{'glosses': {'en': 'test'}}]}),
    ("List: With ID L75-S1", {'senses': [{'id': 'L75-S1', 'glosses': {'en': 'test'}}]}),
    ("List: With ID L75-Q13", {'senses': [{'id': 'L75-Q13', 'glosses': {'en': 'test'}}]}),
    ("List: With ID S1", {'senses': [{'id': 'S1', 'glosses': {'en': 'test'}}]}),
    ("List: With ID Q13", {'senses': [{'id': 'Q13', 'glosses': {'en': 'test'}}]}),

    # Multiple in list
    ("List: 2 senses", {'senses': [{'id': 'L75-S1', 'glosses': {'en': 'test1'}}, {'id': 'L75-S2', 'glosses': {'en': 'test2'}}]}),

    # Empty glosses
    ("Dict: Empty glosses dict", {'senses': {'L75-S1': {'glosses': {}}}}),

    # With claims
    ("Dict: With claims", {'senses': {'L75-S1': {'glosses': {'en': 'test'}, 'claims': []}}}),

    # With examples
    ("Dict: With examples", {'senses': {'L75-S1': {'glosses': {'en': 'test'}, 'examples': [{'language': 'en', 'value': 'example'}]}}}),

    # Nested structures
    ("Dict: Nested glosses list", {'senses': {'L75-S1': {'glosses': [{'language': 'en', 'value': 'test'}]}}}),

    # Without language key
    ("Dict: No language wrapper", {'senses': {'L75-S1': {'glosses': {'en': 'test'}}}}),

    # Minimal
    ("Dict: Minimal", {'senses': {'L75-S1': {}}}),

    # Unicode/special chars
    ("Dict: Unicode sense ID", {'senses': {'L75-Ｓ1': {'glosses': {'en': 'test'}}}}),
]

for name, data in variations:
    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': test_lex,
            'data': json.dumps(data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'entity' in result:
            senses = result['entity'].get('senses', {})
            if senses:
                status = "✓ WORKS"
                working_methods.append(name)
            else:
                status = "✗ No senses in response"
        elif 'error' in result:
            error_code = result['error'].get('code', '?')
            error_info = result['error'].get('info', '')[:30]
            status = f"✗ Error: {error_code}"
        else:
            status = "✗ Unexpected response"

        print(f"{name:45} -> {status}")

    except Exception as e:
        print(f"{name:45} -> ✗ Exception: {str(e)[:30]}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
if working_methods:
    print(f"✓ FOUND {len(working_methods)} WORKING METHOD(S):")
    for method in working_methods:
        print(f"  • {method}")
else:
    print("✗ No working methods found on fresh lexeme (L75)")
    print("  But L61/L62 worked with Q13 format, so sense IDs must pre-exist")

print()
print("=" * 80)
print("VERIFY L75 CURRENT STATE")
print("=" * 80)

r = session.get(API_URL, params={
    'action': 'wbgetentities',
    'ids': test_lex,
    'format': 'json'
})
result = r.json()

if test_lex in result.get('entities', {}):
    entity = result['entities'][test_lex]
    senses = entity.get('senses', [])
    print(f"L75 now has {len(senses)} senses")
    if senses:
        for i, sense in enumerate(list(senses)[:5]):
            print(f"  {i+1}. {sense.get('id', '?')}: {sense.get('glosses', {})}")
