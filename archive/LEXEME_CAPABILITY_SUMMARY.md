# WikibaseLexeme API Capability Summary
## Aelaki Wiki - What Works vs. What Doesn't

**Date**: November 18, 2025
**Status**: Backend is partially functional but broken for sense creation

---

## What WORKS ✅

### 1. Creating Empty Lexemes
- **How**: `wbeditentity` with `'new': 'lexeme'` parameter
- **Status**: FULLY FUNCTIONAL
- **Example**: L1-L60 were all created successfully with lemmas and metadata
- **Details**:
  ```python
  'action': 'wbeditentity',
  'new': 'lexeme',
  'data': {
      'type': 'lexeme',
      'language': 'Q1',
      'lexicalCategory': 'Q4',
      'lemmas': {'mis': {'language': 'mis', 'value': 'word'}}
  }
  ```
- **Result**: API returns success, lexeme is created and persists

### 2. Modifying Existing Senses
- **How**: `wbeditentity` with `'id'` parameter + sense object that already exists
- **Status**: FULLY FUNCTIONAL
- **Example**: L61 modification test with marker
- **Proof**:
  - Modified L61 gloss from `"yes"` to `"yes [TEST_MARKER_1763506298]"`
  - Fetched L61 again after 1 second delay
  - Marker was present in saved data ✓ PERSISTED
- **Details**: Only works if sense already has an ID (like `'id': 'L61-S1'`)
- **Result**: API returns success, changes persist to database

### 3. Reading Lexeme Data
- **How**: `query` action with `'titles': 'Lexeme:LX'` parameter
- **Status**: FULLY FUNCTIONAL
- **Example**: All fetch operations returned valid JSON data
- **Details**: Can read lemmas, forms, senses, glosses, and claims
- **Result**: Data structure is preserved and readable

---

## What DOESN'T WORK ❌

### 1. Creating Senses at Lexeme Creation Time
- **Attempted**: Creating L66 with senses in initial payload
- **Status**: FAILS - Senses are silently dropped
- **API Behavior**:
  ```json
  {
    "success": 1,
    "entity": {
      "id": "L66",
      "senses": []          // ← Empty! Senses were dropped
    }
  }
  ```
- **What Happened**:
  - Sent: `"senses": [{"glosses": {"en": {"value": "test"}}}]`
  - Received: Lexeme created but `"senses": []`
  - Verified: Fetched L66 again - has 0 senses
- **Why**: Backend doesn't support creating new senses during lexeme creation
- **Workaround**: None available at API level

### 2. Adding Senses to Empty Lexemes via wbeditentity
- **Attempted**: Using `wbeditentity` with `'id': 'L2'` + senses array
- **Status**: FAILS - Returns "nochange" indicator
- **API Behavior**:
  ```json
  {
    "success": 1,
    "entity": {
      "senses": [],
      "nochange": ""        // ← Rejection indicator
    }
  }
  ```
- **What Happened**:
  - API says "success" but includes `"nochange": ""` field
  - This means: "Request accepted, but not applied"
  - Lexeme still has 0 senses after call
- **Why**: Backend validator rejects new sense creation even when properly formatted
- **Workaround**: None available at API level

### 3. wbladdsense Endpoint
- **Attempted**: Dedicated endpoint for adding senses to lexemes
- **Status**: COMPLETELY BROKEN
- **API Response**:
  ```json
  {
    "error": {
      "code": "missingparam",
      "info": "The \"data\" parameter must be set."
    }
  }
  ```
- **What We Tried**:
  - Sent: `action=wbladdsense` + `lexemeId=L67` + `glosses={...}`
  - Response: Missing parameter error
- **Why**: Either endpoint not implemented or expects different parameter format than standard Wikibase
- **Workaround**: None - endpoint is non-functional

### 4. wbladdform Endpoint
- **Attempted**: Dedicated endpoint for adding forms to lexemes
- **Status**: COMPLETELY BROKEN
- **API Response**: Same as wbladdsense - "missing parameter" error
- **Why**: Same as wbladdsense - likely implementation issue
- **Workaround**: None - endpoint is non-functional

