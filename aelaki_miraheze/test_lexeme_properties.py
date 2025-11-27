#!/usr/bin/env python3
"""
test_lexeme_properties.py
=========================
Comprehensive test of Wikibase Lexeme functionality.
Try creating lexemes with various properties to determine what works and what doesn't.

Tests different combinations of:
- Lemmas
- Forms
- Senses
- Claims (properties/statements)
- Different data structures
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
# TEST 1: Basic Lexeme (just lemma, minimal structure)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 1: Basic Lexeme (Lemma only)")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test1-basic'
        }
    }
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    print(f"✓ Created: {lex_id}")
    print(f"  Structure: {json.dumps(result.get('entity', {}), indent=2)}\n")
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Lexeme with a Form
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 2: Lexeme with Form (plural, inflection)")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test2-form'
        }
    },
    'forms': [
        {
            'representations': {
                'mis': {
                    'language': 'mis',
                    'value': 'test2-form-plural'
                }
            },
            'grammaticalFeatures': []
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    forms = result.get('entity', {}).get('forms', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Forms in response: {len(forms)}")
    if forms:
        print(f"  Form 0: {json.dumps(forms[0], indent=2)}")
    print()
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: Lexeme with Claims (statements/properties)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 3: Lexeme with Claims (statements)")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test3-claims'
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
                        'numeric-id': 1
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
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    claims = result.get('entity', {}).get('claims', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Claims in response: {len(claims)}")
    print(f"  Response: {json.dumps(result.get('entity', {}), indent=2)}\n")
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: Lexeme with Sense (test what happens with senses)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 4: Lexeme with Sense (definition)")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test4-sense'
        }
    },
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'a test sense'
                }
            }
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    senses = result.get('entity', {}).get('senses', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Senses in response: {len(senses)}")
    if senses:
        print(f"  Sense 0: {json.dumps(senses[0], indent=2)}")
    else:
        print(f"  WARNING: Senses were dropped!")
    print()
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: Lexeme with Sense + Claims
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 5: Lexeme with Sense + Sense Claims")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test5-sense-claims'
        }
    },
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'sense with claims'
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
                                'numeric-id': 1
                            },
                            'type': 'wikibase-entityid'
                        }
                    },
                    'type': 'statement',
                    'rank': 'normal'
                }
            ]
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    senses = result.get('entity', {}).get('senses', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Senses in response: {len(senses)}")
    if senses:
        sense_claims = senses[0].get('claims', [])
        print(f"  Claims in sense: {len(sense_claims)}")
        print(f"  Response: {json.dumps(result.get('entity', {}), indent=2)}")
    else:
        print(f"  WARNING: Senses were dropped!")
    print()
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 6: Form with Grammatical Features
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 6: Lexeme with Form + Grammatical Features")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test6-gram-features'
        }
    },
    'forms': [
        {
            'representations': {
                'mis': {
                    'language': 'mis',
                    'value': 'test6-plural'
                }
            },
            'grammaticalFeatures': ['Q146786']  # plural
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    forms = result.get('entity', {}).get('forms', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Forms in response: {len(forms)}")
    if forms:
        features = forms[0].get('grammaticalFeatures', [])
        print(f"  Grammatical features in form: {features}")
        print(f"  Response: {json.dumps(result.get('entity', {}), indent=2)}")
    print()
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 7: Multiple Forms
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 7: Lexeme with Multiple Forms")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test7-multi-form'
        }
    },
    'forms': [
        {
            'representations': {
                'mis': {
                    'language': 'mis',
                    'value': 'form-singular'
                }
            },
            'grammaticalFeatures': []
        },
        {
            'representations': {
                'mis': {
                    'language': 'mis',
                    'value': 'form-plural'
                }
            },
            'grammaticalFeatures': ['Q146786']
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    forms = result.get('entity', {}).get('forms', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Forms in response: {len(forms)}")
    if forms:
        for i, form in enumerate(forms):
            rep = form.get('representations', {}).get('mis', {}).get('value', 'N/A')
            features = form.get('grammaticalFeatures', [])
            print(f"    Form {i}: {rep}, features: {features}")
    print()
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# TEST 8: Multiple Senses
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TEST 8: Lexeme with Multiple Senses")
print("=" * 80)

test_data = {
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {
        'mis': {
            'language': 'mis',
            'value': 'test8-multi-sense'
        }
    },
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'first sense'
                }
            }
        },
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': 'second sense'
                }
            }
        }
    ]
}

try:
    r = session.post(API_URL, data={
        'action': 'wbeditentity',
        'new': 'lexeme',
        'data': json.dumps(test_data),
        'token': csrf_token,
        'format': 'json'
    })
    result = r.json()
    lex_id = result.get('entity', {}).get('id')
    senses = result.get('entity', {}).get('senses', [])
    print(f"✓ Created: {lex_id}")
    print(f"  Senses in response: {len(senses)}")
    if senses:
        for i, sense in enumerate(senses):
            gloss = sense.get('glosses', {}).get('en', {}).get('value', 'N/A')
            print(f"    Sense {i}: {gloss}")
    else:
        print(f"  WARNING: All senses were dropped!")
    print()
except Exception as e:
    print(f"✗ Failed: {e}\n")

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("SUMMARY")
print("=" * 80)

print("""
This test creates 8 different lexemes with various property combinations:

1. Basic lexeme (lemma only) - ✓ EXPECTED TO WORK
2. Lexeme with forms - ? TEST IF FORMS WORK
3. Lexeme with claims - ? TEST IF LEXEME-LEVEL CLAIMS WORK
4. Lexeme with sense - ✗ EXPECTED TO FAIL (senses get dropped)
5. Lexeme with sense + sense claims - ✗ EXPECTED TO FAIL
6. Lexeme with form + grammatical features - ? TEST IF FEATURES WORK
7. Lexeme with multiple forms - ? TEST IF MULTIPLE FORMS WORK
8. Lexeme with multiple senses - ✗ EXPECTED TO FAIL

WHAT WE'RE LOOKING FOR:
========================

In each test response, check:
- Did the lexeme get created? (look for ID in response)
- Did the property/structure persist in the response?
- If not, does it say "nochange" or give an error?

KEY QUESTIONS TO ANSWER:
========================
1. Do forms work? (Test 2, 6, 7)
2. Do claims on lexemes work? (Test 3)
3. Do grammatical features on forms work? (Test 6, 7)
4. Are senses fundamentally broken? (Tests 4, 5, 8)
5. What's the minimum viable structure for a working lexeme?

INTERPRETATION:
================
- If forms appear in response: Forms work
- If forms are empty in response: Forms get dropped like senses
- If claims appear: Lexeme-level properties work
- If senses are always dropped: Sense creation is infrastructure issue
- If grammatical features appear: Form metadata works
""")
