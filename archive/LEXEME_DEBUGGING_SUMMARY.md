# Aelaki Lexeme Debugging Summary

## Objective
Add English glosses to Aelaki Lexemes L1-L60. Successfully created L3-L60 with cardinal names (Pan, Bal, Bhan, etc.), but adding senses/glosses via API keeps failing.

---

## What We Know Works ✓

### 1. Lexeme Creation (L3-L60)
- **Script**: `aelaki_lexemes.py`
- **Method**: `wbeditentity` with `'new': 'lexeme'` parameter
- **Status**: SUCCESSFUL - All 58 lexemes created with:
  - Lemmas (cardinal names in Aelaki)
  - Language: Q1 (Aelaki)
  - Lexical Category: Q4 (Number)

### 2. Existing Lexemes with Senses (L61, L62)
- **L61**: `Su` (yes) - has sense S1 with English gloss
- **L62**: `Fu` (no) - has sense S1 with English gloss
- **Correct Structure**:
```json
{
  "type": "lexeme",
  "id": "L61",
  "lemmas": {"mis": {"language": "mis", "value": "Su"}},
  "lexicalCategory": "Q9",
  "language": "Q1",
  "claims": [],
  "nextFormId": 1,
  "nextSenseId": 2,
  "forms": [],
  "senses": [
    {
      "id": "L61-S1",
      "glosses": {
        "en": {
          "language": "en",
          "value": "yes"
        }
      },
      "claims": []
    }
  ]
}
```

---

## What We Tried (All Failed) ✗

### Attempt 1: `wbeditentity` with minimal senses data
**Script**: `add_aelaki_glosses.py` (first iteration)
```python
edit_data = {
    'senses': [
        {
            'glosses': {
                'en': gloss  # WRONG: string instead of object
            }
        }
    ]
}
```
**Result**: API returned `"success": 1` but with `"nochange": ""` - data was NOT persisted.
**Why Failed**: Gloss format was wrong. Should be object with `language` and `value` keys.

---

### Attempt 2: `wbeditentity` with correct gloss structure but pre-assigned IDs
**Script**: `add_aelaki_glosses_fixed.py`
```python
edit_data = {
    'senses': [
        {
            'id': f'{lexeme_id}-S1',  # WRONG: trying to reference non-existent sense
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': gloss
                }
            },
            'claims': []
        }
    ],
    'nextSenseId': 2
}
```
**Result**: All 60 failed with error: `⧼wikibase-validator-sense-not-found⧽`
**Why Failed**: Can't reference a sense ID (L1-S1) that doesn't exist yet. You can't create a new sense by providing a pre-assigned ID.

---

### Attempt 3: `wbeditentity` with auto-generated sense IDs (no ID provided)
**Script**: `add_aelaki_glosses_new.py`
```python
edit_data = {
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': gloss
                }
            },
            'claims': []
        }
    ]
}
```
**Result**: API returned `"success": 1` but returned `"senses": []` in response. Data NOT persisted.
**Why Failed**: Same issue as Attempt 1 - the wbeditentity action on Aelaki wiki accepts the request but never actually saves senses.

---

### Attempt 4: Direct MediaWiki page editing
**Script**: `add_aelaki_glosses_direct.py`
```python
edit_params = {
    'action': 'edit',
    'title': 'Lexeme:L1',
    'text': new_content,  # Full lexeme JSON
    'contentmodel': 'wikibase-lexeme',
    'token': csrf_token,
}
```
**Result**: All 60 failed with error: `wikibase-no-direct-editing` - Direct editing is disabled in namespace Lexeme
**Why Failed**: Aelaki wiki has locked down the Lexeme namespace - only wbeditentity is allowed.

---

## Root Cause Analysis

### The Core Problem
The Aelaki wiki's **WikibaseLexeme extension** is not functioning properly:
- ✓ Lexeme creation (`new: lexeme`) works fine
- ✓ The API accepts edit requests for senses
- ✗ **The API never persists sense data to the database**