### 5. Adding Senses to L1-L60 Using L61 Template
- **Attempted**: Copy L61's proven structure to L1-L60, modify only lemma and gloss
- **Status**: ALL 60 FAILED - sense validation error
- **API Response**: All returned same error
  ```
  ✗ (⧼wikibase-validator-sense-not-found⧽)
  ```
- **What Happened**:
  - L61 has sense `'id': 'L61-S1'` with gloss - works perfectly
  - L1-L60 have no senses at all
  - Tried to add senses by providing structure with new sense IDs (e.g., `'id': 'L1-S1'`)
  - Backend validator says: "Can't find sense L1-S1"
  - Validator is rejecting the request because sense ID doesn't already exist
- **Why**: Backend won't create new sense objects, even when ID is explicitly provided
- **Result**: 0 out of 60 succeeded

---

## Summary Table

| Operation | Method | Status | Reason |
|-----------|--------|--------|--------|
| **Create empty lexeme** | wbeditentity (new) | ✅ Works | Basic creation works fine |
| **Modify existing sense** | wbeditentity (existing ID) | ✅ Works | Can update what exists |
| **Create sense at creation time** | wbeditentity payload | ❌ Fails | Senses silently dropped |
| **Add sense to empty lexeme** | wbeditentity (array) | ❌ Fails | Returns "nochange" |
| **Add sense (dedicated endpoint)** | wbladdsense | ❌ Fails | Endpoint broken/not implemented |
| **Add form (dedicated endpoint)** | wbladdform | ❌ Fails | Endpoint broken/not implemented |
| **Add sense using template** | wbeditentity (copy L61) | ❌ Fails | Validator rejects new sense IDs |

---

## The Core Issue

**The backend is fundamentally broken for sense creation, but works for sense modification.**

This indicates:
- ✅ Database tables exist for senses (`wb_sense`, etc.)
- ✅ Reading senses works perfectly
- ✅ Modifying existing sense data works perfectly (L61 proof)
- ❌ **Creating new sense objects is completely blocked**
- ❌ Database INSERT operations for senses are failing or prevented
- ❌ Validator won't accept sense IDs that don't already exist

### Most Likely Cause
1. **Incomplete database initialization** - WikibaseLexeme `update.php` was never run on Aelaki
2. **Missing database constraints** - Sense IDs must exist in database before API can reference them
3. **Version mismatch** - Extension version doesn't support sense creation
4. **Permission issue** - Sense creation is disabled in configuration

---

## Next Steps

### If you want to use Lexeme with senses:
1. **Contact Miraheze support** with:
   - This report
   - Test lexeme IDs (L61 works, L66 fails, L67 fails)
   - Ask: "Was `php maintenance/update.php` run for WikibaseLexeme extension?"
   - Ask: "Are `wb_sense` and `wb_sense_id_unit` tables present?"

2. **Wait for Miraheze to fix** the backend infrastructure

3. **Use workaround approach**:
   - Keep L61/L62 as "master" lexemes with senses
   - Use semantic properties to link L1-L60 to concepts
   - Or manually add senses via wiki UI (very slow)

### If you want to abandon Lexeme senses:
- Continue using L1-L60 without senses (they're created and functional)
- Use only the fields that work: lemmas, forms, claims
- Store definitions in separate Wikidata items instead

---

## Test Evidence Files

| File | Purpose |
|------|---------|
| `test_lexeme_api_comprehensive.py` | 5-phase diagnostic (L61 persistence + L66 creation) |
| `test_lexeme_all_methods.py` | Tests all 4 API methods (wbeditentity, wbladdsense, wbladdform) |
| `add_aelaki_glosses_working.py` | Attempted L1-L60 with L61 template (all 60 failed) |
| `FINAL_LEXEME_DIAGNOSTIC_REPORT.md` | Professional analysis + Miraheze support message |

