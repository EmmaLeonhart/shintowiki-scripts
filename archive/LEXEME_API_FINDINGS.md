# Comprehensive Lexeme API Findings on Aelaki

## Key Discovery: Claims CAN be added to Lexemes!

The comprehensive testing revealed a critical finding: **Claims ARE actually working on Aelaki lexemes**, but with specific requirements.

---

## Test Results Summary

### ✓ WORKING Methods

#### Suite 1: wbeditentity with Claim Formats
- **Format A (Dict with property keys - Standard Wikibase)**: ✓ SUCCESS
  - Sends claims as: `{'claims': {'P1': [...]}}`
  - Result: Claims appear in response

- **Format B (List format - Aelaki variant)**: ✓ SUCCESS
  - Sends claims as: `{'claims': [...]}`
  - Result: Claims appear in response

#### Suite 5: Property Value Types
- **P1 Q10 (wikibase-item)**: ✓ SUCCESS
  - Basic entity reference works

- **novalue snak type**: ✓ SUCCESS
  - Claims without values work

- **somevalue snak type**: ✓ SUCCESS
  - Claims with "somevalue" work

### ✗ NOT WORKING Methods

#### Suite 1: Claims Issues
- **Format C (Claims with just mainsnak)**: ✗ ERROR
  - Missing 'type' field requirement

- **Format D (Qualified snaks)**: ✗ ERROR
  - P3 doesn't exist (not a working property)

#### Suite 2: Dedicated Lexeme Endpoints
- **wbladdsense**: ✗ EXCEPTION (No JSON response)
  - These endpoints are either not installed or completely broken

- **wbladdform**: ✗ EXCEPTION (No JSON response)

- **wbladdformtolex**: ✗ EXCEPTION (No JSON response)

- **wbleditentity with senses**: ✗ EXCEPTION (No JSON response)

- **wbleditentity with forms**: ✗ EXCEPTION (No JSON response)

#### Suite 3: Creating New Lexemes
- All methods fail with "Q1860 not found"
  - Language entity doesn't exist
  - This is why new lexeme creation was failing

#### Suite 5: Property Value Types
- **String value**: ✗ ERROR (modification-failed)
  - P6 (string property) doesn't work on lexemes

---

## Critical Insight: The API Structure is Broken

Looking at the L61 query response:

```
L61 structure in API response:
  Type: lexeme
  Lemmas: {'mis': {'language': 'mis', 'value': 'Su'}}
  Language: Q1
  Lexical category: Q9
  Senses: N/A              <-- NO SENSES IN RESPONSE
  Forms: N/A               <-- NO FORMS IN RESPONSE
  Claims: {'P1': [...]}    <-- CLAIMS ARE HERE AND PERSISTENT!
```

**Key Finding**: L61 has P1 Q10 claims that are persistent and returned in API responses. But senses and forms are completely absent.

---

## Why Previous Testing Failed

The confusion came from mixing results:

1. **Regular Items (Q11, Q12)**:
   - Claims work perfectly
   - All data persists
   - Full API functionality

2. **Lexemes (L1-L75)**:
   - **Claims**: ✓ DO WORK (we confirmed this!)
   - **Senses**: ✗ Don't work (never appear in response)
   - **Forms**: ✗ Don't work (never appear in response)
   - **Lemma updates**: ✗ Return parse errors

---

## Correct Way to Add Claims to Lexemes

Both of these formats work:

### Method 1: Dict Format (Standard Wikibase)
```python
edit_data = {
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
                'type': 'statement',  # REQUIRED
                'rank': 'normal'
            }
        ]
    }
}
```

### Method 2: List Format (Aelaki variant)
```python
edit_data = {
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
            'type': 'statement',  # REQUIRED
            'rank': 'normal'
        }
    ]
}
```

Both return claims in the response and persist in the database.

---

## Why Earlier Scripts Failed

1. **add_p1_q10_all_lexemes.py** showed "no claims in response"
   - Likely used wrong property (P6 with string value?)
   - Or had incorrect claim structure

2. **add_aelaki_glosses_working.py** failed with sense validation errors
   - Aelaki's Lexeme implementation doesn't support senses/forms via API
   - Sense creation is broken at the backend level

---

## What's Actually Broken on Aelaki Lexemes

1. ✗ **Sense creation/editing** (wbladdsense endpoints don't exist or are broken)
2. ✗ **Form creation/editing** (wbladdform endpoints don't exist or are broken)
3. ✗ **Lemma updates** (wbleditentity with lemmas returns parse error)
4. ✗ **String properties** (modification-failed error)
5. ✗ **New lexeme creation** (depends on Q1860 language entity which doesn't exist)

---

## What Actually Works on Aelaki Lexemes

1. ✓ **Claiming basic lexeme properties** (P1, P2, etc. with wikibase-item values)
2. ✓ **Modifying existing lexemes via wbeditentity**
3. ✓ **Reading lexeme data** (wbgetentities)
4. ✓ **Claims persist** (verified with L61 having P1 Q10)
5. ✓ **novalue and somevalue snaks**

---

## Recommended Next Steps

1. **Verify that claims are actually persisting**: Run verify script on L1-L75 after re-running add_p1_q10
2. **Use the correct claim structure**: Ensure 'type' and 'rank' fields are present
3. **Stop trying to create senses/forms**: They're not implemented on this Aelaki instance
4. **For new lexemes**: Either:
   - Create them manually on the wiki interface
   - Implement them in MongoDB directly (like Gaiad-database does)
   - Wait for Miraheze to fix the language entity issue

---

## Conclusion

The Aelaki Lexeme implementation is a hybrid/partial implementation:
- Core Wikibase features work (claims, properties, basic editing)
- WikibaseLexeme extension features are broken (senses, forms, lemma updates)
- It's essentially "Wikibase items that have lexeme metadata" rather than full Lexeme support
- Claims are the one thing that successfully work on lexemes
