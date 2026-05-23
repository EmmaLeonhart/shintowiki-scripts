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
import re
import requests
from opencc import OpenCC

# Windows UTF-8 console fix (guard against double-wrapping from imports)
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
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": SPARQL_QUERY, "format": "json"},
        headers={"User-Agent": "Japanese-Tokiponizer/1.0 (Chinese label pipeline)"},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    results = data["results"]["bindings"]
    print(f"Got {len(results)} results from Wikidata.")
    return results


def main():
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

    # Sample output
    print("\n--- Sample output ---")
    for row in rows[:20]:
        print(f"  {row['qid']:12s} | {row['ja_label']:20s} → {row['zh_label']}")


if __name__ == "__main__":
    main()
