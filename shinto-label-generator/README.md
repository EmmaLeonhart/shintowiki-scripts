# Shrine label generator

Generates multi-language labels for Shinto shrines and Buddhist temples sourced from Wikidata. Currently produces labels in **Toki Pona**, **Korean**, **Chinese**, **German**, **Spanish**, **Basque**, **Italian**, **Lithuanian**, **Dutch**, **Russian**, **Turkish**, and **Ukrainian**.

**GitHub Pages:** Browse and copy QuickStatements output at [emmaleonhart.github.io/shinto-label-generator](https://emma-leonhart.github.io/shrine-label-generator)

The Toki Pona module converts Japanese names (Hepburn romanization, Nihon-shiki, Hiragana, Katakana) into Toki Pona phonology, following a custom phonological mapping system designed to preserve Japanese etymological distinctions (Yotsugana, H→K/P positional rules, etc.)

The Russian Ukrainian and Lithuanian modules translate based on genitive cases

## Files

- `tokiponizer.py` — Core Toki Pona conversion library. Takes Japanese text in any script and produces Toki Pona-compatible name(s). Returns multiple variants when `zu` ambiguity exists.
- `koreanizer.py` — Romaji-to-Korean hangul transliterator. Preserves voiced/unvoiced consonant distinctions and merges ん as ㄴ batchim.
- `fetch_shrines_tokiponize.py` — Toki Pona SPARQL pipeline: fetches shrines with Indonesian labels, tokiponizes, outputs CSV + QuickStatements.
- `generate_korean_quickstatements.py` — Korean label pipeline: koreanize for Japan shrines, hanja readings for non-Japan shrines.
- `generate_chinese_quickstatements.py` — Chinese label pipeline: kana→man'yogana substitution + OpenCC shinjitai→simplified conversion.
- `generate_multilang_quickstatements.py` — Multi-language pipeline: tr, de, nl, es, it, eu, lt, ru, uk labels via transliteration/romanization.
- `!regenerateQuickStatements.bat` — Master batch file: runs all pipelines sequentially.
- `quickstatements/` — Output directory: `tok.txt`, `ko.txt`, `zh.txt`, `de.txt`, `es.txt`, `eu.txt`, `it.txt`, `lt.txt`, `nl.txt`, `ru.txt`, `tr.txt`, `uk.txt`
- `docs/` — GitHub Pages site: browse and copy all QuickStatements output in-browser.

## Dependencies

```bash
pip install requests hanja opencc-python-reimplemented
```

## Usage

```bash
# Run all pipelines (Toki Pona + Korean + Chinese)
!regenerateQuickStatements.bat

# Or run individually:
python fetch_shrines_tokiponize.py
python generate_korean_quickstatements.py
python generate_chinese_quickstatements.py

# Use the converters directly:
python -c "from tokiponizer import tokiponize; print(tokiponize('Hachiman'))"
python -c "from koreanizer import koreanize; print(koreanize('Hachiman'))"
python -c "from generate_chinese_quickstatements import japanese_to_chinese; print(japanese_to_chinese('八幡宮'))"
```

## Toki Pona Phonological Rules

- Voiced consonants are devoiced (g→k, z→s, d→t, b→p)
- `zu` is ambiguous (could be す or づ), so both `su` and `tu` variants are output
- Initial H → K, medial H → P
- Long vowels collapse to short
- Diphthongs follow a fixed mapping table
- `r` → `l`, `chi` → `si`, `tsu` → `tu`
- Output is always capitalized with no spaces

## Korean Label Rules

- Japan shrines: Indonesian label → strip prefix → koreanize name → append suffix
  - `Kuil` → 신사, `Kuil Agung` → 신궁, `Wihara` → 사원, `Wihara Agung` → 대사원
- Non-Japan shrines: Japanese kanji → sino-Korean reading via `hanja`
- Fallback: Japan shrines without Indonesian labels use the hanja path

## Chinese Label Rules

- Kana in Japanese labels are replaced with man'yogana-style Chinese characters (の→之, ヶ→个, etc.)
- Remaining kanji are converted from Japanese shinjitai to simplified Chinese via OpenCC
- Pure kanji labels pass through with minimal changes
