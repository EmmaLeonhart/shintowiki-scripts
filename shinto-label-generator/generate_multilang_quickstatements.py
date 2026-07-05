"""
Generate labels in multiple languages for Shinto shrines and Buddhist temples.

Source (B1, 2026-06-21): the ENGLISH label is now the primary, accurate seed —
`extract_name_from_en` pulls the name out of "<Name> Shrine" / "Grand Shrine" /
"Daijinja" forms produced by Stages 0/1/2. The Indonesian (id) label + local
proposals are KEPT as a fallback for shrines/temples English doesn't yet cover
(English wins on overlap). Nothing Indonesian-derived is removed.

Languages handled:
  Simple suffix/prefix: tr, de, nl, es, it, eu
  Lithuanian (declension): lt
  Cyrillic (declension): ru, uk
  Farsi (Perso-Arabic script): fa
  Arabic (MSA): ar
  Egyptian Arabic: arz
  Hindi (Devanagari script): hi

Output: quickstatements/{lang}.txt for each language
"""

import os
import sys
import io
import re
import csv
import unicodedata
import requests
from tokiponizer import kana_to_romaji, tokenize_romaji

def _ensure_utf8_stdout():
    """Windows UTF-8 console fix. Called from main() rather than at import time so
    the module stays import-safe (a module-level sys.stdout swap breaks pytest)."""
    if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    elif hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# ----------------------------
# Cyrillic maps (Polivanov system)
# ----------------------------

CYRILLIC_BASE = {
    "a": "а", "i": "и", "u": "у", "e": "э", "o": "о",
    "ka": "ка", "ki": "ки", "ku": "ку", "ke": "кэ", "ko": "ко",
    "sa": "са", "shi": "си", "su": "су", "se": "сэ", "so": "со",
    "ta": "та", "chi": "ти", "tsu": "цу", "tu": "цу", "te": "тэ", "to": "то",
    "na": "на", "ni": "ни", "nu": "ну", "ne": "нэ", "no": "но",
    "ha": "ха", "hi": "хи", "hu": "фу", "fu": "фу", "he": "хэ", "ho": "хо",
    "ma": "ма", "mi": "ми", "mu": "му", "me": "мэ", "mo": "мо",
    "ya": "я", "yu": "ю", "yo": "ё",
    "ra": "ра", "ri": "ри", "ru": "ру", "re": "рэ", "ro": "ро",
    "wa": "ва", "wi": "ви", "we": "вэ", "wo": "о",
    "n": "н",
    "ga": "га", "gi": "ги", "gu": "гу", "ge": "гэ", "go": "го",
    "za": "дза", "ji": "дзи", "zu": "дзу", "ze": "дзэ", "zo": "дзо",
    "da": "да", "di": "дзи", "du": "дзу", "de": "дэ", "do": "до",
    "ba": "ба", "bi": "би", "bu": "бу", "be": "бэ", "bo": "бо",
    "pa": "па", "pi": "пи", "pu": "пу", "pe": "пэ", "po": "по",
}

CYRILLIC_YOON = {
    "kya": "кя", "kyu": "кю", "kyo": "кё",
    "sha": "ся", "shu": "сю", "sho": "сё",
    "cha": "тя", "chu": "тю", "cho": "тё",
    "nya": "ня", "nyu": "ню", "nyo": "нё",
    "hya": "хя", "hyu": "хю", "hyo": "хё",
    "mya": "мя", "myu": "мю", "myo": "мё",
    "rya": "ря", "ryu": "рю", "ryo": "рё",
    "gya": "гя", "gyu": "гю", "gyo": "гё",
    "ja": "дзя", "ju": "дзю", "jo": "дзё",
    "bya": "бя", "byu": "бю", "byo": "бё",
    "pya": "пя", "pyu": "пю", "pyo": "пё",
    "dya": "дя", "dyu": "дю", "dyo": "дё",
}

# ----------------------------
# Farsi maps (Perso-Arabic script)
# ----------------------------

# Initial vowels need an alef carrier in Farsi
FARSI_INITIAL = {"a": "ا", "i": "ای", "u": "او", "e": "ای", "o": "او"}

FARSI_BASE = {
    "a": "ا", "i": "ی", "u": "و", "e": "ه", "o": "و",
    "ka": "کا", "ki": "کی", "ku": "کو", "ke": "که", "ko": "کو",
    "sa": "سا", "shi": "شی", "su": "سو", "se": "سه", "so": "سو",
    "ta": "تا", "chi": "چی", "tsu": "تسو", "tu": "تسو", "te": "ته", "to": "تو",
    "na": "نا", "ni": "نی", "nu": "نو", "ne": "نه", "no": "نو",
    "ha": "ها", "hi": "هی", "hu": "هو", "fu": "فو", "he": "هه", "ho": "هو",
    "ma": "ما", "mi": "می", "mu": "مو", "me": "مه", "mo": "مو",
    "ya": "یا", "yu": "یو", "yo": "یو",
    "ra": "را", "ri": "ری", "ru": "رو", "re": "ره", "ro": "رو",
    "wa": "وا", "wi": "وی", "we": "وه", "wo": "و",
    "n": "ن",
    "ga": "گا", "gi": "گی", "gu": "گو", "ge": "گه", "go": "گو",
    "za": "زا", "ji": "جی", "zu": "زو", "ze": "زه", "zo": "زو",
    "da": "دا", "di": "دی", "du": "دو", "de": "ده", "do": "دو",
    "ba": "با", "bi": "بی", "bu": "بو", "be": "به", "bo": "بو",
    "pa": "پا", "pi": "پی", "pu": "پو", "pe": "په", "po": "پو",
}

FARSI_YOON = {
    "kya": "کیا", "kyu": "کیو", "kyo": "کیو",
    "sha": "شا",  "shu": "شو",  "sho": "شو",
    "cha": "چا",  "chu": "چو",  "cho": "چو",
    "nya": "نیا", "nyu": "نیو", "nyo": "نیو",
    "hya": "هیا", "hyu": "هیو", "hyo": "هیو",
    "mya": "میا", "myu": "میو", "myo": "میو",
    "rya": "ریا", "ryu": "ریو", "ryo": "ریو",
    "gya": "گیا", "gyu": "گیو", "gyo": "گیو",
    "ja":  "جا",  "ju":  "جو",  "jo":  "جو",
    "bya": "بیا", "byu": "بیو", "byo": "بیو",
    "pya": "پیا", "pyu": "پیو", "pyo": "پیو",
    "dya": "دیا", "dyu": "دیو", "dyo": "دیو",
}


