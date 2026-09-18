#!/usr/bin/env python3
"""
romance_katakana.py
===================
Italian / Spanish / Portuguese place names into katakana.

**Why only these languages, and only ja.** The religious-building corpus's
remaining refused qualifiers are localities — "Madonna del Pero", "Madonna di
Campiglio", "Nossa Senhora das Tábuas". They cannot be finished by listing
devotions, so the qualifier has to be transliterated. Romance orthography is
close to phonemic, which makes a rule-based mapping to kana honest work rather
than guessing.

⛔ **zh and ko get no equivalent and must not.** There is no rule-based route from
an Italian village name to Chinese characters or to hangul — Chinese
transliteration of foreign names is a convention (the Xinhua tables), not a
derivation, and inventing one fabricates a reading rather than sourcing it. Those
stay refused. This is the same line the rest of the pipeline holds: emit what can
be derived, refuse the rest.

**What it refuses.** Anything outside the Latin letters it knows how to read, and
anything whose orthography is not Romance — a German or Polish locality reaching
this function comes back `None` rather than being read as if it were Italian.
`Rzhavets` and `Bąkowa` are not Italian and must not be treated as such.
"""

import re
import unicodedata

# Single vowels.
_V = {"a": "ア", "i": "イ", "u": "ウ", "e": "エ", "o": "オ"}

# consonant -> the five kana for that consonant + each vowel, in a/i/u/e/o order.
_ROWS = {
    "k": "カキクケコ", "g": "ガギグゲゴ", "s": "サシスセソ", "z": "ザジズゼゾ",
    "t": "タチツテト", "d": "ダヂヅデド", "n": "ナニヌネノ", "h": "ハヒフヘホ",
    "b": "バビブベボ", "p": "パピプペポ", "m": "マミムメモ", "r": "ラリルレロ",
    "y": "ヤ-ユ-ヨ", "w": "ワ---ヲ",
}

# Digraph consonants that take the small-y forms.
_YOON = {
    "ky": ("キャ", "キ", "キュ", "キェ", "キョ"),
    "gy": ("ギャ", "ギ", "ギュ", "ギェ", "ギョ"),
    "sh": ("シャ", "シ", "シュ", "シェ", "ショ"),
    "j":  ("ジャ", "ジ", "ジュ", "ジェ", "ジョ"),
    "ch": ("チャ", "チ", "チュ", "チェ", "チョ"),
    "ny": ("ニャ", "ニ", "ニュ", "ニェ", "ニョ"),
    "hy": ("ヒャ", "ヒ", "ヒュ", "ヒェ", "ヒョ"),
    "by": ("ビャ", "ビ", "ビュ", "ビェ", "ビョ"),
    "py": ("ピャ", "ピ", "ピュ", "ピェ", "ピョ"),
    "my": ("ミャ", "ミ", "ミュ", "ミェ", "ミョ"),
    "ry": ("リャ", "リ", "リュ", "リェ", "リョ"),
    "f":  ("ファ", "フィ", "フ", "フェ", "フォ"),
    "v":  ("ヴァ", "ヴィ", "ヴ", "ヴェ", "ヴォ"),
    "ts": ("ツァ", "ツィ", "ツ", "ツェ", "ツォ"),
    "l":  ("ラ", "リ", "ル", "レ", "ロ"),
}

_ORDER = "aiueo"

# Kana for a consonant with no vowel after it. The u-column is right for most,
# but t and d take ト/ド in loanwords -- ツ/ヅ is archaic and wrong here, and it
# was producing ソンヅリオ for Sondrio.
_BARE = {"t": "ト", "d": "ド"}

# Letters we accept at all. Anything else -> refuse, rather than improvise.
_ALLOWED = set("abcdefghijlmnopqrstuvxyz")


def _fold(text):
    """Strip accents. Romance accents mark stress, which kana does not write."""
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c))


# Onsets Italian/Spanish/Portuguese actually permit. A word starting with
# anything else is not Romance and must not be read as if it were.
_ONSETS = {
    "bl", "br", "ch", "cl", "cr", "dr", "fl", "fr", "gh", "gl", "gn", "gr",
    "pl", "pr", "qu", "sb", "sc", "sd", "sf", "sg", "sl", "sm", "sn", "sp",
    "sq", "sr", "st", "sv", "tr", "ps", "pn", "lh", "nh",
}

# Letters that do not occur in native Italian/Spanish/Portuguese spelling.
_NON_ROMANCE_LETTERS = set("kwy")


def is_romance_shaped(word):
    """False when the spelling is plainly not Italian/Spanish/Portuguese.

    Cheap and deliberately strict. The corpus mixes Polish, Czech, German and
    Russian place names in among the Italian ones, and reading one of those with
    Romance rules produces a confident wrong answer -- the worst kind.
    """
    w = _fold(word).lower()
    if not w or not set(w) <= _ALLOWED:
        return False
    if _NON_ROMANCE_LETTERS & set(w):
        return False
    # Four consonants in a row does not happen in Romance. THREE does -- "Umbria"
    # is um-bri-a and was being refused by a stricter version of this check. The
    # word-initial test below is what actually catches the Slavic and German
    # names, so this only needs to stop the extreme cases.
    if re.search(r"[^aeiou]{4,}", w):
        return False
    m = re.match(r"^([^aeiou]{2,})", w)
    if m and m.group(1) not in _ONSETS:
        return False
    return True


