#!/usr/bin/env python3
"""
test_all_sense_methods.py
=========================
Test EVERY POSSIBLE way to add senses to Lexemes on Aelaki.
Try all documented Wikibase versions and methods.
Focus on correctly specifying the sense language as English.
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
# TEST SUITE 1: Adding senses via wbeditentity (different structure versions)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 1: Adding senses via wbeditentity")
print("=" * 80)
print()

sense_tests = [
    {
        'name': 'Method 1: Senses as dict with English glosses (proper format)',
        'data': {
            'senses': {
                'L70-S1': {
                    'glosses': {
                        'en': {
                            'language': 'en',
                            'value': 'Test gloss for sense 1'
                        }
                    }
                }
            }
        }
    },
    {
        'name': 'Method 2: Senses as dict with just gloss value (minimal)',
        'data': {
            'senses': {
                'L70-S2': {
                    'glosses': {
                        'en': 'Test gloss for sense 2'
                    }
                }
            }
        }
    },
    {
        'name': 'Method 3: Senses as list with English glosses',
        'data': {
            'senses': [
                {
                    'glosses': {
                        'en': {
                            'language': 'en',
                            'value': 'Test gloss for sense 3'
                        }
                    }
                }
            ]
        }
    },
    {
        'name': 'Method 4: Senses with sense ID auto-generation',
        'data': {
            'senses': {
                'L70-S4': {
                    'glosses': {
                        'en': 'Sense 4'
                    }
                },
                'L70-S5': {
                    'glosses': {
                        'en': 'Sense 5'
                    }
                }
            }
        }
    },
    {
        'name': 'Method 5: Senses with claims (sense properties)',
        'data': {
            'senses': {
                'L70-S6': {
                    'glosses': {
                        'en': 'Sense with claims'
                    },
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
            }
        }
    },
    {
        'name': 'Method 6: Senses with multiple language glosses',
        'data': {
            'senses': {
                'L70-S7': {
                    'glosses': {
                        'en': {'language': 'en', 'value': 'English gloss'},
                        'ja': {'language': 'ja', 'value': '日本語の意味'}
                    }
                }
            }
        }
    },
    {
        'name': 'Method 7: Senses in old format (no language wrapper)',
        'data': {
            'senses': {
                'L70-S8': {
                    'glosses': 'Simple gloss string'
                }
            }
        }
    },
    {
        'name': 'Method 8: Senses as embedded in main entity structure',
        'data': {
            'type': 'lexeme',
            'senses': {
                'L70-S9': {
                    'glosses': {
                        'en': 'Embedded sense'
                    }
                }
            }
        }
    }
]

results_suite1 = []
for i, test_case in enumerate(sense_tests):
    print(f"Test 1.{i+1}: {test_case['name']}")

    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': 'L70',
            'data': json.dumps(test_case['data']),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            error_code = result['error'].get('code', 'unknown')
            error_info = result['error'].get('info', '')
            print(f"  ✗ Error: {error_code}")
            if error_info and error_info != error_code:
                print(f"    Info: {error_info[:70]}")
            results_suite1.append((test_case['name'], 'ERROR'))
        elif 'entity' in result:
            entity = result['entity']
            senses = entity.get('senses', {})

            if senses:
                sense_count = len(senses) if isinstance(senses, dict) else len(senses) if isinstance(senses, list) else 0
                print(f"  ✓ Success - {sense_count} senses in response")
                results_suite1.append((test_case['name'], f'SUCCESS ({sense_count} senses)'))
            else:
                print(f"  ✗ Success but no senses in response")
                results_suite1.append((test_case['name'], 'NO_SENSES'))
        else:
            keys = list(result.keys())
            print(f"  ✗ Unexpected response (keys: {', '.join(keys[:3])})")
            results_suite1.append((test_case['name'], 'UNEXPECTED'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:60]}")
        results_suite1.append((test_case['name'], 'EXCEPTION'))

    time.sleep(0.3)

print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 2: Creating NEW lexemes with senses (different approaches)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 2: Creating new lexemes WITH senses")
print("=" * 80)
print()

# First, check what language entities exist
print("Checking available language entities...")
r = session.get(API_URL, params={
    'action': 'query',
    'titles': 'Item:Q1|Item:Q2',
    'format': 'json'
})

# Use Q1 as fallback, try multiple language IDs
language_options = ['Q1', 'Q2', 'Q1860']

new_lex_tests = [
    {
        'name': 'Create lexeme with sense in creation (Q1 language)',
        'lang': 'Q1',
        'data_func': lambda lang: {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-lex-with-sense'}
            },
            'language': lang,
            'senses': {
                'L-temp-S1': {
                    'glosses': {
                        'en': {'language': 'en', 'value': 'Test sense gloss'}
                    }
                }
            }
        }
    },
    {
        'name': 'Create lexeme with sense and claims',
        'lang': 'Q1',
        'data_func': lambda lang: {
            'type': 'lexeme',
            'lemmas': {
                'en': {'language': 'en', 'value': 'test-lex-sense-claims'}
            },
            'language': lang,
            'senses': {
                'L-temp-S1': {
                    'glosses': {
                        'en': 'Sense with claims'
                    },
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
            }
        }
    }
]

results_suite2 = []
for i, test_case in enumerate(new_lex_tests):
    print(f"Test 2.{i+1}: {test_case['name']}")

    try:
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'new': 'lexeme',
            'data': json.dumps(test_case['data_func'](test_case['lang'])),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            error_info = result['error'].get('info', result['error'].get('code'))
            print(f"  ✗ Error: {error_info[:60]}")
            results_suite2.append((test_case['name'], 'ERROR'))
        elif 'entity' in result:
            entity = result['entity']
            lex_id = entity.get('id', '?')
            senses = entity.get('senses', {})

            if senses:
                sense_count = len(senses) if isinstance(senses, dict) else len(senses) if isinstance(senses, list) else 0
                print(f"  ✓ Created {lex_id} - {sense_count} senses in response")
                results_suite2.append((test_case['name'], f'SUCCESS ({lex_id})'))
            else:
                print(f"  ✓ Created {lex_id} - but no senses in response")
                results_suite2.append((test_case['name'], f'CREATED NO SENSES ({lex_id})'))
        else:
            print(f"  ✗ Unexpected response")
            results_suite2.append((test_case['name'], 'UNEXPECTED'))
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:60]}")
        results_suite2.append((test_case['name'], 'EXCEPTION'))

    time.sleep(0.3)

print()

# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 3: Query L70 to see what actually persisted
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST SUITE 3: Verify what persisted on L70")
print("=" * 80)
print()

try:
    r = session.get(API_URL, params={
        'action': 'wbgetentities',
        'ids': 'L70',
        'format': 'json'
    })
    result = r.json()

    if 'entities' in result and 'L70' in result['entities']:
        L70 = result['entities']['L70']

        senses = L70.get('senses', {})
        print(f"L70 current state:")
        print(f"  Senses in API: {len(senses) if isinstance(senses, (dict, list)) else 'N/A'}")

        if senses and isinstance(senses, dict):
            print(f"  Sense IDs: {', '.join(list(senses.keys())[:5])}")
            first_sense_id = list(senses.keys())[0]
            first_sense = senses[first_sense_id]
            print(f"  First sense glosses: {first_sense.get('glosses', {})}")
            print(f"  First sense claims: {bool(first_sense.get('claims'))}")

        claims = L70.get('claims', {})
        print(f"  Claims in API: {len(claims) if isinstance(claims, dict) else 'N/A'}")

        print("\n✓ L70 query successful - persistence verified")
    else:
        print("✗ L70 not found")
except Exception as e:
    print(f"✗ Failed to query L70: {e}")

print()

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print()

print("Suite 1 - Adding senses to existing lexeme (L70):")
working_count = 0
for name, result in results_suite1:
    if 'SUCCESS' in result:
        print(f"  ✓ {result}: {name[:50]}")
        working_count += 1
    else:
        print(f"  ✗ {result}: {name[:50]}")

print()
print("Suite 2 - Creating new lexemes with senses:")
for name, result in results_suite2:
    status = "✓" if "SUCCESS" in result or "CREATED" in result else "✗"
    print(f"  {status} {result}: {name[:50]}")

print()
print("OVERALL CONCLUSION:")
if working_count > 0:
    print(f"✓ Found {working_count} working method(s) for adding senses!")
else:
    print("✗ No working methods found for adding senses")
    print("  This suggests senses may require a different approach or API method")
