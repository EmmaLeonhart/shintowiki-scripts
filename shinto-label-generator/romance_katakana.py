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
    w = _fold(word.lower().replace("ç", "s").replace("ã", "a").replace("õ", "o"))
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


# --------------------------------------------------------------------------
# Per-language rules, chosen from the item's own P17 rather than assumed
# --------------------------------------------------------------------------
# ⛔ An earlier version applied Italian rules to everything and said so in a
# comment, on the belief that the corpus was Italian-dominant. Measured, it is
# not: Galician 15% + Portuguese 2.3% + Spanish ~2% against Italian 11%. So the
# tie-break was backwards for the larger slice, and `Conceição` read as
# コンチェイーサン (Italian ce = /tʃe/) where Portuguese wants コンセイサン.
#
# There is no need to guess at all: P17 is present on 99.7% of these items.

# Shared by every Romance language here.
_COMMON_HEAD = [("qu", "k"), ("gue", "ge"), ("gui", "gi"),
                ("que", "ke"), ("qui", "ki")]
_COMMON_TAIL = [("x", "ks"), ("c", "k"), ("Ĉ", "ch")]

_RULES = {
    # Italian: soft c/g are affricates, gn/gli are palatals, z is ts, double
    # consonants are geminates.
    "it": _COMMON_HEAD + [
        ("cch", "kk"), ("ggh", "gg"),
        ("chi", "ki"), ("che", "ke"), ("cha", "ka"), ("cho", "ko"),
        ("ghi", "gi"), ("ghe", "ge"),
        ("h", ""),
        ("scia", "sha"), ("scio", "sho"), ("sciu", "shu"),
        ("sci", "shi"), ("sce", "she"), ("sc", "sk"),
        ("cia", "Ĉa"), ("cio", "Ĉo"), ("ciu", "Ĉu"),
        ("ce", "Ĉe"), ("ci", "Ĉi"),
        ("gia", "ja"), ("gio", "jo"), ("giu", "ju"), ("ge", "je"), ("gi", "ji"),
        ("gn", "ny"), ("gli", "ry"), ("gl", "l"),
        ("z", "ts"),
    ] + _COMMON_TAIL,
    # Portuguese: soft c/g are fricatives, lh/nh are the palatals, z is z,
    # and ç/ão are handled before folding.
    "pt": _COMMON_HEAD + [
        ("ch", "sh"),
        ("lh", "ry"), ("nh", "ny"),
        ("h", ""),
        ("ce", "se"), ("ci", "si"),
        ("gia", "ja"), ("gio", "jo"), ("giu", "ju"), ("ge", "je"), ("gi", "ji"),
        ("ss", "s"), ("z", "z"), ("j", "j"),
    ] + _COMMON_TAIL,
    # Spanish: soft c is s, g before e/i is h, j is h, ll is y, ñ is ny.
    "es": _COMMON_HEAD + [
        ("ch", "Ĉ"),
        ("ll", "y"), ("h", ""),
        ("ce", "se"), ("ci", "si"),
        ("ge", "he"), ("gi", "hi"), ("ja", "ha"), ("jo", "ho"), ("ju", "hu"),
        ("je", "he"), ("ji", "hi"),
        ("z", "s"),
    ] + _COMMON_TAIL,
}
DEFAULT_RULES = "it"

# P17 country QID -> which rule set. Anything absent falls back to DEFAULT_RULES.
COUNTRY_RULES = {
    "Q38": "it",                                   # Italy
    "Q45": "pt", "Q155": "pt", "Q1029": "pt", "Q916": "pt",   # PT, BR, MZ, AO
    "Q29": "es", "Q96": "es", "Q414": "es", "Q739": "es",     # ES, MX, AR, CO
    "Q419": "es", "Q298": "es", "Q717": "es", "Q736": "es",   # PE, CL, VE, EC
    "Q77": "es", "Q750": "es", "Q241": "es", "Q800": "es",    # UY, BO, CU, CR
    "Q774": "es", "Q783": "es", "Q811": "es", "Q736": "es",   # GT, HN, NI
}


def rules_for_country(qid):
    """Which rule set an item's P17 implies, or **None** to refuse.

    ⛔ This returned DEFAULT_RULES for anything unlisted, which meant every
    country fell back to ITALIAN. Measured on the real corpus that was 14,000+
    items, and it leaked: French names pass the Romance shape gate and were read
    as Italian --

        Chapelle Notre-Dame-de-Pitié de Trouville-sur-Mer
          -> ピーチエ・トロウヴィッレ・スル・メル

    which is the same failure as reading Rzhavets as Italian, just harder to
    spot because the letters look plausible. French orthography is not close to
    phonemic (silent finals, nasal vowels), so there is no cheap rule for it.
    An unlisted country now REFUSES rather than guessing.
    """
    return COUNTRY_RULES.get(qid)


