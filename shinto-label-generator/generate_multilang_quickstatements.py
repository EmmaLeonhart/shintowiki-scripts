"""
Generate labels in multiple languages for Shinto shrines and Buddhist temples.
Source: Indonesian (id) labels on Wikidata OR local proposed labels.

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

# Windows UTF-8 console fix
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
# Name extraction
# ----------------------------

def extract_name(id_label):
    """Extract shrine/temple name from Indonesian label, preserving original casing.
    Returns (name, is_grand, p_type) or None.
    p_type is 'shrine' or 'temple'."""
    cleaned = re.sub(r'\([^)]*\)', '', id_label)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = cleaned.strip()
    
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
        if lang == "fa": return "معبد بزرگ" if is_grand else "معبد"
        if lang == "ar": return "معبد … الكبير" if is_grand else "معبد"
        if lang == "arz": return "معبد … الكبير" if is_grand else "معبد"
        if lang == "hi": return "महा मंदिर" if is_grand else "मंदिर"
        return ""

    if lang == "tr":
        return f"{name} {get_affix()}"
    if lang == "de":
        if p_type == "temple": return f"{name}-{get_affix()}" # e.g. Senso-Tempel
        return f"{name} {get_affix()}"
    if lang == "nl":
        if p_type == "temple": return f"{name}-{get_affix()}"
        return f"{name}{get_affix()}" # Ise-shrijn
    if lang in ["es", "it", "fr", "pt"]:
        return f"{get_affix()} {name}"
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
    if lang == "hi":
        hi_name = hindify(name)
        return f"{hi_name} {get_affix()}"
    return None

# ----------------------------
# SPARQL
# ----------------------------

ALL_LANGS = ["tr", "de", "nl", "es", "it", "eu", "lt", "ru", "uk", "fa", "ar", "arz", "hi", "fr", "pt"]


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


def run_sparql(query, label):
    print(f"  Querying Wikidata: {label}...")
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers={"User-Agent": "Japanese-Tokiponizer/1.0 (multilang label pipeline)"},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    results = data["results"]["bindings"]
    print(f"  Got {len(results)} results.")
    return results

def load_proposals():
    """Load local Indonesian label proposals."""
    path = "proposed_indonesian_labels.csv"
    if not os.path.exists(path):
        return []
    
    proposals = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            proposals.append(row)
    print(f"  Loaded {len(proposals)} local proposals.")
    return proposals

# ----------------------------
# Main
# ----------------------------

def main():
    outdir = "quickstatements"
    os.makedirs(outdir, exist_ok=True)
    
    # Load proposals once
    local_proposals = load_proposals()

    for lang in ALL_LANGS:
        print(f"\n=== {lang.upper()} ===")
        
        rows = []
        seen = set()
        
        # 1. From Wikidata
        results = run_sparql(make_sparql(lang), f"shrines missing {lang} label")
        skipped = 0
        
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
            else:
                skipped += 1
                
        print(f"  From Wikidata: {len(rows)} rows")

        # 2. From Local Proposals
        # These are items that have JA label but NO ID label on Wikidata.
        # So they won't be in the SPARQL results (which require ID label).
        # We assume they also don't have the target language label (since they are 'Japanese-only').
        
        added_local = 0
        for p in local_proposals:
            qid = p["qid"]
            if qid in seen:
                continue
            
            # Use the proposed ID label as source
            id_label = p["proposed_label"]
            # We also have p["type"] but let's re-extract to be safe/consistent
            extracted = extract_name(id_label)
            if not extracted:
                continue
            name, is_grand, p_type = extracted
            
            label = format_label(lang, name, is_grand, p_type)
            if label:
                rows.append({"qid": qid, "label": label})
                seen.add(qid)
                added_local += 1
        
        print(f"  From Local Proposals: {added_local} rows")

        # Write QuickStatements
        filepath = os.path.join(outdir, f"{lang}.txt")
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                escaped = row["label"].replace('"', '""')
                f.write(f'{row["qid"]}\tL{lang}\t"{escaped}"\n')

        print(f"  Total: Wrote {len(rows)} to {filepath}")

        # Sample
        for row in rows[:5]:
            print(f"    {row['qid']:12s} | {row['label']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