# ----------------------------
# Arabic maps (MSA transliteration)
# ----------------------------

# Initial vowels need a hamza carrier in Arabic
ARABIC_INITIAL = {"a": "أ", "i": "إي", "u": "أو", "e": "إي", "o": "أو"}

ARABIC_BASE = {
    "a": "ا", "i": "ي", "u": "و", "e": "ي", "o": "و",
    "ka": "كا", "ki": "كي", "ku": "كو", "ke": "كي", "ko": "كو",
    "sa": "سا", "shi": "شي", "su": "سو", "se": "سي", "so": "سو",
    "ta": "تا", "chi": "تشي", "tsu": "تسو", "tu": "تسو", "te": "تي", "to": "تو",
    "na": "نا", "ni": "ني", "nu": "نو", "ne": "ني", "no": "نو",
    "ha": "ها", "hi": "هي", "hu": "هو", "fu": "فو", "he": "هي", "ho": "هو",
    "ma": "ما", "mi": "مي", "mu": "مو", "me": "مي", "mo": "مو",
    "ya": "يا", "yu": "يو", "yo": "يو",
    "ra": "را", "ri": "ري", "ru": "رو", "re": "ري", "ro": "رو",
    "wa": "وا", "wi": "وي", "we": "وي", "wo": "و",
    "n": "ن",
    "ga": "غا", "gi": "غي", "gu": "غو", "ge": "غي", "go": "غو",
    "za": "زا", "ji": "جي", "zu": "زو", "ze": "زي", "zo": "زو",
    "da": "دا", "di": "دي", "du": "دو", "de": "دي", "do": "دو",
    "ba": "با", "bi": "بي", "bu": "بو", "be": "بي", "bo": "بو",
    "pa": "با", "pi": "بي", "pu": "بو", "pe": "بي", "po": "بو",
}

ARABIC_YOON = {
    "kya": "كيا", "kyu": "كيو", "kyo": "كيو",
    "sha": "شا",  "shu": "شو",  "sho": "شو",
    "cha": "تشا", "chu": "تشو", "cho": "تشو",
    "nya": "نيا", "nyu": "نيو", "nyo": "نيو",
    "hya": "هيا", "hyu": "هيو", "hyo": "هيو",
    "mya": "ميا", "myu": "ميو", "myo": "ميو",
    "rya": "ريا", "ryu": "ريو", "ryo": "ريو",
    "gya": "غيا", "gyu": "غيو", "gyo": "غيو",
    "ja":  "جا",  "ju":  "جو",  "jo":  "جو",
    "bya": "بيا", "byu": "بيو", "byo": "بيو",
    "pya": "بيا", "pyu": "بيو", "pyo": "بيو",
    "dya": "ديا", "dyu": "ديو", "dyo": "ديو",
}


# ----------------------------
# Hindi maps (Devanagari script)
# ----------------------------

HINDI_INITIAL = {"a": "अ", "i": "इ", "u": "उ", "e": "ए", "o": "ओ"}

HINDI_BASE = {
    "a": "अ", "i": "इ", "u": "उ", "e": "ए", "o": "ओ",
    "ka": "क", "ki": "कि", "ku": "कु", "ke": "के", "ko": "को",
    "sa": "स", "shi": "शि", "su": "सु", "se": "से", "so": "सो",
    "ta": "त", "chi": "चि", "tsu": "त्सु", "tu": "तु", "te": "ते", "to": "तो",
    "na": "न", "ni": "नि", "nu": "नु", "ne": "ने", "no": "नो",
    "ha": "ह", "hi": "हि", "hu": "हु", "fu": "फ़ु", "he": "हे", "ho": "हो",
    "ma": "म", "mi": "मि", "mu": "मु", "me": "मे", "mo": "मो",
    "ya": "य", "yu": "यु", "yo": "यो",
    "ra": "र", "ri": "रि", "ru": "रु", "re": "रे", "ro": "रो",
    "wa": "व", "wi": "वि", "we": "वे", "wo": "वो",
    "n": "न",
    "ga": "ग", "gi": "गि", "gu": "गु", "ge": "गे", "go": "गो",
    "za": "ज़", "ji": "जि", "zu": "ज़ु", "ze": "ज़े", "zo": "ज़ो",
    "da": "द", "di": "दि", "du": "दु", "de": "दे", "do": "दो",
    "ba": "ब", "bi": "बि", "bu": "बु", "be": "बे", "bo": "बो",
    "pa": "प", "pi": "पि", "pu": "पु", "pe": "पे", "po": "पो",
}

HINDI_YOON = {
    "kya": "क्य", "kyu": "क्यु", "kyo": "क्यो",
    "sha": "श",   "shu": "शु",   "sho": "शो",
    "cha": "च",   "chu": "चु",   "cho": "चो",
    "nya": "न्य", "nyu": "न्यु", "nyo": "न्यो",
    "hya": "ह्य", "hyu": "ह्यु", "hyo": "ह्यो",
    "mya": "म्य", "myu": "म्यु", "myo": "म्यो",
    "rya": "र्य", "ryu": "र्यु", "ryo": "र्यो",
    "gya": "ग्य", "gyu": "ग्यु", "gyo": "ग्यो",
    "ja":  "ज",   "ju":  "जु",   "jo":  "जो",
    "bya": "ब्य", "byu": "ब्यु", "byo": "ब्यो",
    "pya": "प्य", "pyu": "प्यु", "pyo": "प्यो",
    "dya": "द्य", "dyu": "द्यु", "dyo": "द्यो",
}


def _hindify_word(word):
    """Transliterate a single romanized Japanese word to Hindi (Devanagari) script."""
    w = unicodedata.normalize("NFKC", word).lower()
    w = w.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    w = re.sub(r"[^\w]", "", w)
    w = kana_to_romaji(w)
    tokens = tokenize_romaji(w)
    parts = []
    for idx, t in enumerate(tokens):
        if t in HINDI_YOON:
            parts.append(HINDI_YOON[t])
        elif t in HINDI_BASE:
            if idx == 0 and t in HINDI_INITIAL:
                parts.append(HINDI_INITIAL[t])
            else:
                parts.append(HINDI_BASE[t])
    return "".join(parts)


