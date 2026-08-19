"""
Generate simplified Chinese (zh) labels for Shinto shrines and Buddhist temples.

Process:
1. Fetch shrines with Japanese labels but no Chinese labels
2. Detect kana in Japanese label → replace with phonetic Chinese characters (man'yogana-style)
3. Convert Japanese shinjitai → Traditional Chinese → Simplified Chinese via OpenCC

Output: quickstatements/zh.txt
"""

import os
import sys
import io
import json
import re
import requests
from opencc import OpenCC
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT


def _ensure_utf8_stdout():
    """Windows UTF-8 console fix. Called from main() rather than at import time so
    the module stays import-safe (a module-level sys.stdout swap breaks pytest)."""
    if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    elif hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT DISTINCT ?item ?jaLabel WHERE {
  {
    ?item wdt:P31/wdt:P279* wd:Q845945 .
  }
  UNION
  {
    ?item wdt:P31 wd:Q5393308 .
    ?item wdt:P17 wd:Q17 .
  }
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel) = "ja")
  FILTER NOT EXISTS { ?item rdfs:label ?zhLabel . FILTER(LANG(?zhLabel) = "zh") }
}
ORDER BY ?item
"""

# OpenCC converter: Traditional → Simplified Chinese
# Japanese shinjitai is close enough to traditional Chinese for t2s to work.
# (jp2t config doesn't exist in opencc-python-reimplemented)
t2s = OpenCC("t2s")

# B3a: script-variant converters from the simplified base label.
_s2t = OpenCC("s2t")    # generic traditional
_s2tw = OpenCC("s2tw")  # Taiwan traditional
_s2hk = OpenCC("s2hk")  # Hong Kong traditional


def zh_variants(simplified):
    """Map the simplified zh label to each zh script-variant language code.
    Simplified codes (zh-hans/zh-cn/zh-sg) reuse the base; traditional codes
    (zh-hant/zh-tw/zh-hk) are OpenCC-converted.

    gan + zh-mo added 2026-07-04 (temple-only tier routing): every sampled
    gan temple label on Wikidata is verbatim generic-traditional hanzi
    (大德寺/延曆寺/藥師寺/圓覺寺) → s2t, same as zh-hant; Macau follows the
    Hong Kong traditional convention (sampled 南法華寺) → s2hk. cdo was
    checked the same way and DEFERRED: zero cdo labels exist on Japanese
    shrines/temples even under a broad P31-subclass sweep, so there is no
    observed convention to follow (cdo wiki also mixes hanzi with romanized
    Bàng-uâ-cê, so guessing a script would be wrong half the time)."""
    return {
        "zh-hans": simplified,
        "zh-cn": simplified,
        "zh-sg": simplified,
        "zh-hant": _s2t.convert(simplified),
        "zh-tw": _s2tw.convert(simplified),
        "zh-hk": _s2hk.convert(simplified),
        "gan": _s2t.convert(simplified),
        "zh-mo": _s2hk.convert(simplified),
    }


# ----------------------------
# cdo (Min Dong / Bàng-uâ-cê) romanization of the SAME hanzi (Emma's directive):
# not a phonetic transliteration of the kana, but the Min Dong reading of every
# character in the zh-hant (traditional) label, space-joined. Readings come from
# cdo_readings.json (built by fetch_cdo_readings.py from Wiktionary |md=). GATED:
# emit ONLY when every CJK character is covered — never a partial/wrong label.
# ----------------------------
_CDO_READINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "cdo_readings.json")
try:
    with open(_CDO_READINGS_PATH, encoding="utf-8") as _cf:
        CDO_READINGS = json.load(_cf)
except FileNotFoundError:
    CDO_READINGS = {}

# Japanese-shinjitai man'yōgana forms OpenCC s2t leaves alone; the md= reading
# lives on the Chinese-traditional page (keeps cdoify in sync with the fetcher).
_CDO_SHINJITAI = {"恵": "惠", "曽": "曾", "気": "氣"}


def cdoify(hanzi):
    """Min Dong (Bàng-uâ-cê) romanization of a (traditional) hanzi string: each
    CJK char → its Wiktionary md= reading, single-space-joined. GATED twice —
    returns None if (a) ANY CJK character has no reading, or (b) the label is not
    PURELY CJK. A disambiguated label like ``神社（京都府）`` has no clean
    char-by-char Bàng-uâ-cê form (the parens/space would leak into the output as
    stray tokens and multi-spaces), so it is withheld rather than mangled."""
    if not hanzi:
        return None
    out = []
    for ch in hanzi:
        if "一" <= ch <= "鿿":
            reading = (CDO_READINGS.get(ch)
                       or CDO_READINGS.get(_CDO_SHINJITAI.get(ch, ch))
                       or CDO_READINGS.get(_s2t.convert(ch)))
            if not reading:
                return None
            # A stored reading may carry slash-variants or annotations; keep only
            # the first clean syllable (no whitespace/punct) so no stray tokens or
            # double-spaces leak into the label.
            syllable = re.split(r"[\s(),;~/]", reading.strip())[0].strip()
            if not syllable:
                return None
            out.append(syllable)
        else:
            # Any non-CJK char (paren, space, latin, ・, ー, digit) → not cleanly
            # romanizable → withhold the whole label.
            return None
    return " ".join(out) or None

# ----------------------------
# Kana → Chinese character mapping (man'yogana-style phonetic substitution)
# ----------------------------
# Common kana found in shrine names and their Chinese character equivalents.
# Priority: use characters that are commonly used in Chinese shrine/place contexts.

KANA_TO_CHINESE = {
    # Hiragana
    "の": "之",
    "ヶ": "个",
    "ケ": "个",
    "が": "贺",
    "ヶ丘": "个丘",

    # Common shrine-name kana
    "あ": "阿", "い": "伊", "う": "宇", "え": "江", "お": "於",
    "か": "加", "き": "纪", "く": "久", "け": "気", "こ": "古",
    "さ": "佐", "し": "志", "す": "须", "せ": "世", "そ": "曽",
    "た": "多", "ち": "知", "つ": "津", "て": "天", "と": "都",
    "な": "奈", "に": "仁", "ぬ": "奴", "ね": "祢", "の": "之",
    "は": "波", "ひ": "比", "ふ": "布", "へ": "部", "ほ": "保",
    "ま": "万", "み": "美", "む": "武", "め": "女", "も": "茂",
    "や": "也", "ゆ": "由", "よ": "与",
    "ら": "良", "り": "利", "る": "留", "れ": "礼", "ろ": "路",
    "わ": "和", "ゐ": "為", "ゑ": "恵", "を": "乎",
    "ん": "无",

    # Katakana (same mappings)
    "ア": "阿", "イ": "伊", "ウ": "宇", "エ": "江", "オ": "於",
    "カ": "加", "キ": "纪", "ク": "久", "ケ": "気", "コ": "古",
    "サ": "佐", "シ": "志", "ス": "须", "セ": "世", "ソ": "曽",
    "タ": "多", "チ": "知", "ツ": "津", "テ": "天", "ト": "都",
    "ナ": "奈", "ニ": "仁", "ヌ": "奴", "ネ": "祢", "ノ": "之",
    "ハ": "波", "ヒ": "比", "フ": "布", "ヘ": "部", "ホ": "保",
    "マ": "万", "ミ": "美", "ム": "武", "メ": "女", "モ": "茂",
    "ヤ": "也", "ユ": "由", "ヨ": "与",
    "ラ": "良", "リ": "利", "ル": "留", "レ": "礼", "ロ": "路",
    "ワ": "和", "ヰ": "為", "ヱ": "恵", "ヲ": "乎",
    "ン": "无",

    # Voiced hiragana
    "が": "贺", "ぎ": "义", "ぐ": "具", "げ": "下", "ご": "吾",
    "ざ": "座", "じ": "治", "ず": "头", "ぜ": "是", "ぞ": "曽",
    "だ": "太", "ぢ": "治", "づ": "津", "で": "出", "ど": "土",
    "ば": "马", "び": "尾", "ぶ": "武", "べ": "部", "ぼ": "母",
    "ぱ": "波", "ぴ": "比", "ぷ": "布", "ぺ": "部", "ぽ": "保",

    # Voiced katakana
    "ガ": "贺", "ギ": "义", "グ": "具", "ゲ": "下", "ゴ": "吾",
    "ザ": "座", "ジ": "治", "ズ": "头", "ゼ": "是", "ゾ": "曽",
    "ダ": "太", "ヂ": "治", "ヅ": "津", "デ": "出", "ド": "土",
    "バ": "马", "ビ": "尾", "ブ": "武", "ベ": "部", "ボ": "母",
    "パ": "波", "ピ": "比", "プ": "布", "ペ": "部", "ポ": "保",

    # v-sound (ヴ / ゔ): Japanese has no man'yōgana for /v/; the standard convention
    # approximates ヴ as ば行 (v -> b). The 2-char combos are matched before the bare
    # ヴ by japanese_to_chinese's pair-first lookahead, so ヴァ -> 马 (ba), not 武+阿.
    "ヴァ": "马", "ヴィ": "尾", "ヴゥ": "武", "ヴェ": "部", "ヴォ": "母",
    "ゔぁ": "马", "ゔぃ": "尾", "ゔぅ": "武", "ゔぇ": "部", "ゔぉ": "母",
    "ヴ": "武", "ゔ": "武",

    # Small kana
    "っ": "", "ッ": "",
    "ゃ": "也", "ゅ": "由", "ょ": "与",
    "ャ": "也", "ュ": "由", "ョ": "与",
    "ぁ": "阿", "ぃ": "伊", "ぅ": "宇", "ぇ": "江", "ぉ": "於",
    "ァ": "阿", "ィ": "伊", "ゥ": "宇", "ェ": "江", "ォ": "於",

    # Long vowel mark
    "ー": "",
}


def is_kana(char):
    """Check if character is hiragana or katakana."""
    code = ord(char)
    return (0x3040 <= code <= 0x309F or  # Hiragana
            0x30A0 <= code <= 0x30FF)    # Katakana


def japanese_to_chinese(ja_label):
    """Convert a Japanese label to simplified Chinese.

    1. Replace kana characters with phonetic Chinese characters
    2. Convert Japanese shinjitai kanji → Traditional Chinese → Simplified Chinese
    """
    if not ja_label:
        return None

    # First pass: replace kana with Chinese characters
    # Try multi-char patterns first (e.g., ヶ丘), then single chars
    result = []
    i = 0
    while i < len(ja_label):
        # Try 2-char pattern
        if i + 1 < len(ja_label):
            pair = ja_label[i:i+2]
            if pair in KANA_TO_CHINESE:
                result.append(KANA_TO_CHINESE[pair])
                i += 2
                continue

        char = ja_label[i]
        if char in KANA_TO_CHINESE:
            result.append(KANA_TO_CHINESE[char])
        elif is_kana(char):
            # Unknown kana — skip (shouldn't happen with complete mapping)
            result.append(char)
        else:
            result.append(char)
        i += 1

    intermediate = "".join(result)

    # Second pass: convert to simplified Chinese via OpenCC
    simplified = t2s.convert(intermediate)

    # If result still contains kana, it's incomplete — but still return it
    return simplified if simplified else None


def fetch_shrines():
    """Fetch shrines with Japanese labels but no Chinese labels."""
    print("Querying Wikidata for shrines without Chinese labels...")
    wd_pace(SPARQL_INTERVAL)
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": SPARQL_QUERY, "format": "json"},
        headers={"User-Agent": WIKIDATA_USER_AGENT},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    results = data["results"]["bindings"]
    print(f"Got {len(results)} results from Wikidata.")
    return results


def main():
    _ensure_utf8_stdout()
    results = fetch_shrines()

    # Deduplicate by QID
    seen = set()
    deduped = []
    for binding in results:
        qid = binding["item"]["value"].split("/")[-1]
        if qid not in seen:
            seen.add(qid)
            deduped.append(binding)
    print(f"After dedup: {len(deduped)} unique shrines without Chinese labels")

    rows = []
    skipped = 0

    for binding in deduped:
        qid = binding["item"]["value"].split("/")[-1]
        ja_label = binding.get("jaLabel", {}).get("value", "")

        zh_label = japanese_to_chinese(ja_label)

        if zh_label:
            rows.append({"qid": qid, "ja_label": ja_label, "zh_label": zh_label})
        else:
            skipped += 1

    # Write QuickStatements with comments
    outdir = "quickstatements"
    os.makedirs(outdir, exist_ok=True)
    filepath = os.path.join(outdir, "zh.txt")
    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            label = row["zh_label"].replace('"', '""')
            f.write(f'# Source: JA "{row["ja_label"]}"\n')
            f.write(f'{row["qid"]}\tLzh\t"{label}"\n')

    print(f"\nDone! Wrote {len(rows)} Chinese QuickStatements to {filepath}")
    print(f"Skipped {skipped} items (no translatable label)")

    # B3a: emit the zh script variants (simplified reuse base; traditional via
    # OpenCC). Generated for the same shrines (those missing a zh label, which
    # almost always also miss the rarer script-variant labels).
    variant_codes = ["zh-hant", "zh-tw", "zh-hk", "zh-hans", "zh-cn", "zh-sg", "gan", "zh-mo"]
    variant_lines = {code: [] for code in variant_codes}
    for row in rows:
        variants = zh_variants(row["zh_label"])
        for code, label in variants.items():
            esc = label.replace('"', '""')
            variant_lines[code].append(f'# Source: JA "{row["ja_label"]}"')
            variant_lines[code].append(f'{row["qid"]}\tL{code}\t"{esc}"')
    for code in variant_codes:
        vpath = os.path.join(outdir, f"{code}.txt")
        with open(vpath, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(variant_lines[code]))
            if variant_lines[code]:
                f.write("\n")
        print(f"  Wrote {len(rows)} {code} QuickStatements to {vpath}")

    # cdo (Min Dong): romanize the zh-hant form; GATED — only rows where every
    # char has a reading get a line. Zero cdo labels exist on shrines today, so
    # this fills a real gap; coverage grows as fetch_cdo_readings.py --corpus is
    # rerun. Skipped rows (an uncovered char) are counted, not silently dropped.
    cdo_lines = []
    cdo_skipped = 0
    for row in rows:
        cdo_label = cdoify(zh_variants(row["zh_label"])["zh-hant"])
        if cdo_label is None:
            cdo_skipped += 1
            continue
        esc = cdo_label.replace('"', '""')
        cdo_lines.append(f'# Source: JA "{row["ja_label"]}"')
        cdo_lines.append(f'{row["qid"]}\tLcdo\t"{esc}"')
    cdo_path = os.path.join(outdir, "cdo.txt")
    with open(cdo_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(cdo_lines))
        if cdo_lines:
            f.write("\n")
    print(f"  Wrote {len(cdo_lines) // 2} cdo QuickStatements to {cdo_path} "
          f"(gated: {cdo_skipped} rows skipped for an uncovered char)")

    # Sample output
    print("\n--- Sample output ---")
    for row in rows[:20]:
        print(f"  {row['qid']:12s} | {row['ja_label']:20s} → {row['zh_label']}")


if __name__ == "__main__":
    main()
