"""
Shared "bare name / term" transliteration for the non-shrine label generators
(kami, shrine ranks, provinces). These items have no "Shrine"/"Temple" affix —
the label IS the transliterated Japanese name/term — so they all reduce to:
render one Japanese name into every covered language's script.

Reuses the exact machinery the shrine pipelines already use:
  - generate_multilang_quickstatements: cyrillic / arabic / farsi / devanagari /
    bengali / marathi / assamese / greek / hebrew / czech / slovene / lithuanian
  - generate_chinese_quickstatements: japanese_to_chinese + zh_variants (from the
    JP kanji)
  - koreanizer.koreanize (phonetic) / hanja (sino-Korean reading)
  - tokiponizer.tokiponize

Latin-script languages keep the plain romaji (a proper name doesn't translate).
CJK is derived from the Japanese kanji, never the romaji.
"""

import re
import requests

from generate_multilang_quickstatements import (
    cyrillicize, arabify, farsify, hindify, bengalify, marathify, assamify,
    grecify, hebraify, czechify, slovenify, lithuanize,
)
from generate_chinese_quickstatements import japanese_to_chinese, zh_variants
from koreanizer import koreanize
from tokiponizer import tokiponize, tokenize_romaji, kana_to_romaji, katakana_to_hiragana
import hanja

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

SPARQL = "https://query-main.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": WIKIDATA_USER_AGENT}

ZH_CODES = ["zh", "zh-hant", "zh-tw", "zh-hk", "zh-hans", "zh-cn", "zh-sg", "gan", "zh-mo"]

# Per-language transliterators for non-Latin scripts. Anything not here and not
# CJK/ko/tok keeps the plain romaji (Latin-script languages).
_SPECIAL = {
    "cs": czechify, "sl": slovenify, "lt": lithuanize,
    "ru": lambda n: cyrillicize(n, "ru"), "uk": lambda n: cyrillicize(n, "uk"),
    "fa": farsify, "ur": farsify, "ar": arabify,
    "arz": lambda n: arabify(n).replace("غ", "ج"),
    "hi": hindify, "mai": hindify, "mr": marathify, "bn": bengalify, "as": assamify,
    "el": grecify, "he": hebraify,
}


def clean_name(s):
    """Strip parentheticals/brackets and surrounding whitespace from a label."""
    s = re.sub(r"\([^)]*\)", "", s or "")
    s = re.sub(r"\[[^\]]*\]", "", s)
    return s.strip()


_MACRONS = str.maketrans("āīūēōâîûêô", "aiueoaiueo")


def looks_romaji(s):
    """True if s reads as a Hepburn romaji Japanese name (so transliterating it
    produces a real reading, not phonetic garbage from English glosses like
    'Three Pioneer Kami'). Requires letters-only and near-full mora coverage."""
    w = clean_name(s).lower().translate(_MACRONS)
    w = re.sub(r"[\s\-'ʼ’]", "", w)
    if not w or not re.match(r"^[a-z]+$", w):
        return False
    consumed = len("".join(tokenize_romaji(w)))
    return consumed >= 0.9 * len(w)


def _is_kana(s):
    s = clean_name(s)
    return bool(s) and all(
        ("぀" <= c <= "ヿ") or c in "ー・ 　" for c in s)


def romaji_source(en, ja):
    """Best romaji reading for transliteration: the en label if it looks romaji,
    else a kana ja label romanised, else None (can't transliterate reliably)."""
    en = clean_name(en)
    if en and looks_romaji(en):
        return en
    jac = clean_name(ja)
    if jac and _is_kana(jac):
        return kana_to_romaji(katakana_to_hiragana(jac))
    return None


def hanja_read(ja_kanji):
    """Sino-Korean reading of a kanji string, or None if unresolved. A valid reading
    is pure Hangul — so reject the output if ANY Han is left unconverted OR if any
    Japanese kana survived (hanja only converts Han, leaving kana/Latin verbatim,
    which would otherwise emit mixed-script garbage like '국지정문화재등データベース')."""
    if not ja_kanji:
        return None
    out = hanja.translate(ja_kanji, "substitution")
    if any("一" <= c <= "鿿" or "㐀" <= c <= "䶿"        # residual Han (unconverted)
           or "ぁ" <= c <= "ゖ"                   # hiragana
           or "ァ" <= c <= "ヺ"                   # katakana
           for c in out):
        return None
    return out or None


def bare_name(lang, romaji, ja_kanji=None, ko_mode="phonetic"):
    """Render a Japanese proper name/term into `lang`. Returns the label string
    or None. zh-family codes return None here (use zh_map(ja_kanji) instead)."""
    romaji = clean_name(romaji)
    if not romaji:
        return None
    if lang in _SPECIAL:
        try:
            return _SPECIAL[lang](romaji) or None
        except Exception:
            return None
    if lang == "tok":
        try:
            v = tokiponize(romaji.lower())
            return v[0] if v else None
        except Exception:
            return None
    if lang == "ko":
        if ko_mode == "hanja":
            return hanja_read(ja_kanji)
        return koreanize(romaji) or None
    if lang in ZH_CODES:
        return None
    return romaji            # Latin-script: keep the romaji proper name


def zh_map(ja_kanji):
    """{zh-code: label} for the zh family, from the JP kanji. {} if unparseable."""
    if not ja_kanji:
        return {}
    simp = japanese_to_chinese(ja_kanji)
    if not simp:
        return {}
    return {"zh": simp, **zh_variants(simp)}


# ---------------------------------------------------------------------------
# Wikidata fetch helpers
# ---------------------------------------------------------------------------

def _get(url, params, retries=3):
    import time
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=120)
            if r.status_code == 429:
                raise SystemExit("HTTP 429 from Wikidata — bailing (repo policy).")
            r.raise_for_status()
            return r
        except SystemExit:
            raise
        except Exception as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise last


def sparql_qids(where_body):
    """Return the QIDs matching a SPARQL WHERE body binding ?item."""
    q = f"SELECT DISTINCT ?item WHERE {{ {where_body} }}"
    r = _get(SPARQL, {"query": q, "format": "json"})
    return [b["item"]["value"].rsplit("/", 1)[1] for b in r.json()["results"]["bindings"]]


def fetch_labels(qids):
    """qid -> {'en':..., 'ja':..., 'langs': set(existing label langs)}."""
    import time
    out = {}
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        data = _get(API, {"action": "wbgetentities", "ids": "|".join(batch),
                          "props": "labels", "format": "json"}).json()
        ents = data.get("entities", {})
        for q in batch:
            L = ents.get(q, {}).get("labels", {})
            out[q] = {"en": L.get("en", {}).get("value", ""),
                      "ja": L.get("ja", {}).get("value", ""),
                      "langs": set(L.keys())}
        time.sleep(0.2)
    return out


def write_qs(path, lines):
    """lines: iterable of (qid, lang, label) OR (qid, lang, label, source).

    When a 4th `source` element is present and truthy, a ``# <source>`` provenance
    comment line is written immediately before the label — noting the source label the
    transliteration derives from (todo: "annotate output lines with the source label").
    Comment lines are skipped by both the drip selector (select_label_proposals) and
    the submitter (direct_daily_edits), so they never reach Wikidata. Backward
    compatible: 3-tuples emit just the label line."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in lines:
            qid, lang, label = row[0], row[1], row[2]
            source = row[3] if len(row) > 3 else None
            if source:
                # keep the comment single-line and tab-free so it can't be misparsed
                src = str(source).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
                if src:
                    f.write(f"# {src}\n")
            esc = label.replace('"', '""')
            f.write(f'{qid}\tL{lang}\t"{esc}"\n')