def hindify(name):
    """Convert a romanized Japanese name to Hindi (Devanagari) script. Handles multi-word names."""
    words = name.split()
    hindi_words = [_hindify_word(w) for w in words if w]
    return " ".join(w for w in hindi_words if w)


# ----------------------------
# Bengali (B4b): transliterate the Devanagari (hindify) output to Bengali script.
# Devanagari and Bengali share a parallel Unicode layout (ISCII legacy), so each
# emitted akshara maps to its Bengali counterpart at offset +0x80 — verified
# valid for every character hindify can emit EXCEPT व (no Bengali 'va' → ব).
# Built dynamically from the Hindi maps so it stays in sync.
# ----------------------------

DEVANAGARI_TO_BENGALI = {}
for _d in (HINDI_BASE, HINDI_YOON, HINDI_INITIAL):
    for _v in _d.values():
        for _ch in _v:
            DEVANAGARI_TO_BENGALI.setdefault(_ch, chr(ord(_ch) + 0x80))
DEVANAGARI_TO_BENGALI["व"] = "ব"  # Bengali has no 'va' letter; use ba

# Bengali shrine words (mirrors the Hindi मंदिर / महा मंदिर convention),
# built from codepoints to avoid mis-typed script: মন্দির, মহা মন্দির.
_BN_MANDIR = "".join(chr(c) for c in [0x09AE, 0x09A8, 0x09CD, 0x09A6, 0x09BF, 0x09B0])
_BN_MAHA = "".join(chr(c) for c in [0x09AE, 0x09B9, 0x09BE])


_DEVA_CONSONANTS = set(range(0x0915, 0x093A))   # क … ह
_DEVA_MATRAS = set(range(0x093E, 0x094D))       # ा … ौ (vowel signs)
_DEVA_VIRAMA = 0x094D
_DEVA_NUKTA = 0x093C
_BN_AA_MATRA = "া"                          # া


def bengalify(name):
    """Transliterate a romanized Japanese name to Bengali script via the
    Devanagari (hindify) output. Bengali's inherent vowel is 'ô', not 'a', so a
    bare consonant carrying Devanagari's inherent 'a' must get an explicit
    aa-matra (া) to read correctly (কাসুগা "Kasuga", not কসুগ "Kôsugô").
    Returns None if hindify produced nothing or any char is unmapped."""
    deva = hindify(name)
    if not deva:
        return None
    out = []
    i, n = 0, len(deva)
    while i < n:
        ch = deva[i]
        if ch == " ":
            out.append(" ")
            i += 1
            continue
        if ch not in DEVANAGARI_TO_BENGALI:
            return None
        out.append(DEVANAGARI_TO_BENGALI[ch])
        cp = ord(ch)
        i += 1
        if cp in _DEVA_CONSONANTS:
            # consume an optional nukta (stays before any matra)
            if i < n and ord(deva[i]) == _DEVA_NUKTA:
                out.append(DEVANAGARI_TO_BENGALI[deva[i]])
                i += 1
            # inherent 'a' unless an explicit matra or virama follows
            nxt = ord(deva[i]) if i < n else None
            if nxt not in _DEVA_MATRAS and nxt != _DEVA_VIRAMA:
                out.append(_BN_AA_MATRA)
    return "".join(out)


# Marathi (deep tail): same Devanagari script as Hindi, but the existing labels
# render names with explicit aa-matras (कामिकावा, not कमिकव) + the तीर्थ suffix.
# So: hindify, then insert a Devanagari aa-matra after each inherent-a consonant
# (same logic as bengalify, staying in Devanagari). Known gap: hindify drops
# gemination (Hokkaido→होकाइदो vs होक्काइदो) — inherited from Hindi, documented.
_DEVA_AA_MATRA = "ा"  # U+093E
_MR_TIRTH = "".join(chr(c) for c in [0x0924, 0x0940, 0x0930, 0x094D, 0x0925])  # तीर्थ


# ----------------------------
# Czech / Slovene Latin transcription (rung-2 tier, 2026-07-04). Conventions
# from existing Wikidata labels: cs Jasukuni, Meidži, Curugaoka Hačiman,
# Acuta, Kašihara džingú, Enrjakudži, Bjódóin (š/č/dž/c, ó/ú for long
# vowels, hyphens joined); sl the same consonants but NO vowel length and
# hyphens KEPT (Jakuši-dži, Todai-dži, Hačimangu, Kijomizu). Single-pass
# alternation so ya→ja can't be re-hit by ja→dža.
# ----------------------------

_SLAVIC_MAP = {
    "shi": "ši", "sha": "ša", "shu": "šu", "sho": "šo",
    "chi": "či", "cha": "ča", "chu": "ču", "cho": "čo",
    "tsu": "cu",
    "ji": "dži", "ja": "dža", "ju": "džu", "jo": "džo",
    "ya": "ja", "yu": "ju", "yo": "jo",
    "ts": "c", "sh": "š", "ch": "č",
    "y": "j", "j": "dž", "w": "v",
}
_SLAVIC_RE = re.compile("|".join(sorted(_SLAVIC_MAP, key=len, reverse=True)))
_CS_LONG = {"ā": "á", "ī": "í", "ū": "ú", "ē": "é", "ō": "ó"}


def _slavic_word(word, long_vowels):
    w = unicodedata.normalize("NFC", word)
    cap = w[:1].isupper()
    w = _SLAVIC_RE.sub(lambda m: _SLAVIC_MAP[m.group(0)], w.lower())
    if long_vowels:
        for macron, acute in _CS_LONG.items():
            w = w.replace(macron, acute)
    else:
        for macron, plain in zip("āīūēō", "aiueo"):
            w = w.replace(macron, plain)
    return (w[:1].upper() + w[1:]) if cap else w


def czechify(name):
    """Romanized Japanese → Czech transcription; hyphen segments joined
    (Enryaku-ji → Enrjakudži)."""
    words = [_slavic_word(w, long_vowels=True).replace("-", "")
             for w in name.split()]
    return " ".join(w for w in words if w)


def slovenify(name):
    """Romanized Japanese → Slovene transcription; hyphens kept, vowel
    length dropped (Tōdai-ji → Todai-dži)."""
    words = [_slavic_word(w, long_vowels=False) for w in name.split()]
    return " ".join(w for w in words if w)