def _romanise(word):
    """Romance spelling -> a plain consonant/vowel string kana can be built from.

    The digraphs are the whole reason this is language-specific:
      * Italian `ch`/`gh` are hard K/G before i and e — Chiesa is KI, not CHI.
      * Italian `ci`/`gi` before a vowel are CH/J with the i silent — Campiglio.
      * `gn` is NY, `gl` before i is LY.
      * Spanish `ñ` is NY, `qu` is K, `x` is KS.
      * Portuguese `lh` is LY, `nh` is NY, final `-ão` is AN.

    ⚠ Where two Romance languages disagree, **Italian wins**, because the corpus
    is Italian-dominant (Madonna del/di, San, Chiesa). Spanish `ll` = Y is
    therefore NOT applied: it was turning the Italian geminate in `Cardello`
    into カルデヨ instead of カルデッロ. Spanish names with `ll` come out with a
    geminate, which is the cost of that choice and is stated rather than hidden.
    """
    if not is_romance_shaped(word):
        return None
    w = _fold(word).lower()
    subs = [
        # 1. endings and qu-
        ("ão", "an"), ("qu", "k"), ("gue", "ge"), ("gui", "gi"),
        ("que", "ke"), ("qui", "ki"),
        # 2. hard ch/gh BEFORE the silent-h strip
        ("cch", "kk"), ("ggh", "gg"),
        ("chi", "ki"), ("che", "ke"), ("cha", "ka"), ("cho", "ko"),
        ("ghi", "gi"), ("ghe", "ge"),
        # 3. Portuguese lh/nh, also before the strip -- they are not silent h
        ("lh", "ry"), ("nh", "ny"),
        # 4. ⛔ NOW strip the remaining silent h. This MUST come before any rule
        #    that PRODUCES an h: it used to sit at the end of the list and ate
        #    the h out of the sh/ch this function had just created, so Brescia
        #    came out ブレサ instead of ブレシア.
        ("h", ""),
        # 5. sc- before c-, or "scia" loses to the "cia" rule
        ("scia", "sha"), ("scio", "sho"), ("sciu", "shu"),
        ("sci", "shi"), ("sce", "she"), ("sc", "sk"),
        # 6. soft c/g
        ("cia", "cha"), ("cio", "cho"), ("ciu", "chu"), ("ce", "che"),
        ("ci", "chi"),
        ("gia", "ja"), ("gio", "jo"), ("giu", "ju"), ("ge", "je"),
        ("gi", "ji"),
        # 7. the palatals
        ("gn", "ny"), ("gli", "ry"), ("gl", "l"),
        # 8. leftovers
        ("ss", "s"), ("z", "ts"), ("x", "ks"), ("c", "k"),
    ]
    for a, b in subs:
        w = w.replace(a, b)
    return w or None


def to_katakana(word):
    """Katakana for one Romance word, or None if it cannot be read."""
    w = _romanise(word)
    if not w:
        return None
    out = []
    i = 0
    while i < len(w):
        # geminate: double consonant -> small tsu
        if (i + 1 < len(w) and w[i] == w[i + 1] and w[i] not in _ORDER
                and w[i] not in "ny"):
            out.append("ッ")
            i += 1
            continue
        matched = False
        for cons in sorted(_YOON, key=len, reverse=True):
            if w.startswith(cons, i):
                j = i + len(cons)
                if j < len(w) and w[j] in _ORDER:
                    out.append(_YOON[cons][_ORDER.index(w[j])])
                    i = j + 1
                else:
                    out.append(_YOON[cons][2])
                    i = j
                matched = True
                break
        if matched:
            continue
        ch = w[i]
        if ch in _ORDER:
            out.append(_V[ch])
            i += 1
            continue
        if ch in _ROWS:
            if i + 1 < len(w) and w[i + 1] in _ORDER:
                kana = _ROWS[ch][_ORDER.index(w[i + 1])]
                if kana == "-":
                    return None
                out.append(kana)
                i += 2
            else:
                # a bare consonant: n closes a syllable, the rest take u.
                # m before a labial closes it too -- Campiglio is カンピリョ,
                # not カムピリョ.
                if ch == "n" or (ch == "m" and i + 1 < len(w)
                                 and w[i + 1] in "pbm"):
                    out.append("ン")
                else:
                    kana = _BARE.get(ch, _ROWS[ch][2])
                    if kana == "-":
                        return None
                    out.append(kana)
                i += 1
            continue
        return None
    return "".join(out) or None


def place_to_katakana(phrase):
    """Katakana for a multi-word place, or None if ANY word fails.

    Partial output would be a half-transliterated name, which is worse than
    nothing — it looks deliberate.
    """
    if not phrase:
        return None
    words = [w for w in re.split(r"[\s\-–—']+", phrase.strip()) if w]
    if not words:
        return None
    parts = []
    for w in words:
        kana = to_katakana(w)
        if not kana:
            return None
        parts.append(kana)
    return "・".join(parts)
