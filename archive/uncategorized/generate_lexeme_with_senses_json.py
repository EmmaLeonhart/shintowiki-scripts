#!/usr/bin/env python3
"""
generate_lexeme_with_senses_json.py
===================================
Generate the raw JSON structure needed for lexemes with senses.
This shows what format is needed to create/modify lexemes with senses that will persist.
"""

import json

# This is the structure that L61 has (working example)
l61_structure = {
    "pageid": 1242,
    "ns": 146,
    "title": "Lexeme:L61",
    "type": "lexeme",
    "id": "L61",
    "lemmas": {
        "mis": {
            "language": "mis",
            "value": "Su"
        }
    },
    "language": "Q1",
    "lexicalCategory": "Q9",
    "senses": [
        {
            "id": "L61-S1",
            "glosses": {
                "en": {
                    "language": "en",
                    "value": "yes [TEST_MARKER_1763506298]"
                }
            },
            "claims": []
        }
    ],
    "claims": {
        "P1": [
            {
                "mainsnak": {
                    "snaktype": "value",
                    "property": "P1",
                    "datavalue": {
                        "value": {
                            "entity-type": "item",
                            "numeric-id": 10,
                            "id": "Q10"
                        },
                        "type": "wikibase-entityid"
                    }
                },
                "type": "statement",
                "rank": "normal"
            }
        ]
    },
    "forms": []
}

print("=" * 80)
print("L61 WORKING STRUCTURE (with senses)")
print("=" * 80)
print(json.dumps(l61_structure, indent=2))

print("\n\n" + "=" * 80)
print("WHAT'S NEEDED TO CREATE SENSES")
print("=" * 80)
print("""
Key observations:
1. Senses are stored as a LIST [], not a dict
2. Each sense has:
   - "id": like "L61-S1" (required!)
   - "glosses": dict with language keys
   - "claims": empty list (can add claims to senses)

3. The sense ID must follow the pattern: {LEXEME_ID}-S{NUMBER}

So to add a sense to L75:
- Create sense ID: "L75-S1"
- Add glosses with language (e.g., "en")
- Include as array element

4. This structure needs to be stored in the Lexeme page content
   (either via wiki editor or direct database)

The API won't CREATE new senses - it can only MODIFY existing ones.
Therefore, sense IDs must be pre-created somehow.
""")

print("\n" + "=" * 80)
print("TEMPLATE FOR NEW LEXEME WITH SENSES")
print("=" * 80)

template_lexeme = {
    "type": "lexeme",
    "id": "L_NEW",
    "lemmas": {
        "en": {
            "language": "en",
            "value": "example-word"
        }
    },
    "language": "Q1",
    "lexicalCategory": "Q9",
    "senses": [
        {
            "id": "L_NEW-S1",
            "glosses": {
                "en": {
                    "language": "en",
                    "value": "First meaning"
                }
            },
            "claims": []
        },
        {
            "id": "L_NEW-S2",
            "glosses": {
                "en": {
                    "language": "en",
                    "value": "Second meaning"
                }
            },
            "claims": []
        }
    ],
    "forms": [],
    "claims": {}
}

print(json.dumps(template_lexeme, indent=2))

print("\n\n" + "=" * 80)
print("POSSIBLE SOLUTIONS")
print("=" * 80)
print("""
Option 1: Create sense IDs via MediaWiki Special:NewLexeme interface
- Manually add senses to lexemes through the wiki UI
- Then modify them via API

Option 2: Create raw JSON pages directly
- Use the MediaWiki API to save JSON content directly to Lexeme pages
- But this might bypass validation

Option 3: Use wikibase:editentity with lemmas only first
- Create lexeme with just lemma
- Then somehow inject sense structure into the raw data

Option 4: Examine the database directly
- Insert sense records directly into the lexeme storage
- This is what the manual UI editing does

Option 5: Check if there's an undocumented sense creation endpoint
- Some Wikibase installations have wbaddsense that actually works
- But it returns JSON parse errors on Aelaki (endpoints exist but broken)
""")