# ----------------------------
# Assamese (temple-only tier, 2026-07-04): Bengali-script sibling. Same
# bengalify output with the Assamese ra (ৰ U+09F0) substituted for the
# Bengali ra (র U+09B0); the temple word মন্দিৰ mirrors bn মন্দির with the
# same substitution. Per Emma's standardization rule, temple-only languages
# use their temple word for BOTH shrines and temples.
# ----------------------------

_AS_RA = chr(0x09F0)
_AS_MANDIR = _BN_MANDIR.replace(chr(0x09B0), _AS_RA)


def assamify(name):
    """Romanized Japanese name → Assamese script (bengalify output with the
    Assamese ra). None when bengalify can't map the name."""
    bn = bengalify(name)
    if not bn:
        return None
    return bn.replace(chr(0x09B0), _AS_RA)


def marathify(name):
    """Romanized Japanese name → Marathi Devanagari with explicit aa-matras."""
    deva = hindify(name)
    if not deva:
        return ""
    out = []
    i, n = 0, len(deva)
    while i < n:
        ch = deva[i]
        if ch == " ":
            out.append(" ")
            i += 1
            continue
        out.append(ch)
        cp = ord(ch)
        i += 1
        if cp in _DEVA_CONSONANTS:
            if i < n and ord(deva[i]) == _DEVA_NUKTA:
                out.append(deva[i])
                i += 1
            nxt = ord(deva[i]) if i < n else None
            if nxt not in _DEVA_MATRAS and nxt != _DEVA_VIRAMA:
                out.append(_DEVA_AA_MATRA)
    return "".join(out)


def _arabify_word(word):
    """Transliterate a single romanized Japanese word to Arabic script."""
    w = unicodedata.normalize("NFKC", word).lower()
    w = w.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    w = re.sub(r"[^\w]", "", w)
    w = kana_to_romaji(w)
    tokens = tokenize_romaji(w)
    parts = []
    for idx, t in enumerate(tokens):
        if t in ARABIC_YOON:
            parts.append(ARABIC_YOON[t])
        elif t in ARABIC_BASE:
            if idx == 0 and t in ARABIC_INITIAL:
                parts.append(ARABIC_INITIAL[t])
            else:
                parts.append(ARABIC_BASE[t])
    return "".join(parts)


def arabify(name):
    """Convert a romanized Japanese name to Arabic script. Handles multi-word names."""
    words = name.split()
    arabic_words = [_arabify_word(w) for w in words if w]
    return " ".join(w for w in arabic_words if w)


def _farsify_word(word):
    """Transliterate a single romanized Japanese word to Farsi script."""
    w = unicodedata.normalize("NFKC", word).lower()
    w = w.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    w = re.sub(r"[^\w]", "", w)
    w = kana_to_romaji(w)
    tokens = tokenize_romaji(w)
    parts = []
    for idx, t in enumerate(tokens):
        if t in FARSI_YOON:
            parts.append(FARSI_YOON[t])
        elif t in FARSI_BASE:
            if idx == 0 and t in FARSI_INITIAL:
                parts.append(FARSI_INITIAL[t])
            else:
                parts.append(FARSI_BASE[t])
    return "".join(parts)


def farsify(name):
    """Convert a romanized Japanese name to Farsi script. Handles multi-word names."""
    words = name.split()
    farsi_words = [_farsify_word(w) for w in words if w]
    return " ".join(w for w in farsi_words if w)


# ----------------------------
# Greek maps (B3 tier-2). Conventions from existing Wikidata labels: u→ου,
# voiced stops as digraphs (g→γκ, d→ντ, b→μπ), h→χ, y→γι. Output is unaccented
# (Greek stress accents aren't predictable from romaji).
# ----------------------------

GREEK_BASE = {
    "a": "α", "i": "ι", "u": "ου", "e": "ε", "o": "ο",
    "ka": "κα", "ki": "κι", "ku": "κου", "ke": "κε", "ko": "κο",
    "sa": "σα", "shi": "σι", "su": "σου", "se": "σε", "so": "σο",
    "ta": "τα", "chi": "τσι", "tsu": "τσου", "tu": "τσου", "te": "τε", "to": "το",
    "na": "να", "ni": "νι", "nu": "νου", "ne": "νε", "no": "νο",
    "ha": "χα", "hi": "χι", "hu": "φου", "fu": "φου", "he": "χε", "ho": "χο",
    "ma": "μα", "mi": "μι", "mu": "μου", "me": "με", "mo": "μο",
    "ya": "για", "yu": "γιου", "yo": "γιο",
    "ra": "ρα", "ri": "ρι", "ru": "ρου", "re": "ρε", "ro": "ρο",
    "wa": "ουα", "wo": "ο", "n": "ν",
    "ga": "γκα", "gi": "γκι", "gu": "γκου", "ge": "γκε", "go": "γκο",
    "za": "ζα", "ji": "τζι", "zu": "ζου", "ze": "ζε", "zo": "ζο",
    "da": "ντα", "di": "ντι", "du": "ντου", "de": "ντε", "do": "ντο",
    "ba": "μπα", "bi": "μπι", "bu": "μπου", "be": "μπε", "bo": "μπο",
    "pa": "πα", "pi": "πι", "pu": "που", "pe": "πε", "po": "πο",
}

GREEK_YOON = {
    "kya": "κια", "kyu": "κιου", "kyo": "κιο",
    "sha": "σα", "shu": "σου", "sho": "σο",
    "cha": "τσα", "chu": "τσου", "cho": "τσο",
    "nya": "νια", "nyu": "νιου", "nyo": "νιο",
    "hya": "χια", "hyu": "χιου", "hyo": "χιο",
    "mya": "μια", "myu": "μιου", "myo": "μιο",
    "rya": "ρια", "ryu": "ριου", "ryo": "ριο",
    "gya": "γκια", "gyu": "γκιου", "gyo": "γκιο",
    "ja": "τζα", "ju": "τζου", "jo": "τζο",
    "bya": "μπια", "byu": "μπιου", "byo": "μπιο",
    "pya": "πια", "pyu": "πιου", "pyo": "πιο",
}


