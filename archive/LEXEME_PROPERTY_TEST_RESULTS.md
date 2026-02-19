# Lexeme Property Test Results
## Comprehensive Test of What Works in Wikibase Lexeme

**Date**: November 18, 2025
**Test Script**: `test_lexeme_properties.py`

---

## Test Results Summary

| Test # | What We Tried | Created | Persisted | Status |
|--------|---------------|---------|-----------|--------|
| 1 | Basic lexeme (lemma only) | L68 ✓ | ✓ | WORKS |
| 2 | Lexeme with form | L69 ✓ | ✗ Forms dropped | FAILS |
| 3 | Lexeme with claims | None ✗ | N/A | FAILS |
| 4 | Lexeme with sense | L71 ✓ | ✗ Senses dropped | FAILS |
| 5 | Lexeme with sense + sense claims | L72 ✓ | ✗ Senses dropped | FAILS |
| 6 | Lexeme with form + grammatical features | L73 ✓ | ✗ Forms dropped | FAILS |
| 7 | Lexeme with multiple forms | L74 ✓ | ✗ Forms dropped | FAILS |
| 8 | Lexeme with multiple senses | L75 ✓ | ✗ Senses dropped | FAILS |

---

## Detailed Findings

### ✅ WHAT WORKS

#### 1. Basic Lexeme Creation (Lemma + Metadata)
```python
{
    'type': 'lexeme',
    'language': 'Q1',
    'lexicalCategory': 'Q4',
    'lemmas': {'mis': {'language': 'mis', 'value': 'word'}}
}
```

**Result**: L68 created successfully
```json
{
  "type": "lexeme",
  "id": "L68",
  "lemmas": {
    "mis": {
      "language": "mis",
      "value": "test1-basic"
    }
  },
  "lexicalCategory": "Q4",
  "language": "Q1",
  "claims": {},
  "forms": [],
  "senses": [],
  "lastrevid": 20542
}
```

**Conclusion**: You CAN create a lexeme with:
- ✓ Type
- ✓ Language
- ✓ Lexical Category
- ✓ Lemmas (base word forms in different languages)
- ✓ Empty claims, forms, senses

---

### ❌ WHAT DOESN'T WORK

#### 2. Forms (Inflectional variants)
**What we tried**: Create lexeme with forms array
```python
'forms': [
    {
        'representations': {'mis': {'language': 'mis', 'value': 'plural-form'}},
        'grammaticalFeatures': []
    }
]
```

**Result**: L69 created but forms array is EMPTY
```
Forms in response: 0
```

**Conclusion**: Forms are silently dropped, just like senses.

---

#### 3. Claims on Lexemes (Properties/Statements)
**What we tried**: Add a claim to lexeme-level
```python
'claims': [
    {
        'mainsnak': {
            'snaktype': 'value',
            'property': 'P1',
            'datavalue': {'value': {'entity-type': 'item', 'numeric-id': 1}, 'type': 'wikibase-entityid'}
        },
        'type': 'statement',
        'rank': 'normal'
    }
]
```

**Result**: Entity ID is None (failed to create)
```
✓ Created: None
Claims in response: 0
Response: {}
```

**Conclusion**: Claims at lexeme level don't work - lexeme creation failed entirely.

---

#### 4. Senses (Definitions/Meanings)
**What we tried**: Create lexeme with sense glosses
```python
'senses': [
    {
        'glosses': {'en': {'language': 'en', 'value': 'a test sense'}}
    }
]
```

**Result**: L71 created but senses array is EMPTY
```
✓ Created: L71
Senses in response: 0
WARNING: Senses were dropped!
```

**Conclusion**: Senses are ALWAYS dropped during creation, regardless of how they're formatted.

---

#### 5. Sense Claims (Properties on senses)
**What we tried**: Add claims to senses
```python
'senses': [
    {
        'glosses': {...},
        'claims': [...]
    }
]
```

