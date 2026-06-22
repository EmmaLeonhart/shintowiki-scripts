# Shrine-label generator coverage (B3)

Live source of truth: `shinto-label-generator/language_registry.py` (run
`python language_registry.py` to regenerate the numbers below). This doc is the
human-readable snapshot + the plan for filling the long tail.

As of 2026-06-21: **116 languages** in `query.csv`, **44 covered**, **69 todo** (plus `bn`, a new language not yet in query.csv).
(`ja`/`en` are source/pipeline languages, `mul` is skipped — not counted as todo.)

## Covered (19)
| Method | Languages | Generator |
|---|---|---|
| Affix (name + shrine word) | tr, de, nl, es, it, eu, fr, pt | `generate_multilang_quickstatements.py` |
| Declension / Cyrillic | lt, ru, uk | `generate_multilang_quickstatements.py` |
| Script transliteration | fa, ar, arz, hi | `generate_multilang_quickstatements.py` |
| CJK man'yōgana → simplified | zh | `generate_chinese_quickstatements.py` |
| Hangul / hanja | ko | `generate_korean_quickstatements.py` |
| Tokiponize | tok | `fetch_shrines_tokiponize.py` |
| Romaji | id | `generate_indonesian_proposals.py` |

All non-CJK generators are now **English-label primary** (B1/B1b); CJK + Korean
derive from the Japanese label (a known assumption, B2 dropped).

## Todo — the long tail (94), by priority

### Tier 1 — CJK script variants of zh — **DONE (B3a)**
`zh-hant`, `zh-hk`, `zh-tw` (traditional, via OpenCC s2t/s2tw/s2hk) and
`zh-hans`, `zh-cn`, `zh-sg` (simplified, reuse the base) are now emitted by
`generate_chinese_quickstatements.py` (`zh_variants`) into their own
`quickstatements/<code>.txt` files. **Still todo:** the Sinitic topolects that
aren't a pure script conversion — `nan` 11, `yue` 8, `wuu` 6, `hak` 4, `lzh` 2,
`nan-latn-tailo` 4, `nan-latn-pehoeji` 4 (need romanization/topolect-specific
handling, not just OpenCC).

### Tier 2 — European / high-count transliteration targets
**Done (affix, conventions from existing labels):** `ca` (Santuari), `gl`
(Santuario), `sv` (-templet), `nb`/`da` (-helligdommen), `hu` (-szentély/
-nagyszentély), plus `vi` (B4) and `bn` (B4b).
**Done batch 2 (affix):** `la` (Templum/Magnum Templum), `ast` (Santuariu),
`sh`/`hr` (`<Name> hram`).
**Done (Latin tail):** `az` (`<Name> məbədi`), `tl` (Dambanang), `war`
(Santuario), `min` (Kuil/Kuil Gadang).
**Done:** `eo` (Jaŝiro/Ĉefjaŝiro), `jv` (Kuil).
**Remaining is the marginal/risky tail:** mk (needs Macedonian Cyrillic map);
unfamiliar-script maps th/my/he/ka/ta/bo (low confidence — better LLM/manual);
and ~50 single-digit-label Latin/other langs (1–3 labels, conventions unreliable
from so few examples). Coverage of all medium+ count languages is complete.
**Deferred — need name re-transliteration or the Japanese suffix, not a plain
English-romaji affix:** `cs`/`sl` re-spell the name phonetically (Jasukuni,
Meidži); `pl`/`fi` keep the Japanese word (Jinja/Taisha); `sk`/`nan` re-spell
phonetically (Icukušima, POJ); `ro` convention inconsistent.
**Script maps DONE:** `el` (Greek — grecify), `he` (Hebrew — hebraify, abjad with
matres lectionis; verified to reproduce real labels סאנו/יסוקוני/האקוטו/איסה).
**Failed the verification gate — route to the LLM, do NOT hand-build** (Emma's
2026-06-21 scope review confirmed building only what verifies):
- `th` 33 (Thai), `my` 25 (Burmese): context-dependent vowel forms / consonant
  stacking — a flat romaji→syllable map can't reproduce the existing labels
  (e.g. Thai "ma" is มะ in Itsukushima but มั in Amatsu).
- `ka` 10 (Georgian): clean alphabet, but the dominant convention KEEPS the
  Japanese suffix transliterated (ძინძია=jinja, ტაიშა=taisha) — our suffix-stripped
  English name can't reconstruct it (same class as cs/sl/pl/fi/mk).
**Remaining tail** (`ta`, `bo`, `mk`, and ~50 single-digit langs): per Emma's
scope decision, not pursued — low value / unreliable from 1–3 examples / needs
LLM or manual.

### Tier 3 — regional-language variants of already-covered languages
`en-gb` 11, `en-us` 8, `en-ca` 7, `pt-br` 2, `de-ch` 1 — these duplicate an
existing label in a regional code; low value, likely skip unless Wikidata
specifically wants them.

### Tier 4 — single-digit long tail (~50 languages, 1–9 labels each)
`be-tarask`, `lv`, `ml`, `si`, `sq`, `sr`, `tl`, `uz`, `war`, `nds`, `ty`, `ba`,
`ban`, `bg`, `mt`, `pnb`, `sco`, `ks`, `be`, `cv`, `te`, `cy`, `is`, `ky`, `lfn`,
`mn`, `kn`, `bar`, `ne`, `ha`, `pap`, `yo`, `ff`, `bo`, `et`, `awa`, `gu`, `sa`,
`oc`, `ta`, `br`, `ga`, `hy`, `bcl`, `tt`, `co`, `da`, `min`, `or`, `mr`.
For these, follow Emma's rule: inspect the existing handful of Wikidata labels
and **continue a good pattern, or invent a sane convention** rather than copying
a clearly-wrong one (Tibetan `bo` was flagged as previously bad).

## Plan
1. **B4** — add `bn` + `vi` generators (queued, concrete).
2. Extend `generate_chinese_quickstatements.py` to emit the zh script variants
   (Tier 1 — biggest win, CJK-derived).
3. Work down Tier 2 in `generate_multilang_quickstatements.py` (affix + new
   script maps), seeded from the English name.
4. Tier 4 case-by-case, convention-checked against existing labels.