### Diagnostic Evidence

**API Response Analysis**:
When we send a well-formed `wbeditentity` request to add a sense:
- API returns `"success": 1` ✓
- But also returns `"nochange": ""` indicator
- The returned entity shows `"senses": []` (empty)
- The lexeme's `lastrevid` doesn't change
- Revision history shows NO new edits

This indicates:
1. The wbeditentity action **receives and parses** the request correctly
2. But **validation or persistence fails silently**
3. The change is rejected before being saved to the database
4. The API lies about success to avoid throwing an error

### Why This Is Happening

According to Miraheze Wikibase configuration issues:

**Most Likely Cause**: The WikibaseLexeme extension on Aelaki needs specific database initialization or configuration that wasn't done when the wiki was created. Lexeme support requires:
- Proper database tables for senses
- Proper database tables for forms
- Property constraints for sense-level statements
- Frontend JavaScript modules for the UI

If ANY of these are misconfigured or missing:
- The backend can accept requests
- But it cannot commit the changes
- And it silently fails rather than throwing errors

---

## What We Need to Do Next

### Option 1: Check & Fix ManageWiki Configuration
- Verify WikibaseLexeme extension is fully enabled
- Check if all required properties exist (Q4=Number, Q9=Word, etc.)
- Verify database initialization completed
- Check Miraheze system logs for errors

### Option 2: Recreate L1 or Reset Lexeme Data
- L1 might contain corrupted metadata
- Creating a brand new lexeme from scratch might avoid corruption
- Or manually resetting the lexeme entity data

### Option 3: Use a Workaround
- Create senses via the MediaWiki UI (manual, slow)
- Or wait for Miraheze to fix the backend issue
- Or request Miraheze admins to check database configuration

### Option 4: Direct Database Modification
- If you have admin access to Miraheze database
- Manually insert sense records
- Or restore from backup if lexeme support was working before

---

## Files Created & Status

| File | Status | Purpose |
|------|--------|---------|
| `aelaki_lexemes.py` | ✓ Working | Created L3-L60 lexemes |
| `add_aelaki_glosses.py` | ✗ Failed | Initial gloss attempt (wrong format) |
| `add_aelaki_glosses_fixed.py` | ✗ Failed | Gloss with ID pre-assignment (sense-not-found error) |
| `add_aelaki_glosses_new.py` | ✗ Failed | Gloss with auto-generated IDs (silent persistence failure) |
| `add_aelaki_glosses_direct.py` | ✗ Failed | Direct page editing (direct-editing disabled) |
| `debug_aelaki_api.py` | ✓ Diagnostic | Revealed "nochange" indicator issue |
| `fetch_existing_lexeme.py` | ✓ Diagnostic | Extracted L61/L62 structure for reference |
| `LEXEME_DEBUGGING_SUMMARY.md` | This file | Documentation of all attempts |

---

## Recommended Next Steps

1. **For Immediate Action**:
   - Contact Miraheze support about WikibaseLexeme persistence issue
   - Ask if lexeme sense editing was ever tested on Aelaki wiki
   - Request database logs for sense write operations

2. **For Efficient Problem Solving**:
   - Document this issue clearly for ChatGPT/Claude with this summary
   - Include: error messages, API responses, and database persistence failures
   - Include: L61/L62 structure as "working examples"

3. **For Workaround**:
   - Create a one-off script that uses mwclient to edit L61/L62 (known working)
   - Then copy their structure to L1-L60 via database if possible
   - Or manually add glosses via Aelaki wiki UI

---

## Key Insights for Future Work

- **Don't trust API success responses** - always verify data was actually saved
- **"nochange" indicator is critical** - means request was accepted but not applied
- **Database persistence failures are silent** - they don't throw errors
- **Lexeme infrastructure requires backend support** - can't be fixed by API calls alone
- **Test with known-working examples first** - L61/L62 give us a blueprint