def _grecify_word(word):
    w = unicodedata.normalize("NFKC", word).lower()
    w = w.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    w = re.sub(r"[^\w]", "", w)
    w = kana_to_romaji(w)
    tokens = tokenize_romaji(w)
    parts = []
    for t in tokens:
        if t in GREEK_YOON:
            parts.append(GREEK_YOON[t])
        elif t in GREEK_BASE:
            parts.append(GREEK_BASE[t])
    result = "".join(parts)
    return result.capitalize() if result else ""


def grecify(name):
    """Convert a romanized Japanese name to Greek script. Handles multi-word names."""
    words = name.split()
    greek_words = [_grecify_word(w) for w in words if w]
    return " ".join(w for w in greek_words if w)


# ----------------------------
# Hebrew maps (B3 script map). Abjad with matres lectionis: a→א, u/o→ו, i→י,
# final e→ה, ya→י. Verified to reproduce existing labels (סאנו, יסוקוני,
# האקוטו, איסה). Stored in logical (reading) order — no RTL reversal.
# ----------------------------

HEBREW_INITIAL = {"a": "א", "i": "אי", "u": "או", "e": "א", "o": "או"}

HEBREW_BASE = {
    "a": "א", "i": "י", "u": "ו", "e": "ה", "o": "ו",
    "ka": "קא", "ki": "קי", "ku": "קו", "ke": "קה", "ko": "קו",
    "sa": "סא", "shi": "שי", "su": "סו", "se": "סה", "so": "סו",
    "ta": "טא", "chi": "צ׳י", "tsu": "צו", "tu": "צו", "te": "טה", "to": "טו",
    "na": "נא", "ni": "ני", "nu": "נו", "ne": "נה", "no": "נו",
    "ha": "הא", "hi": "הי", "hu": "פו", "fu": "פו", "he": "הה", "ho": "הו",
    "ma": "מא", "mi": "מי", "mu": "מו", "me": "מה", "mo": "מו",
    "ya": "י", "yu": "יו", "yo": "יו",
    "ra": "רא", "ri": "רי", "ru": "רו", "re": "רה", "ro": "רו",
    "wa": "וא", "wo": "ו", "n": "ן",
    "ga": "גא", "gi": "גי", "gu": "גו", "ge": "גה", "go": "גו",
    "za": "זא", "ji": "ג׳י", "zu": "זו", "ze": "זה", "zo": "זו",
    "da": "דא", "di": "די", "du": "דו", "de": "דה", "do": "דו",
    "ba": "בא", "bi": "בי", "bu": "בו", "be": "בה", "bo": "בו",
    "pa": "פא", "pi": "פי", "pu": "פו", "pe": "פה", "po": "פו",
}


def _hebraify_word(word):
    w = unicodedata.normalize("NFKC", word).lower()
    w = w.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    w = re.sub(r"[^\w]", "", w)
    w = kana_to_romaji(w)
    tokens = tokenize_romaji(w)
    parts = []
    for idx, t in enumerate(tokens):
        if t in HEBREW_BASE:
            if idx == 0 and t in HEBREW_INITIAL:
                parts.append(HEBREW_INITIAL[t])
            else:
                parts.append(HEBREW_BASE[t])
    return "".join(parts)


def hebraify(name):
    """Convert a romanized Japanese name to Hebrew script. Handles multi-word names."""
    words = name.split()
    heb_words = [_hebraify_word(w) for w in words if w]
    return " ".join(w for w in heb_words if w)


# ----------------------------
# Name extraction
# ----------------------------

def extract_name(id_label):
    """Extract shrine/temple name from Indonesian label, preserving original casing.
    Returns (name, is_grand, p_type) or None.
    p_type is 'shrine' or 'temple'."""
    cleaned = re.sub(r'\([^)]*\)', '', id_label)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'[ \t  ]+', ' ', cleaned).strip()   # collapse spaces incl nbsp; keep U+3000

    # Check prefixes
    # Kuil = Shrine (usually), Wihara = Temple
    prefixes = [
        ("Kuil Agung ", True, "shrine"),
        ("Kuil ", False, "shrine"),
        ("Wihara Agung ", True, "temple"),
        ("Wihara ", False, "temple"),
    ]
    
    for prefix, is_grand, p_type in prefixes:
        if cleaned.startswith(prefix):
            name = cleaned[len(prefix):].strip()
            return (name, is_grand, p_type) if name else None
    return None


# English shrine/temple-label suffixes produced by Stages 0/1/2, most specific
# first so "Grand Shrine" is matched before bare " Shrine". Each:
# (suffix, is_grand, p_type). Temple labels are "<Stem>-<suffix> Temple" (the
# hyphenated suffix stays in the name, like "<Name>-gu Shrine").
_EN_SUFFIXES = [
    (" Grand Shrine", True, "shrine"),
    (" Daijinja", True, "shrine"),
    (" Daijingu", True, "shrine"),
    (" Temple", False, "temple"),
    (" Shrine", False, "shrine"),
]


def extract_name_from_en(en_label):
    """Extract the shrine/temple name (+ is_grand + p_type) from an English label,
    preserving casing. Returns (name, is_grand, p_type) or None when the label is
    not in a recognised English shrine/temple form (then the caller falls back to
    the id path). '<Name>-gu Shrine' / '<Name>-sha Shrine' / '<Name>-ji Temple'
    keep the hyphenated part in the name."""
    cleaned = re.sub(r'\([^)]*\)', '', en_label)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'[ \t  ]+', ' ', cleaned).strip()   # collapse spaces incl nbsp; keep U+3000
    for suffix, is_grand, p_type in _EN_SUFFIXES:
        if cleaned.endswith(suffix):
            name = cleaned[: -len(suffix)].strip()
            # Degenerate: a bare qualifier with no real name.
            if not name or name == "Grand":
                return None
            return (name, is_grand, p_type)
    return None

# ----------------------------
# Cyrillicization (Polivanov system)
# ----------------------------

def _cyrillicize_word(word):
    """Cyrillicize a single romanized Japanese word."""
    w = unicodedata.normalize("NFKC", word).lower()
    w = w.replace("ā", "a").replace("ī", "i").replace("ū", "u").replace("ē", "e").replace("ō", "o")
    w = re.sub(r"[^\w]", "", w)
    w = kana_to_romaji(w)
    tokens = tokenize_romaji(w)
    parts = []
    for t in tokens:
        if t in CYRILLIC_YOON:
            parts.append(CYRILLIC_YOON[t])
        elif t in CYRILLIC_BASE:
            parts.append(CYRILLIC_BASE[t])
    result = "".join(parts)
    return result.capitalize() if result else ""


