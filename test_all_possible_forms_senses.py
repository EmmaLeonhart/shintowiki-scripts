#!/usr/bin/env python3
"""
test_all_possible_forms_senses.py
==================================
Attempt EVERY SINGLE DOCUMENTED WAY to add forms and senses to Wikibase Lexemes.
Try multiple versions of Wikibase API, old formats, new formats, alternate methods.
Focus on finding ANY method that works.
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

try:
    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
    login_token = r.json()['query']['tokens']['logintoken']

    r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
    if r.json().get('login', {}).get('result') != 'Success':
        print("✗ Login failed")
        sys.exit(1)

    r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
    csrf_token = r.json()['query']['tokens']['csrftoken']
except Exception as e:
    print(f"✗ Auth failed: {e}")
    sys.exit(1)

print("✓ Authenticated\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST ALL METHODS FOR ADDING SENSES
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("COMPREHENSIVE SENSE ADDITION TESTS")
print("=" * 80)
print()

test_lex = 'L75'  # Use one of our test lexemes
sense_methods = []

# METHOD FAMILIES FOR SENSES

# 1. WBEDITENTITY with senses in various formats
print("FAMILY 1: wbeditentity with different sense structures")
print("-" * 80)

sense_structure_tests = [
    {
        'name': '1.1: Senses with standard glosses dict',
        'data': {'senses': {'L75-S1': {'glosses': {'en': {'language': 'en', 'value': 'test'}}}}}
    },
    {
        'name': '1.2: Senses with string glosses',
        'data': {'senses': {'L75-S2': {'glosses': {'en': 'test'}}}}
    },
    {
        'name': '1.3: Senses without language code',
        'data': {'senses': {'L75-S3': {'glosses': {'test gloss'}}}}
    },
    {
        'name': '1.4: Senses as array instead of dict',
        'data': {'senses': [{'glosses': {'en': 'test'}}]}
    },
    {
        'name': '1.5: Senses with ID auto-generation (no ID specified)',
        'data': {'senses': [{'glosses': {'en': 'auto-sense'}}]}
    },
    {
        'name': '1.6: Senses with multilingual glosses',
        'data': {'senses': {'L75-S6': {'glosses': {'en': 'english', 'ja': 'japanese'}}}}
    },
    {
        'name': '1.7: Senses with example',
        'data': {'senses': {'L75-S7': {'glosses': {'en': 'test'}, 'examples': [{'language': 'en', 'value': 'example text'}]}}}
    },
    {
        'name': '1.8: Senses with claims',
        'data': {'senses': {'L75-S8': {'glosses': {'en': 'test'}, 'claims': {'P1': [{'mainsnak': {'snaktype': 'value', 'property': 'P1', 'datavalue': {'value': {'entity-type': 'item', 'numeric-id': 10}, 'type': 'wikibase-entityid'}}, 'type': 'statement', 'rank': 'normal'}]}}}}
    },
]

for i, test in enumerate(sense_structure_tests):
    print(f"\n{test['name']}")
    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': test_lex,
            'data': json.dumps(test['data']),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'entity' in result and result['entity'].get('senses'):
            print(f"  ✓ SUCCESS - senses in response")
            sense_methods.append((test['name'], 'SUCCESS'))
        elif 'error' in result:
            print(f"  ✗ Error: {result['error'].get('code')}")
            sense_methods.append((test['name'], 'ERROR'))
        else:
            print(f"  ✗ No senses in response")
            sense_methods.append((test['name'], 'NO_SENSES'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:50]}")
        sense_methods.append((test['name'], 'EXCEPTION'))
    time.sleep(0.2)

# 2. DEDICATED LEXEME API ENDPOINTS
print("\n\nFAMILY 2: Dedicated Lexeme API endpoints (wbladdsense, wbladdform)")
print("-" * 80)

dedicated_endpoints = [
    {
        'name': '2.1: wbladdsense basic',
        'action': 'wbladdsense',
        'params': {
            'lexemeid': test_lex,
            'data': json.dumps({'glosses': {'en': {'language': 'en', 'value': 'test'}}}),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': '2.2: wbladdsense with examples',
        'action': 'wbladdsense',
        'params': {
            'lexemeid': test_lex,
            'data': json.dumps({'glosses': {'en': 'test'}, 'examples': [{'language': 'en', 'value': 'example'}]}),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': '2.3: wbladdform basic',
        'action': 'wbladdform',
        'params': {
            'lexemeid': test_lex,
            'data': json.dumps({'representations': {'en': {'language': 'en', 'value': 'form1'}}}),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': '2.4: wbladdform with grammatical features',
        'action': 'wbladdform',
        'params': {
            'lexemeid': test_lex,
            'data': json.dumps({'representations': {'en': 'form2'}, 'grammaticalFeatures': ['Q1']}),
            'token': csrf_token,
            'format': 'json'
        }
    },
]

for i, test in enumerate(dedicated_endpoints):
    print(f"\n{test['name']}")
    try:
        r = session.post(API_URL, data=test['params'])
        result = r.json()

        if 'entity' in result or 'sense' in result or 'form' in result:
            print(f"  ✓ SUCCESS - entity/sense/form in response")
            sense_methods.append((test['name'], 'SUCCESS'))
        elif 'error' in result:
            print(f"  ✗ Error: {result['error'].get('code')}")
            sense_methods.append((test['name'], 'ERROR'))
        else:
            print(f"  ✗ No response entity")
            print(f"    Keys: {list(result.keys())[:3]}")
            sense_methods.append((test['name'], 'NO_ENTITY'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:50]}")
        sense_methods.append((test['name'], 'EXCEPTION'))
    time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════════════════
# TEST ALL METHODS FOR ADDING FORMS
# ═══════════════════════════════════════════════════════════════════════════

print("\n\nFAMILY 3: wbeditentity with different form structures")
print("-" * 80)

form_structure_tests = [
    {
        'name': '3.1: Forms with standard representations dict',
        'data': {'forms': {'L75-F1': {'representations': {'en': {'language': 'en', 'value': 'form1'}}}}}
    },
    {
        'name': '3.2: Forms with string representations',
        'data': {'forms': {'L75-F2': {'representations': {'en': 'form2'}}}}
    },
    {
        'name': '3.3: Forms as array',
        'data': {'forms': [{'representations': {'en': 'form3'}}]}
    },
    {
        'name': '3.4: Forms with grammatical features',
        'data': {'forms': {'L75-F4': {'representations': {'en': 'form4'}, 'grammaticalFeatures': ['Q1']}}}
    },
    {
        'name': '3.5: Forms with multiple representations',
        'data': {'forms': {'L75-F5': {'representations': {'en': 'form5', 'ja': 'form5ja'}}}}
    },
    {
        'name': '3.6: Forms with claims',
        'data': {'forms': {'L75-F6': {'representations': {'en': 'form6'}, 'claims': {'P1': [{'mainsnak': {'snaktype': 'value', 'property': 'P1', 'datavalue': {'value': {'entity-type': 'item', 'numeric-id': 10}, 'type': 'wikibase-entityid'}}, 'type': 'statement', 'rank': 'normal'}]}}}}
    },
]

form_methods = []
for i, test in enumerate(form_structure_tests):
    print(f"\n{test['name']}")
    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': test_lex,
            'data': json.dumps(test['data']),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'entity' in result and result['entity'].get('forms'):
            print(f"  ✓ SUCCESS - forms in response")
            form_methods.append((test['name'], 'SUCCESS'))
        elif 'error' in result:
            print(f"  ✗ Error: {result['error'].get('code')}")
            form_methods.append((test['name'], 'ERROR'))
        else:
            print(f"  ✗ No forms in response")
            form_methods.append((test['name'], 'NO_FORMS'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:50]}")
        form_methods.append((test['name'], 'EXCEPTION'))
    time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("\n\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print()

print("SENSES (Family 1 + 2):")
successful_sense_methods = [(name, result) for name, result in sense_methods if 'SUCCESS' in result]
if successful_sense_methods:
    print(f"✓ FOUND {len(successful_sense_methods)} WORKING METHOD(S) FOR SENSES:")
    for name, result in successful_sense_methods:
        print(f"  • {name}")
else:
    print("✗ No working methods found for senses")
    print("  Top errors:")
    for name, result in sense_methods[:5]:
        print(f"    • {name}: {result}")

print()
print("FORMS (Family 3):")
successful_form_methods = [(name, result) for name, result in form_methods if 'SUCCESS' in result]
if successful_form_methods:
    print(f"✓ FOUND {len(successful_form_methods)} WORKING METHOD(S) FOR FORMS:")
    for name, result in successful_form_methods:
        print(f"  • {name}")
else:
    print("✗ No working methods found for forms")
    print("  Top errors:")
    for name, result in form_methods[:5]:
        print(f"    • {name}: {result}")

print()
if successful_sense_methods or successful_form_methods:
    print(f"✓ TOTAL WORKING METHODS: {len(successful_sense_methods + successful_form_methods)}")
else:
    print("✗ NO WORKING METHODS FOUND")
