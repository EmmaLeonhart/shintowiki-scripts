# Japanese-Tokiponizer

## Project Context
Generates multi-language labels (Toki Pona, Korean, Chinese, German, Spanish, Basque, Italian, Lithuanian, Dutch, Russian, Turkish, Ukrainian) for Shinto shrines and Buddhist temples from Wikidata. A GitHub Pages site at `docs/index.html` lets users browse and copy all QuickStatements output in-browser.

## Key Files
- `tokiponizer.py` — Core phonological mapper (Japanese → Toki Pona)
- `koreanizer.py` — Romaji-to-Korean hangul transliterator (preserves voicing)
- `fetch_shrines_tokiponize.py` — SPARQL pipeline: Wikidata → Indonesian labels → tokiponize → CSV + QuickStatements
- `generate_korean_quickstatements.py` — Korean label pipeline (koreanize for Japan shrines, hanja for non-Japan)
- `generate_chinese_quickstatements.py` — Chinese label pipeline (kana→man'yogana + OpenCC shinjitai→simplified)
- `generate_multilang_quickstatements.py` — tr/de/nl/es/it/eu/lt/ru/uk pipeline
- `!regenerateQuickStatements.bat` — Master batch: runs all pipelines
- `quickstatements/` — Output directory: `tok.txt`, `ko.txt`, `zh.txt`, `de.txt`, `es.txt`, `eu.txt`, `it.txt`, `lt.txt`, `nl.txt`, `ru.txt`, `tr.txt`, `uk.txt`
- `docs/index.html` — GitHub Pages site for browsing/copying QuickStatements output

## Workflow Guidelines
- **Commit early and often.** Every meaningful change should be committed.
- **Use `python` not `python3`** on this Windows system.
- Data files (CSV) are tracked in git intentionally.

## Architecture
### Toki Pona
- `tokiponize(text)` returns a list of variants (multiple when `zu` ambiguity exists)
- Indonesian labels: "Kuil X" → "tomo sewi X", "Kuil Agung X" → "tomo sewi suli X"
- Bracket content stripped, spaces/dashes removed, decapitalized before conversion

### Korean
- Japan shrines: Indonesian label → strip prefix → `koreanize()` → append suffix (신사/신궁/사원/대사원)
- Non-Japan shrines: Japanese kanji → `hanja.translate()` for sino-Korean reading
- `koreanize()` preserves voiced/unvoiced (unlike tokiponizer); merges ん as ㄴ batchim

### Chinese
- Japanese label → replace kana with man'yogana-style Chinese characters → OpenCC `t2s`
- Pure kanji labels pass through with only shinjitai→simplified conversion