def cyrillicize(name, lang="ru"):
    """Convert a romanized Japanese name to Cyrillic. Handles multi-word names."""
    words = name.split()
    cyrillic_words = [_cyrillicize_word(w) for w in words if w]
    result = " ".join(w for w in cyrillic_words if w)
    if lang == "uk":
        result = result.replace("э", "е").replace("и", "і")
    return result

# ----------------------------
# Lithuanian romanization
# ----------------------------

def lithuanize(name):
    """Apply Lithuanian phonological adjustments to a romanized Japanese name."""
    # ch → č (case-preserving)
    result = name.replace("Ch", "Č").replace("ch", "č")
    result = result.replace("Sh", "Š").replace("sh", "š")
    result = result.replace("W", "V").replace("w", "v")
    return result

# ----------------------------
# Declension functions
# ----------------------------

def _decline_word_lithuanian(word):
    """Apply Lithuanian genitive to the last word."""
    lower = word.lower()
    for ending, repl in [("an", "ano"), ("in", "ino"), ("un", "uno"),
                         ("en", "eno"), ("on", "ono")]:
        if lower.endswith(ending):
            return word[:-len(ending)] + repl
    for ending, repl in [("a", "os"), ("i", "io"), ("u", "us"),
                         ("e", "ės"), ("o", "o")]:
        if lower.endswith(ending):
            return word[:-len(ending)] + repl
    return word


def decline_lithuanian(name):
    words = name.split()
    if not words:
        return name
    words[-1] = _decline_word_lithuanian(words[-1])
    return " ".join(words)


def _decline_word_russian(word):
    for ending, repl in [("ан", "ана"), ("ин", "ина"), ("ун", "уна"),
                         ("эн", "эна"), ("он", "она")]:
        if word.endswith(ending):
            return word[:-len(ending)] + repl
    if word.endswith("а"):
        if len(word) >= 2 and word[-2] in "гкхжчшщ":
            return word[:-1] + "и"
        return word[:-1] + "ы"
    return word


def decline_russian(name):
    words = name.split()
    if not words:
        return name
    words[-1] = _decline_word_russian(words[-1])
    return " ".join(words)


def _decline_word_ukrainian(word):
    for ending, repl in [("ан", "ана"), ("ін", "іна"), ("ун", "уна"),
                         ("ен", "ена"), ("он", "она")]:
        if word.endswith(ending):
            return word[:-len(ending)] + repl
    if word.endswith("а"):
        return word[:-1] + "и"
    return word


def decline_ukrainian(name):
    words = name.split()
    if not words:
        return name
    words[-1] = _decline_word_ukrainian(words[-1])
    return " ".join(words)

# ----------------------------
# Label formatters per language
# ----------------------------

