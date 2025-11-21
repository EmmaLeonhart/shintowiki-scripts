#!/usr/bin/env python3
"""
test_all_lexeme_api_methods.py
==============================
Comprehensive test of ALL possible Lexeme API endpoints and methods on Aelaki.
Test every documented Lexeme API command to see which ones actually work.
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
# TEST SUITE 1: wbeditentity - Different Data Formats
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 1: wbeditentity with various claim formats")
print("=" * 80)
print()

test_cases = [
    {
        'name': 'Format A: claims as dict with property keys (standard Wikibase)',
        'data': {
            'claims': {
                'P1': [
                    {
                        'mainsnak': {
                            'snaktype': 'value',
                            'property': 'P1',
                            'datavalue': {
                                'value': {'entity-type': 'item', 'numeric-id': 10},
                                'type': 'wikibase-entityid'
                            }
                        },
                        'type': 'statement',
                        'rank': 'normal'
                    }
                ]
            }
        }
    },
    {
        'name': 'Format B: claims as list (Aelaki variant)',
        'data': {
            'claims': [
                {
                    'mainsnak': {
                        'snaktype': 'value',
                        'property': 'P1',
                        'datavalue': {
                            'value': {'entity-type': 'item', 'numeric-id': 10},
                            'type': 'wikibase-entityid'
                        }
                    },
                    'type': 'statement',
                    'rank': 'normal'
                }
            ]
        }
    },
    {
        'name': 'Format C: claims with just mainsnak',
        'data': {
            'claims': [
                {
                    'mainsnak': {
                        'snaktype': 'value',
                        'property': 'P1',
                        'datavalue': {
                            'value': {'entity-type': 'item', 'numeric-id': 10},
                            'type': 'wikibase-entityid'
                        }
                    }
                }
            ]
        }
    },
    {
        'name': 'Format D: claims with qualified snak',
        'data': {
            'claims': [
                {
                    'mainsnak': {
                        'snaktype': 'value',
                        'property': 'P1',
                        'datavalue': {
                            'value': {'entity-type': 'item', 'numeric-id': 10},
                            'type': 'wikibase-entityid'
                        }
                    },
                    'type': 'statement',
                    'rank': 'normal',
                    'qualifiers': {
                        'P3': [
                            {
                                'snaktype': 'value',
                                'property': 'P3',
                                'datavalue': {
                                    'value': 'test',
                                    'type': 'string'
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
]

results_suite1 = []
for i, test_case in enumerate(test_cases):
    print(f"Test 1.{i+1}: {test_case['name']}")
    print(f"  Trying with L75...")

    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': 'L75',
            'data': json.dumps(test_case['data']),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            status = f"✗ Error: {result['error'].get('info', result['error'].get('code'))}"
            print(f"  {status}")
            results_suite1.append((test_case['name'], 'ERROR'))
        elif 'success' in result and result['success']:
            entity = result.get('entity', {})
            claims = entity.get('claims', [])
            if isinstance(claims, (list, dict)) and claims:
                print(f"  ✓ Success - claims in response: {len(claims)}")
                results_suite1.append((test_case['name'], 'SUCCESS'))
            else:
                print(f"  ✗ Success but no claims in response")
                results_suite1.append((test_case['name'], 'NO_CLAIMS'))
        else:
            print(f"  ✗ No success indicator")
            results_suite1.append((test_case['name'], 'NO_SUCCESS'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:60]}")
        results_suite1.append((test_case['name'], 'EXCEPTION'))

    time.sleep(0.5)

print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 2: Dedicated Lexeme API Endpoints
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 2: Dedicated Lexeme API endpoints")
print("=" * 80)
print()

lexeme_endpoints = [
    {
        'name': 'wbladdsense - Add sense to existing lexeme',
        'action': 'wbladdsense',
        'params': {
            'lexemeid': 'L75',
            'data': json.dumps({
                'glosses': {
                    'en': {'language': 'en', 'value': 'Test sense gloss'}
                }
            }),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': 'wbladdform - Add form to existing lexeme',
        'action': 'wbladdform',
        'params': {
            'lexemeid': 'L75',
            'data': json.dumps({
                'representations': {
                    'en': {'language': 'en', 'value': 'test-form'}
                },
                'grammaticalFeatures': ['Q1']
            }),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': 'wbladdformtolex - Alternative form addition',
        'action': 'wbladdformtolex',
        'params': {
            'lexemeid': 'L75',
            'data': json.dumps({
                'representations': {
                    'en': {'language': 'en', 'value': 'alt-form'}
                }
            }),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': 'wbleditentity - Direct lexeme edit with senses',
        'action': 'wbeditentity',
        'params': {
            'id': 'L75',
            'data': json.dumps({
                'senses': {
                    'L75-S1': {
                        'glosses': {
                            'en': {'language': 'en', 'value': 'gloss test'}
                        }
                    }
                }
            }),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': 'wbleditentity - Direct lexeme edit with forms',
        'action': 'wbeditentity',
        'params': {
            'id': 'L75',
            'data': json.dumps({
                'forms': {
                    'L75-F1': {
                        'representations': {
                            'en': {'language': 'en', 'value': 'form-test'}
                        }
                    }
                }
            }),
            'token': csrf_token,
            'format': 'json'
        }
    },
    {
        'name': 'wbeditentity - Direct lexeme edit with lemma',
        'action': 'wbeditentity',
        'params': {
            'id': 'L75',
            'data': json.dumps({
                'lemmas': {
                    'en': {'language': 'en', 'value': 'updated-lemma'}
                }
            }),
            'token': csrf_token,
            'format': 'json'
        }
    }
]

results_suite2 = []
for i, endpoint in enumerate(lexeme_endpoints):
    print(f"Test 2.{i+1}: {endpoint['name']}")
    print(f"  Action: {endpoint['action']}")

    try:
        r = session.post(API_URL, data=endpoint['params'])
        result = r.json()

        if 'error' in result:
            error_code = result['error'].get('code', 'unknown')
            error_info = result['error'].get('info', '')
            status = f"✗ Error: {error_code}"
            if error_info:
                status += f" - {error_info[:50]}"
            print(f"  {status}")
            results_suite2.append((endpoint['name'], 'ERROR'))
        elif 'success' in result and result['success']:
            entity = result.get('entity', {})
            if entity:
                print(f"  ✓ Success - entity returned")
                results_suite2.append((endpoint['name'], 'SUCCESS'))
            else:
                print(f"  ✗ Success but no entity in response")
                results_suite2.append((endpoint['name'], 'NO_ENTITY'))
        else:
            keys = list(result.keys())
            print(f"  ✗ No success indicator (keys: {', '.join(keys)})")
            results_suite2.append((endpoint['name'], 'NO_SUCCESS'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:60]}")
        results_suite2.append((endpoint['name'], 'EXCEPTION'))

    time.sleep(0.5)

print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 3: Creating NEW Lexemes with Different Methods
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 3: Creating NEW lexemes with different structures")
print("=" * 80)
print()

new_lexeme_tests = [
    {
        'name': 'Create lexeme with minimal data (lemmas only)',
        'data': {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-new-minimal'}
            },
            'language': 'Q1860'
        }
    },
    {
        'name': 'Create lexeme with senses in creation',
        'data': {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-with-sense'}
            },
            'language': 'Q1860',
            'senses': {
                'L-temp-S1': {
                    'glosses': {
                        'en': {'language': 'en', 'value': 'test gloss'}
                    }
                }
            }
        }
    },
    {
        'name': 'Create lexeme with forms in creation',
        'data': {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-with-form'}
            },
            'language': 'Q1860',
            'forms': {
                'L-temp-F1': {
                    'representations': {
                        'en': {'language': 'en', 'value': 'test form'}
                    }
                }
            }
        }
    },
    {
        'name': 'Create lexeme with claims in creation',
        'data': {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-with-claims'}
            },
            'language': 'Q1860',
            'claims': [
                {
                    'mainsnak': {
                        'snaktype': 'value',
                        'property': 'P1',
                        'datavalue': {
                            'value': {'entity-type': 'item', 'numeric-id': 10},
                            'type': 'wikibase-entityid'
                        }
                    },
                    'type': 'statement',
                    'rank': 'normal'
                }
            ]
        }
    },
    {
        'name': 'Create lexeme with lexical category',
        'data': {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-with-lexcat'}
            },
            'language': 'Q1860',
            'lexicalCategory': 'Q1'
        }
    }
]

results_suite3 = []
for i, test_case in enumerate(new_lexeme_tests):
    print(f"Test 3.{i+1}: {test_case['name']}")

    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'new': 'lexeme',
            'data': json.dumps(test_case['data']),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            status = f"✗ Error: {result['error'].get('info', result['error'].get('code'))}"
            print(f"  {status}")
            results_suite3.append((test_case['name'], 'ERROR'))
        elif 'entity' in result:
            entity = result['entity']
            lex_id = entity.get('id', 'unknown')

            # Check what actually made it through
            has_senses = bool(entity.get('senses'))
            has_forms = bool(entity.get('forms'))
            has_claims = bool(entity.get('claims'))

            status = f"✓ Created: {lex_id}"
            if has_senses:
                status += " [senses ✓]"
            if has_forms:
                status += " [forms ✓]"
            if has_claims:
                status += " [claims ✓]"

            print(f"  {status}")
            results_suite3.append((test_case['name'], f"CREATED: {lex_id}"))
        else:
            print(f"  ✗ Unexpected response")
            results_suite3.append((test_case['name'], 'UNEXPECTED'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:60]}")
        results_suite3.append((test_case['name'], 'EXCEPTION'))

    time.sleep(0.5)

print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 4: Senses and Forms via wbgetentities
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 4: Querying sense/form structure from existing lexeme")
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

        print("L61 structure in API response:")
        print(f"  Type: {L61.get('type')}")
        print(f"  Lemmas: {L61.get('lemmas', {})}")
        print(f"  Language: {L61.get('language')}")
        print(f"  Lexical category: {L61.get('lexicalCategory')}")
        print(f"  Senses: {len(L61.get('senses', {})) if isinstance(L61.get('senses'), dict) else 'N/A'}")
        print(f"  Forms: {len(L61.get('forms', {})) if isinstance(L61.get('forms'), dict) else 'N/A'}")
        print(f"  Claims: {L61.get('claims', {})}")

        if L61.get('senses'):
            print(f"\n  Sense structure (first sense):")
            first_sense_key = list(L61['senses'].keys())[0]
            first_sense = L61['senses'][first_sense_key]
            print(f"    ID: {first_sense_key}")
            print(f"    Glosses: {first_sense.get('glosses', {})}")
            print(f"    Claims: {first_sense.get('claims', {})}")

        print()
except Exception as e:
    print(f"✗ Failed to query L61: {e}")
    print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 5: Property Type Variations
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 5: Different property value types on lexemes")
print("=" * 80)
print()

property_tests = [
    {
        'name': 'P1 Q10 (wikibase-item)',
        'property': 'P1',
        'snaktype': 'value',
        'datavalue': {
            'value': {'entity-type': 'item', 'numeric-id': 10},
            'type': 'wikibase-entityid'
        }
    },
    {
        'name': 'String value (if any string property exists)',
        'property': 'P6',  # May or may not exist
        'snaktype': 'value',
        'datavalue': {
            'value': 'test string value',
            'type': 'string'
        }
    },
    {
        'name': 'novalue snak type',
        'property': 'P1',
        'snaktype': 'novalue',
        'datavalue': None
    },
    {
        'name': 'somevalue snak type',
        'property': 'P1',
        'snaktype': 'somevalue',
        'datavalue': None
    }
]

results_suite5 = []
for i, test_case in enumerate(property_tests):
    print(f"Test 5.{i+1}: {test_case['name']}")

    claim_data = {
        'mainsnak': {
            'snaktype': test_case['snaktype'],
            'property': test_case['property']
        },
        'type': 'statement',
        'rank': 'normal'
    }

    if test_case['datavalue']:
        claim_data['mainsnak']['datavalue'] = test_case['datavalue']

    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': 'L75',
            'data': json.dumps({'claims': [claim_data]}),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            print(f"  ✗ Error: {result['error'].get('code')}")
            results_suite5.append((test_case['name'], 'ERROR'))
        elif 'success' in result:
            entity = result.get('entity', {})
            claims = entity.get('claims', [])
            if claims:
                print(f"  ✓ Claims in response")
                results_suite5.append((test_case['name'], 'SUCCESS'))
            else:
                print(f"  ✗ No claims in response")
                results_suite5.append((test_case['name'], 'NO_CLAIMS'))
        else:
            print(f"  ✗ No success indicator")
            results_suite5.append((test_case['name'], 'NO_SUCCESS'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:60]}")
        results_suite5.append((test_case['name'], 'EXCEPTION'))

    time.sleep(0.5)

print()

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("COMPREHENSIVE RESULTS SUMMARY")
print("=" * 80)
print()

print("Suite 1 - wbeditentity with different claim formats:")
for name, result in results_suite1:
    status = "✓" if result == "SUCCESS" else "✗"
    print(f"  {status} {result}: {name[:50]}")

print()
print("Suite 2 - Dedicated Lexeme API endpoints:")
for name, result in results_suite2:
    status = "✓" if result == "SUCCESS" else "✗"
    print(f"  {status} {result}: {name[:50]}")

print()
print("Suite 3 - Creating new lexemes:")
for name, result in results_suite3:
    status = "✓" if "CREATED" in result else "✗"
    print(f"  {status} {result}: {name[:50]}")

print()
print("Suite 5 - Property value types:")
for name, result in results_suite5:
    status = "✓" if result == "SUCCESS" else "✗"
    print(f"  {status} {result}: {name[:50]}")

print()
print("CONCLUSION:")
working_methods = []
if any(r == "SUCCESS" for _, r in results_suite1):
    working_methods.append("wbeditentity with certain claim formats")
if any("SUCCESS" in r for _, r in results_suite2):
    working_methods.append("Dedicated lexeme endpoints")
if any("CREATED" in r for _, r in results_suite3):
    working_methods.append("Creating new lexemes")

if working_methods:
    print(f"✓ Found working methods: {', '.join(working_methods)}")
else:
    print("✗ No working methods found for claims/senses/forms on Aelaki lexemes")