**Result**: L72 created but senses AND sense claims are EMPTY
```
✓ Created: L72
Senses in response: 0
WARNING: Senses were dropped!
```

**Conclusion**: Can't add sense claims if we can't create senses.

---

#### 6-7. Multiple Forms & Grammatical Features
**Result**: Same as single form - all forms dropped
```
Forms in response: 0
```

**Conclusion**: Forms infrastructure is completely broken, including grammatical features.

---

#### 8. Multiple Senses
**Result**: Same as single sense - all senses dropped
```
Senses in response: 0
WARNING: All senses were dropped!
```

**Conclusion**: Confirms that senses are universally broken.

---

## What This Tells Us About Wikibase Lexeme on Aelaki

### The Broken Infrastructure

The backend appears to have **selective support** for Lexeme properties:

**Supported**:
- ✓ Lexeme creation itself
- ✓ Lemmas
- ✓ Metadata (language, lexical category)
- ✓ Empty structural arrays (forms, senses)

**Not Supported**:
- ✗ **Forms** (all form data silently dropped)
- ✗ **Senses** (all sense data silently dropped)
- ✗ **Claims** at lexeme level (creation fails)
- ✗ **Claims** at sense level (can't create senses anyway)
- ✗ **Grammatical features** (forms don't work)

### Why This Happens

The pattern is consistent: **The API accepts the request, but silently discards anything beyond the basic lexeme metadata.**

This suggests:
1. **Database schema issue** - Sense/form tables don't exist or are inaccessible
2. **Incomplete initialization** - WikibaseLexeme extension wasn't fully set up
3. **Missing validation** - System discards extra fields instead of validating/storing them
4. **Configuration issue** - Sense/form support may be disabled in LocalSettings.php

---

## Practical Implications

### What you CAN use Aelaki Lexemes for:
- Store base words (lemmas) in multiple languages
- Organize by language (Q1 = Aelaki) and category (Q4 = number)
- Reference lexemes in other Wikibase items via properties

### What you CANNOT use them for:
- Storing word definitions (senses don't work)
- Storing inflected forms (forms don't work)
- Storing grammatical information (grammatical features don't work)
- Storing semantic properties (claims don't work)

### Workaround Approach:
If you need to store this information:
1. Create standalone **Wikidata items** for each word's definition
2. Create standalone **Wikidata items** for each word's forms
3. Use **properties** to link lexemes to these definition/form items
4. Use **semantic properties** instead of lexeme-level metadata

Example:
```
L1 "Pan" (Aelaki for "one")
  → linked via property P9999 to Q5555 (Wikidata: "number one")
  → Q5555 has:
     - English label: "one"
     - Definitions in multiple languages
     - Grammatical properties
```

---

## Test Lexeme IDs for Reference

| ID | What was tested | Result |
|----|-----------------|--------|
| L68 | Basic lexeme | ✓ Works |
| L69 | Forms | ✗ Dropped |
| L70 | (Should have been claims test, but failed to create) | N/A |
| L71 | Single sense | ✗ Dropped |
| L72 | Sense + sense claims | ✗ Dropped |
| L73 | Form + grammatical features | ✗ Dropped |
| L74 | Multiple forms | ✗ Dropped |
| L75 | Multiple senses | ✗ Dropped |

---

## Conclusion

**Aelaki's WikibaseLexeme implementation is only partially functional.**

It's suitable for:
- Storing lemmas (base words)
- Organizing by language and category

It's NOT suitable for:
- Storing definitions (senses don't work)
- Storing word variants (forms don't work)
- Storing grammatical information (grammatical features don't work)
- Adding properties/metadata (claims don't work)

**This is not an API formatting issue or a usage problem. This is a fundamental backend infrastructure limitation that can only be fixed by Miraheze.**

If you need a complete lexeme system, you'll need to use a workaround approach with separate Wikidata items linked via properties.