def format_label(lang, name, is_grand=False, p_type="shrine"):
    """Format a shrine/temple name into a target-language label."""
    
    # Helper for generic temple/shrine words
    def get_affix():
        if lang == "tr": return "Büyük Tapınağı" if is_grand else "Tapınağı"
        if lang == "de": 
            if p_type == "temple": return "Großtempel" if is_grand else "Tempel"
            return "Großschrein" if is_grand else "Schrein"
        if lang == "nl": 
            if p_type == "temple": return "grote tempel" if is_grand else "tempel"
            return "-shrijn"
        if lang == "es":
            if p_type == "temple": return "Gran Templo" if is_grand else "Templo"
            return "Gran Santuario" if is_grand else "Santuario"
        if lang == "it":
            if p_type == "temple": return "Grande Tempio" if is_grand else "Tempio"
            return "Grande Santuario" if is_grand else "Santuario"
        if lang == "eu":
            if p_type == "temple": return "tenplu handia" if is_grand else "tenplua"
            return "santutegi handia" if is_grand else "santutegia"
        if lang == "lt":
            if p_type == "temple": return "didžioji šventykla" if is_grand else "šventykla"
            return "maldykla"
        if lang == "ru":
            if p_type == "temple": return "Великий храм" if is_grand else "Храм"
            return "Большой храм" if is_grand else "Храм"
        if lang == "uk":
            if p_type == "temple": return "Великий храм" if is_grand else "Храм"
            return "Велике святилище" if is_grand else "Святилище"
        if lang == "fr":
            if p_type == "temple": return "Grand Temple" if is_grand else "Temple"
            return "Grand Sanctuaire" if is_grand else "Sanctuaire"
        if lang == "pt":
            if p_type == "temple": return "Grande Templo" if is_grand else "Templo"
            return "Grande Santuário" if is_grand else "Santuário"
        if lang == "vi":
            # Convention from existing Wikidata labels: Đền (shrine),
            # Thần cung (grand/jingū), Chùa (Buddhist temple).
            if p_type == "temple": return "Chùa"
            return "Thần cung" if is_grand else "Đền"
        if lang == "fa": return "معبد بزرگ" if is_grand else "معبد"
        if lang == "ar": return "معبد … الكبير" if is_grand else "معبد"
        if lang == "arz": return "معبد … الكبير" if is_grand else "معبد"
        if lang == "hi": return "महा मंदिर" if is_grand else "मंदिर"
        if lang == "bn": return f"{_BN_MAHA} {_BN_MANDIR}" if is_grand else _BN_MANDIR
        # B3 tier-2 European languages (conventions from existing Wikidata labels)
        if lang == "ca":
            if p_type == "temple": return "Gran Temple" if is_grand else "Temple"
            return "Gran Santuari" if is_grand else "Santuari"
        if lang == "gl":
            if p_type == "temple": return "Gran Templo" if is_grand else "Templo"
            return "Gran Santuario" if is_grand else "Santuario"
        if lang == "sv": return "templet"          # suffixed: <Name>-templet (temple word; fine for both)
        if lang == "nb":
            if p_type == "temple": return "tempel"
            return "helligdommen"      # suffixed: <Name>-helligdommen
        if lang == "da":
            if p_type == "temple": return "tempel"
            return "helligdommen"
        if lang == "nn":
            if p_type == "temple": return "tempel"
            return "heilagdomen"   # Nynorsk parallel of nb helligdommen
        # Rung-2 tier (2026-07-04): both-kind languages that were missing
        # from format_label; distinct words from observed conventions.
        if lang == "pl":
            # observed "świątynia Tado"; świątynia serves both kinds
            return "Wielka świątynia" if is_grand else "Świątynia"
        if lang == "ro":
            if p_type == "temple": return "Marele Templu" if is_grand else "Templul"
            return "Marele Sanctuar" if is_grand else "Sanctuarul"  # observed "Marele Sanctuar de la Izumo"
        if lang == "fi":
            if p_type == "temple": return "temppeli"
            return "pyhäkkö"       # suffixed like the other Nordic langs
        if lang == "cs":
            if p_type == "temple": return "Velký chrám" if is_grand else "Chrám"
            return "Velká svatyně" if is_grand else "Svatyně"  # observed "Svatyně Jasukuni"
        if lang == "sl":
            if p_type == "temple": return "Veliki tempelj" if is_grand else "Tempelj"  # observed "tempelj Kijomizu"
            return "Veliko svetišče" if is_grand else "Svetišče"  # observed both forms
        # Temple-only tier (2026-07-04): these languages have temple-label
        # conventions on Wikidata but no shrine ones, so per Emma's rule the
        # temple word serves both kinds.
        if lang == "ceb": return "Templong"  # observed: "templong <Name>"
        if lang == "mai": return "महा मंदिर" if is_grand else "मंदिर"  # Devanagari, same word as hi
        if lang == "as": return _AS_MANDIR
        if lang == "ur": return "مندر"
        if lang == "hu":
            if p_type == "temple": return "templom"
            return "nagyszentély" if is_grand else "szentély"  # suffixed
        if lang == "la": return "Magnum Templum" if is_grand else "Templum"  # prefix
        if lang == "ast":
            if p_type == "temple": return "Gran Templu" if is_grand else "Templu"
            return "Gran Santuariu" if is_grand else "Santuariu"
        if lang in ("sh", "hr"): return "hram"      # space-suffix: <Name> hram
        if lang == "el":
            if p_type == "temple": return "Μεγάλος Ναός" if is_grand else "Ναός"
            return "Μεγάλο Ιερό" if is_grand else "Ιερό"  # prefix, grecified name
        if lang == "az": return "məbədi"            # məbəd = temple; fine for both
        if lang == "tl":
            if p_type == "temple": return "Templo"
            return "Dambanang"         # prefix
        if lang == "war":
            if p_type == "temple": return "Templo"
            return "Santuario"        # prefix
        if lang == "min":
            if p_type == "temple": return "Wihara Gadang" if is_grand else "Wihara"
            return "Kuil Gadang" if is_grand else "Kuil"  # prefix
        if lang == "eo":
            if p_type == "temple": return "Granda Templo" if is_grand else "Templo"
            return "Ĉefjaŝiro" if is_grand else "Jaŝiro"    # prefix (Esperantized yashiro)
        if lang == "jv":
            if p_type == "temple": return "Wihara"
            return "Kuil"                                   # prefix
        if lang == "he": return "מקדש"                                   # mikdash = temple; fine for both
        if lang == "ms":
            if p_type == "temple": return "Wihara Agung" if is_grand else "Wihara"
            return "Kuil Agung" if is_grand else "Kuil"      # prefix (Malay, like id)
        if lang == "br":
            if p_type == "temple": return "Templ"
            return "Santual"                                # prefix (Breton)
        if lang == "mr":
            if p_type == "temple": return "मंदिर"
            return _MR_TIRTH                                # suffix, Marathi Devanagari name
        return ""

    if lang == "tr":
        return f"{name} {get_affix()}"
    if lang == "de":
        if p_type == "temple": return f"{name}-{get_affix()}" # e.g. Senso-Tempel
        return f"{name} {get_affix()}"
    if lang == "nl":
        if p_type == "temple": return f"{name}-{get_affix()}"
        return f"{name}{get_affix()}" # Ise-shrijn
    if lang in ["es", "it", "fr", "pt", "vi", "ca", "gl", "la", "ast", "tl", "war", "min", "eo", "jv", "ms", "br", "ceb", "pl", "ro"]:
        return f"{get_affix()} {name}"
    if lang in ["sv", "nb", "da", "hu", "nn", "fi"]:
        return f"{name}-{get_affix()}"
    if lang == "cs":
        return f"{get_affix()} {czechify(name)}"
    if lang == "sl":
        return f"{get_affix()} {slovenify(name)}"
    if lang in ["sh", "hr", "az"]:
        return f"{name} {get_affix()}"
    if lang == "eu":
        return f"{name} {get_affix()}"
    if lang == "lt":
        lt_name = lithuanize(name)
        lt_name = decline_lithuanian(lt_name)
        return f"{lt_name} {get_affix()}"
    if lang == "ru":
        cy_name = cyrillicize(name, "ru")
        cy_name = decline_russian(cy_name)
        return f"{get_affix()} {cy_name}"
    if lang == "uk":
        cy_name = cyrillicize(name, "uk")
        cy_name = decline_ukrainian(cy_name)
        return f"{get_affix()} {cy_name}"
    if lang == "fa":
        fa_name = farsify(name)
        return f"{get_affix()} {fa_name}"
    if lang in ["ar", "arz"]:
        ar_name = arabify(name)
        if lang == "arz":
            ar_name = ar_name.replace("غ", "ج")
        base = f"معبد {ar_name}"
        return f"{base} الكبير" if is_grand else base
    if lang == "el":
        el_name = grecify(name)
        return f"{get_affix()} {el_name}"
    if lang == "he":
        he_name = hebraify(name)
        return f"{get_affix()} {he_name}"
    if lang == "hi":
        hi_name = hindify(name)
        return f"{hi_name} {get_affix()}"
    if lang == "mai":
        mai_name = hindify(name)
        return f"{mai_name} {get_affix()}"
    if lang == "as":
        as_name = assamify(name)
        if not as_name:
            return None
        return f"{as_name} {get_affix()}"
    if lang == "ur":
        ur_name = farsify(name)
        return f"{ur_name} {get_affix()}"
    if lang == "mr":
        mr_name = marathify(name)
        return f"{mr_name} {get_affix()}"
    if lang == "bn":
        bn_name = bengalify(name)
        if not bn_name:
            return None
        return f"{bn_name} {get_affix()}"
    return None

# ----------------------------
# SPARQL
# ----------------------------

