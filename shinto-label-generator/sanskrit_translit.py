"""
Sanskrit transliterator — SEPARATE from the Japanese engine (Emma: the two must
not share infrastructure; Japanese is mora-based CV, Sanskrit has consonant
clusters and a native abugida).

Input: a romanized Sanskrit name (IAST-ish or plain ASCII, e.g. "Skanda",
"Varuna", "Vaiśravaṇa", "Trailokyavijaya"). Output: the name in a target script,
LETTER-BY-LETTER so clusters survive (Skanda -> Σκάνδα, not "Κανντα").

Scripts: Devanagari (hi/mai; native Sanskrit script), Bengali (bn/as via the
Devanagari→Bengali offset), Cyrillic (ru/uk), Greek (el). Latin-script languages
keep the romanized name unchanged, so they don't go through here.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Letter tokenizer: greedy digraph/diacritic match over a normalized name.
# ---------------------------------------------------------------------------

# Normalize IAST diacritics to plain ASCII digraphs we tokenize on.
_IAST = {
    "ā": "a", "ī": "i", "ū": "u", "ṛ": "ri", "ṝ": "ri", "ḷ": "li",
    "ṃ": "m", "ṁ": "m", "ḥ": "h", "ń": "n", "ṅ": "n", "ñ": "ny",
    "ṭ": "t", "ḍ": "d", "ṇ": "n", "ś": "sh", "ṣ": "sh", "ḫ": "h",
}

# Multi-letter clusters recognised as single units (order matters: longest first).
_UNITS = ["kh", "gh", "ch", "jh", "th", "dh", "ph", "bh", "sh", "ai", "au",
          "k", "g", "c", "j", "t", "d", "n", "p", "b", "m", "y", "r", "l",
          "v", "w", "s", "h", "a", "i", "u", "e", "o"]
_UNIT_RE = re.compile("|".join(_UNITS))
_VOWELS = {"a", "i", "u", "e", "o", "ai", "au"}


def _norm(name):
    s = unicodedata.normalize("NFC", name or "").lower()
    s = "".join(_IAST.get(c, c) for c in s)
    s = re.sub(r"[^a-z ]", "", s)
    return s


def _tokens(word):
    return _UNIT_RE.findall(word)


# ---------------------------------------------------------------------------
# Devanagari (proper abugida: inherent-a, matras, virama for clusters).
# ---------------------------------------------------------------------------

_DEVA_CONS = {
    "k": "क", "kh": "ख", "g": "ग", "gh": "घ", "ch": "छ", "c": "च", "j": "ज",
    "jh": "झ", "t": "त", "th": "थ", "d": "द", "dh": "ध", "n": "न", "p": "प",
    "ph": "फ", "b": "ब", "bh": "भ", "m": "म", "y": "य", "r": "र", "l": "ल",
    "v": "व", "w": "व", "sh": "श", "s": "स", "h": "ह",
}
_DEVA_VOWEL_IND = {"a": "अ", "i": "इ", "u": "उ", "e": "ए", "o": "ओ",
                   "ai": "ऐ", "au": "औ"}
_DEVA_MATRA = {"a": "", "i": "ि", "u": "ु", "e": "े", "o": "ो",
               "ai": "ै", "au": "ौ"}
_VIRAMA = "्"


def _devanagari(word):
    toks = _tokens(word)
    out = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in _VOWELS:                      # independent vowel
            out.append(_DEVA_VOWEL_IND[t])
            i += 1
        elif t in _DEVA_CONS:
            out.append(_DEVA_CONS[t])
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if nxt in _VOWELS:                # consonant + vowel -> matra
                out.append(_DEVA_MATRA[nxt])
                i += 2
            else:                             # bare consonant -> virama (cluster/final)
                out.append(_VIRAMA)
                i += 1
        else:
            i += 1
    return "".join(out)


# Bengali: Devanagari→Bengali codepoint offset (+0x80), same as the JP pipeline's
# bengalify trick; va→ba (Bengali has no va).
def _to_bengali(deva):
    out = []
    for ch in deva:
        if ch == "व":
            out.append("ব")
        elif "ऀ" <= ch <= "ॿ":
            out.append(chr(ord(ch) + 0x80))
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# Cyrillic (scholarly-ish, letter-by-letter; aspirates as digraphs).
# ---------------------------------------------------------------------------

_CYR = {
    "kh": "кх", "gh": "гх", "ch": "чх", "jh": "джх", "th": "тх", "dh": "дх",
    "ph": "пх", "bh": "бх", "sh": "ш",
    "k": "к", "g": "г", "c": "ч", "j": "дж", "t": "т", "d": "д", "n": "н",
    "p": "п", "b": "б", "m": "м", "y": "й", "r": "р", "l": "л", "v": "в",
    "w": "в", "s": "с", "h": "х",
    "a": "а", "i": "и", "u": "у", "e": "е", "o": "о", "ai": "ай", "au": "ау",
}

_GRK = {
    "kh": "χ", "gh": "γχ", "ch": "τσχ", "jh": "τζχ", "th": "θ", "dh": "δ",
    "ph": "φ", "bh": "μπχ", "sh": "σ",
    "k": "κ", "g": "γκ", "c": "τσ", "j": "τζ", "t": "τ", "d": "ντ", "n": "ν",
    "p": "π", "b": "μπ", "m": "μ", "y": "γι", "r": "ρ", "l": "λ", "v": "β",
    "w": "ου", "s": "σ", "h": "χ",
    "a": "α", "i": "ι", "u": "ου", "e": "ε", "o": "ο", "ai": "αι", "au": "αου",
}


# Arabic (abjad; vowels as matres lectionis — over-voweled but readable).
_ARA = {
    "kh": "خ", "gh": "غ", "ch": "تش", "jh": "ج", "th": "ث", "dh": "ذ",
    "ph": "ف", "bh": "ب", "sh": "ش",
    "k": "ك", "g": "غ", "c": "تش", "j": "ج", "t": "ت", "d": "د", "n": "ن",
    "p": "ب", "b": "ب", "m": "م", "y": "ي", "r": "ر", "l": "ل", "v": "و",
    "w": "و", "s": "س", "h": "ه",
    "a": "ا", "i": "ي", "u": "و", "e": "ي", "o": "و", "ai": "اي", "au": "او",
}
# Perso-Arabic (fa/ur): Arabic + Persian letters for p/g/ch.
_PER = {**_ARA, "p": "پ", "g": "گ", "ch": "چ", "c": "چ"}

# Hebrew (abjad).
_HEB = {
    "kh": "ח", "gh": "ג", "ch": "צ׳", "jh": "ג׳", "th": "ת", "dh": "ד",
    "ph": "פ", "bh": "ב", "sh": "ש",
    "k": "ק", "g": "ג", "c": "צ׳", "j": "ג׳", "t": "ט", "d": "ד", "n": "נ",
    "p": "פ", "b": "ב", "m": "מ", "y": "י", "r": "ר", "l": "ל", "v": "ו",
    "w": "ו", "s": "ס", "h": "ה",
    "a": "א", "i": "י", "u": "ו", "e": "", "o": "ו", "ai": "אי", "au": "או",
}


def _map_word(word, table):
    return "".join(table.get(t, "") for t in _tokens(word))


# Toki Pona: (C)V(n) syllables; phonemes {p t k s m n l w j / a e i o u}. Map each
# sound to the nearest tok phoneme. `n` is a valid CODA and stays before a following
# consonant (nt/np/nk/nm are real — cf. kami tok "Enma", "konken", "menten"); only
# a cluster of two NON-`n` consonants gets an epenthetic 'a' (never drop). Deity
# names take the classifier "jan sewi" (added by the caller).
_TOK_C = {
    "kh": "k", "gh": "k", "ch": "s", "jh": "s", "th": "t", "dh": "t",
    "ph": "p", "bh": "p", "sh": "s",
    "k": "k", "g": "k", "c": "s", "j": "s", "t": "t", "d": "t", "p": "p",
    "b": "p", "m": "m", "n": "n", "y": "j", "r": "l", "l": "l", "v": "w",
    "w": "w", "s": "s", "h": "",          # toki pona has no /h/
}
_TOK_V = {"a": "a", "i": "i", "u": "u", "e": "e", "o": "o", "ai": "a", "au": "o"}
_TOK_VOWELS = set("aeiou")


def _tokipona(word):
    out = []
    for t in _tokens(word):
        if t in _TOK_V:
            out.append(_TOK_V[t])
        elif t in _TOK_C:
            c = _TOK_C[t]
            if not c:
                continue
            # two NON-'n' consonants -> epenthetic 'a'; 'n' is a legal coda, keep it
            if out and out[-1] not in _TOK_VOWELS and out[-1] != "n":
                out.append("a")
            out.append(c)
    s = "".join(out)
    if s and s[-1] not in _TOK_VOWELS and s[-1] != "n":   # illegal final consonant
        s += "a"
    return s[:1].upper() + s[1:] if s else ""


def _cap(s):
    return s[:1].upper() + s[1:] if s and s[0].isascii() else s


# ---------------------------------------------------------------------------
# Public API: sanskrit(name, lang) -> label in that language's script, or None.
# ---------------------------------------------------------------------------

_LANG = {
    "hi": ("deva", False), "mai": ("deva", False), "mr": ("deva", False),
    "bn": ("bengali", False), "as": ("bengali", False),
    "ru": ("cyr", True), "uk": ("cyr", True),
    "el": ("grk", True),
    "ar": ("ara", False), "arz": ("ara", False),
    "fa": ("per", False), "ur": ("per", False),
    "he": ("heb", False),
    "tok": ("tok", False),
}


def sanskrit(name, lang):
    spec = _LANG.get(lang)
    if not spec:
        return None                 # not a script this module handles
    kind, cap = spec
    words = [w for w in _norm(name).split() if w]
    if not words:
        return None
    rendered = []
    for w in words:
        if kind == "deva":
            r = _devanagari(w)
        elif kind == "bengali":
            r = _to_bengali(_devanagari(w))
        elif kind == "cyr":
            r = _map_word(w, _CYR)
        elif kind == "grk":
            r = _map_word(w, _GRK)
            # nasal + voiced-stop digraph: the digraph already carries the nasal,
            # so drop the redundant one (Indra: ν+ντ = "νντ" -> "ντ", cf. el "Ίντρα")
            r = r.replace("νντ", "ντ").replace("μμπ", "μπ").replace("γγκ", "γκ")
        elif kind == "ara":
            r = _map_word(w, _ARA)
        elif kind == "per":
            r = _map_word(w, _PER)
        elif kind == "heb":
            r = _map_word(w, _HEB)
        elif kind == "tok":
            r = _tokipona(w)
        else:
            r = ""
        if cap:
            r = _cap(r)
        if r:
            rendered.append(r)
    return " ".join(rendered) or None


SUPPORTED = set(_LANG)