def _romanise(word, rules=DEFAULT_RULES):
    """Romance spelling -> a plain consonant/vowel string kana can be built from.

    The digraphs are the whole reason this is language-specific, and why the
    rule set is chosen per item rather than fixed:
      * Italian `ch`/`gh` are hard K/G, `ci`/`ge` are affricates, `gn`/`gli` are
        palatals, `z` is TS.
      * Portuguese `ce`/`ci` are S, `lh`/`nh` are the palatals, `ch` is SH.
      * Spanish `ce`/`ci` are S, `ge`/`gi`/`j` are H, `ll` is Y.

    ⛔ The sentinel Ĉ is not decoration: the leftover ("c","k") would otherwise
    rewrite the c of a `ch` a soft-c rule had just produced. Città -> クヒッタ.
    """
    if not is_romance_shaped(word):
        return None
    # ⛔ Before folding: the cedilla and the tilde are NOT stress marks, they
    # change the sound. _fold() strips combining marks, so ç became a bare c and
    # then k -- Graças came out グラーカス instead of グラーサス -- and the "ão"
    # rule could never match a string the fold had already flattened.
    w = word.lower()
    for a, b in (("ç", "s"), ("ãe", "ain"), ("ão", "an"), ("õe", "oin"),
                 ("ã", "an"), ("õ", "on"), ("ñ", "ny")):
        w = w.replace(a, b)
    w = _fold(w)
    for a, b in _RULES.get(rules, _RULES[DEFAULT_RULES]):
        w = w.replace(a, b)
    return w or None


_CHOONPU = "ー"
_MORA_ONLY = {"ッ", "ン"}


def _accented_vowel_index(word):
    """Index of the source vowel carrying a written accent, or None.

    Italian and Portuguese write the accent only when stress is irregular, so
    its presence is authoritative and its absence means the default applies.
    """
    folded_i = -1
    for ch in unicodedata.normalize("NFD", word):
        if unicodedata.combining(ch):
            return folded_i          # the vowel just counted carries it
        if ch.lower() in "aeiou":
            folded_i += 1
    return None


def _lengthen(units, stressed):
    """Insert ー after the stressed kana when its syllable is open.

    A syllable closed by ッ or ン is already heavy and takes no ー — which is
    why Cardello is カルデッロ and Trento is トレント.
    """
    if stressed is None or not (0 <= stressed < len(units)):
        return units
    if units[stressed] in _MORA_ONLY:
        return units
    if stressed + 1 < len(units) and units[stressed + 1] in _MORA_ONLY:
        return units
    return units[:stressed + 1] + [_CHOONPU] + units[stressed + 1:]


def _stress_unit(vowel_units, word):
    """Which kana unit carries the stress.

    ⚠ Stress is a property of the SOURCE word's syllables, not of the kana. A
    first version counted kana and got Coimbra wrong, because ブラ is two morae
    and one syllable. So the vowel GROUPS of the romanised form are counted —
    adjacent vowels are one syllable (the `oi` of Coimbra, the `ua` of Tábuas) —
    and the stressed group's LAST kana is the one lengthened.

    `vowel_units` is [(unit_index, source_vowel_index)] in order.
    """
    if not vowel_units:
        return None
    groups = []
    for unit_i, vowel_i in vowel_units:
        if groups and vowel_i == groups[-1][-1][1] + 1:
            groups[-1].append((unit_i, vowel_i))
        else:
            groups.append([(unit_i, vowel_i)])
    acc = _accented_vowel_index(word)
    if acc is not None:
        for g in groups:
            if any(vi == acc for _, vi in g):
                return g[-1][0]
    if len(groups) < 2:
        return None              # one syllable takes no ー here
    return groups[-2][-1][0]


def to_katakana(word, rules=DEFAULT_RULES):
    """Katakana for one Romance word, or None if it cannot be read.

    ⚠ **Vowel length is applied by RULE, and the rule is not universal.** Romance
    stress falls on the penultimate syllable unless written otherwise, and
    Japanese writes a stressed open syllable long — Fiore is フィオーレ, Salute is
    サルーテ, Loreto is ロレート. Applied consistently this also gives ミラーノ for
    Milano, where established Japanese usage is ミラノ. That is the cost, and it
    is the right trade here: the qualifiers this reads are small localities
    (Pero, Cardello, Campiglio, Tábuas), essentially none of which have an
    established Japanese exonym to conflict with.
    """
    w = _romanise(word, rules)
    if not w:
        return None
    out = []
    vowel_units = []          # (index in out, position of the vowel IN w)
    i = 0
    while i < len(w):
        # ⛔ A geminate DIGRAPH, which the single-character test below cannot see.
        # Italian `zz` is /tts/, and `z -> ts` turns `piazza` into `piatstsa`,
        # where no two adjacent characters are equal — so it came out ピアーツツァ
        # instead of ピアッツァ. Measured 2026-09-19: 12 emitted labels, among them
        # ポーツツォ for Pozzo and ラツツァーロ for Lazzaro.
        if any(w.startswith(d + d, i) for d in ("ts", "ch", "sh")):
            out.append("ッ")
            i += 2
            continue
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
                    vowel_units.append((len(out), j))
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
            vowel_units.append((len(out), i))
            out.append(_V[ch])
            i += 1
            continue
        if ch in _ROWS:
            if i + 1 < len(w) and w[i + 1] in _ORDER:
                kana = _ROWS[ch][_ORDER.index(w[i + 1])]
                if kana == "-":
                    return None
                vowel_units.append((len(out), i + 1))
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
    if not out:
        return None
    return "".join(_lengthen(out, _stress_unit(vowel_units, word)))


def place_to_katakana(phrase, rules=DEFAULT_RULES):
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
        kana = to_katakana(w, rules)
        if not kana:
            return None
        parts.append(kana)
    return "・".join(parts)