ALL_LANGS = ["tr", "de", "nl", "es", "it", "eu", "lt", "ru", "uk", "fa", "ar", "arz", "hi", "fr", "pt", "vi", "bn",
             "ca", "gl", "sv", "nb", "da", "hu", "la", "ast", "sh", "hr", "el",
             "az", "tl", "war", "min", "eo", "jv", "he", "ms", "br", "mr",
             "nn", "ceb", "mai", "as", "ur",
             "pl", "ro", "fi", "cs", "sl"]


def make_sparql(lang_code):
    return f"""
SELECT DISTINCT ?item ?idLabel WHERE {{
  {{
    ?item wdt:P31/wdt:P279* wd:Q845945 .
  }}
  UNION
  {{
    ?item wdt:P31 wd:Q5393308 .
    ?item wdt:P17 wd:Q17 .
  }}
  ?item rdfs:label ?idLabel . FILTER(LANG(?idLabel) = "id")
  FILTER NOT EXISTS {{ ?item rdfs:label ?existing . FILTER(LANG(?existing) = "{lang_code}") }}
}}
ORDER BY ?item
"""


def make_sparql_en(lang_code):
    """B1: primary source — Shinto shrines AND Japanese Buddhist temples that have
    an English label but are missing the target language. The English label is the
    accurate seed the whole pipeline flows through (Indonesian remains a fallback
    below). Temples are Japan-only (P17=Q17), mirroring the rest of the pipeline."""
    return f"""
SELECT DISTINCT ?item ?enLabel WHERE {{
  {{
    ?item wdt:P31/wdt:P279* wd:Q845945 .
  }}
  UNION
  {{
    ?item wdt:P31 wd:Q5393308 .
    ?item wdt:P17 wd:Q17 .
  }}
  ?item rdfs:label ?enLabel . FILTER(LANG(?enLabel) = "en")
  FILTER NOT EXISTS {{ ?item rdfs:label ?existing . FILTER(LANG(?existing) = "{lang_code}") }}
}}
ORDER BY ?item
"""


def run_sparql(query, label):
    """One transient WDQS failure used to kill the WHOLE multilang loop mid-
    run (2026-07-04: the regenerate run died on lang 3/43 and continue-on-
    error hid it — only tr+de were written). Bounded retries with backoff."""
    import time as _t
    print(f"  Querying Wikidata: {label}...")
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": "Japanese-Tokiponizer/1.0 (multilang label pipeline)"},
                timeout=300,
            )
            r.raise_for_status()
            results = r.json()["results"]["bindings"]
            print(f"  Got {len(results)} results.")
            return results
        except Exception as e:
            last_err = e
            wait = 30 * (attempt + 1)
            print(f"  [RETRY] SPARQL failed ({e}); waiting {wait}s...", flush=True)
            _t.sleep(wait)
    raise last_err

# ----------------------------
# Main
# ----------------------------

# Items that match the shrine/temple SPARQL but are actually DEITIES (kami), not
# shrines. Their labels come from generate_kami_quickstatements.py as bare names,
# so the shrine pipeline must NOT emit an affixed "X Shrine" label for them.
# Emma 2026-07-04 on Q10928586 (座摩神 / Ikasuri no Kami): "just the transliteration
# everywhere" — no "Shrine" affix in any language. Add a QID here whenever a kami
# leaks into the shrine query (P31 includes both a shrine class and Q524158 kami).
EXCLUDE_QIDS = {"Q10928586"}


def main():
    _ensure_utf8_stdout()
    outdir = "quickstatements"
    os.makedirs(outdir, exist_ok=True)

    def _gen_lang(lang):
        print(f"\n=== {lang.upper()} ===")

        rows = []
        seen = set(EXCLUDE_QIDS)   # pre-seed so both source loops skip the kami above

        # 1. From English labels (primary, accurate source — B1).
        en_results = run_sparql(make_sparql_en(lang), f"shrines (en source) missing {lang} label")
        en_added = 0
        for binding in en_results:
            qid = binding["item"]["value"].split("/")[-1]
            if qid in seen:
                continue
            extracted = extract_name_from_en(binding["enLabel"]["value"])
            if not extracted:
                continue  # not a canonical en shrine label -> let the id pass try
            name, is_grand, p_type = extracted
            label = format_label(lang, name, is_grand, p_type)
            if label:
                rows.append({"qid": qid, "label": label})
                seen.add(qid)
                en_added += 1
        print(f"  From English: {en_added} rows")

        # 2. From Indonesian labels (KEPT — covers temples + shrines en doesn't reach).
        results = run_sparql(make_sparql(lang), f"shrines missing {lang} label")
        skipped = 0
        id_added = 0

        for binding in results:
            qid = binding["item"]["value"].split("/")[-1]
            if qid in seen:
                continue
            seen.add(qid)

            id_label = binding["idLabel"]["value"]
            extracted = extract_name(id_label)
            if not extracted:
                skipped += 1
                continue
            name, is_grand, p_type = extracted

            label = format_label(lang, name, is_grand, p_type)
            if label:
                rows.append({"qid": qid, "label": label})
                id_added += 1
            else:
                skipped += 1

        print(f"  From Indonesian (Wikidata): {id_added} rows")

        # Write QuickStatements
        filepath = os.path.join(outdir, f"{lang}.txt")
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                # Final whitespace hygiene at the write point (catches every language,
                # incl. affix paths like Hebrew "מקדש <name>" that can leave an edge
                # space). Collapse space/tab/nbsp/narrow-nbsp -> one ASCII space + strip.
                label = re.sub(r'[ \t  ]+', ' ', row["label"]).strip()
                escaped = label.replace('"', '""')
                f.write(f'{row["qid"]}\tL{lang}\t"{escaped}"\n')

        print(f"  Total: Wrote {len(rows)} to {filepath}")

        # Sample
        for row in rows[:5]:
            print(f"    {row['qid']:12s} | {row['label']}")

    # Per-lang fault isolation (2026-07-04): one language's failure must not
    # kill the remaining 40+ (that's how a whole regenerate run silently
    # produced only tr+de). Failures are collected and the run exits nonzero
    # so continue-on-error can't disguise a partial regeneration as success.
    failed = []
    for lang in ALL_LANGS:
        try:
            _gen_lang(lang)
        except Exception as e:
            print(f"[LANG-FAILED] {lang}: {e}", flush=True)
            failed.append(lang)

    if failed:
        sys.exit(f"{len(failed)} language(s) failed: {', '.join(failed)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
