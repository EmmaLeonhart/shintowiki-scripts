#!/usr/bin/env python3
"""
plain_latin_katakana.py
=======================
Balkan / Turkic / Malay proper names into katakana — the name half of the mosque
labels. The sibling of `romance_katakana.py`, and deliberately a separate module:
that one's whole output rule is Romance penultimate stress written as ー
(Loreto → ロレート), and none of these languages have it. Ömer is オメル, not
オーメル.

**Why these three families and no others.** Measured over the 245 mosques in the
religious-building corpus (2026-09-19), the countries are North Macedonia 98,
Indonesia 39, Turkey 23, Azerbaijan 17, Malaysia 5, Bosnia 3, Brunei 1 — **186 of
245** under three orthographies that are each close to one-letter-one-sound, which
is what makes a rule-based reading honest work rather than invention:

    bs   Bosnian / Croatian / Serbian-Latin / Macedonian-Latin   č ć š ž đ dž lj nj
    tr   Turkish / Azerbaijani                                   c ç ş ğ ı ö ü ə x
    ms   Malay / Indonesian                                      sy c kh ng

⛔ **Everything else refuses**, and the refusals are the point. The same corpus
carries French (Mosquée de Carpentras), Russian-romanised Tatar (Bolshiye
Kaybitsy), romanised Arabic (Abd Al-Mun'im Riyad) and German (Donauwörther
Straße). French orthography is not phonemic; Arabic romanisation is not even
consistent with itself across the corpus. `rules_for_country` returns None for all
of them, exactly as `romance_katakana.rules_for_country` does — that function
already learned this lesson the expensive way, by defaulting to Italian and
reading `Notre-Dame-de-Pitié` as ピーチエ.

⛔ **ja only.** There is no rule-based route from a Macedonian village name to
Chinese characters or hangul; those are conventions, not derivations. zh and ko
keep refusing the named mosques, and get the generic ones (`Old Mosque`,
`Great Mosque`) from the modifier table instead, which is a translation and not a
reading.
"""

import re
import unicodedata

# The kana grid itself is not duplicated — one source of truth, in the module
# that established it. Only the ROMANISATION rules differ between the two.
from romance_katakana import (          # noqa: F401
    _V, _ROWS, _YOON, _ORDER, _BARE,
)

# --------------------------------------------------------------------------
# Romanisation rules, per orthography family
# --------------------------------------------------------------------------
# Sentinels, borrowed from romance_katakana's Ĉ trick: a rule's OUTPUT must not
# be eaten by a later rule's input. ž → j → y would turn Žarko into ヤルコ, and
# č → ch → (c → ts) turned Gradačac into グラダツハツ, a c the ch rule had just
# written. Both park on a sentinel until the plain-letter rules have run.
_CHOONPU = "ー"

_J = "Ĵ"
_CH = "Ĉ"
# German `ch` is a fricative that the kana grid writes with the h row (Bach バッハ,
# ich イヒ). It parks on its own sentinel because `ch -> h` would otherwise be
# re-read by nothing, but `tsch -> ch` writes a ch the same pass must NOT touch.
_H = "Ĥ"
# ⛔ German s before a vowel is /z/, and written as a plain `z` it was eaten by
# German's own `z -> ts` rule one pass later: Salvator came back ツァルファトル,
# Rosen ロツェン, Sachsen ツァハツェン. Same trick, same reason, as `_CH` and `_J`.
_Z = "Ż"

_RULES = {
    # Bosnian / Croatian / Serbian-Latin / Macedonian-Latin. Diacritics are the
    # phonemes here, so these run BEFORE any accent folding.
    "bs": [
        ("dž", _J), ("đ", _J), ("ž", _J),
        ("lj", "ry"), ("nj", "ny"),
        ("č", _CH), ("ć", _CH), ("š", "sh"),
        ("c", "ts"),
        ("j", "y"),
        (_J, "j"), (_CH, "ch"),
    ],
    # Turkish / Azerbaijani. ı is the unrounded high vowel and reads as ウ
    # (Kızıl → クズル); ə is Azerbaijani's open front vowel and reads as ア;
    # x is the velar fricative and reads as ハ行. Turkish j is already /ʒ/ and
    # needs no rule — the kana grid's j row is ジャ.
    "tr": [
        ("c", "j"), ("ç", "ch"), ("ş", "sh"),
        ("ı", "u"), ("ə", "a"), ("x", "h"),
        # Not Turkish orthography, but the corpus romanises Azerbaijani names
        # through English: Gazakh for Qazax, Bakhshi for Baxsi. Without this the
        # h opened its own syllable -- ガザクフ, バクフシ.
        ("kh", "h"),
        ("ğ", ""),
    ],
    # German (Germany, Austria, German-speaking Switzerland). Emma, 2026-09-19,
    # asked which orthographies to build for the refused residue: "All of them,
    # French included." German is 3,357 of the 6,627 and is the most regular of
    # them -- the spelling is a near-transparent map onto the sound once the
    # digraphs and the umlauts are resolved, which `_pre_german` does first.
    #
    # ⚠ Order is load-bearing throughout. `tsch` must beat `sch`; `chs` must beat
    # `ch`; `v -> f` must run before `w -> v` or every W becomes an F.
    "de": [
        ("tsch", _CH), ("sch", "sh"),
        ("chs", "ks"), ("ch", _H),
        ("ck", "kk"), ("ph", "f"), ("th", "t"), ("qu", "kv"), ("x", "ks"),
        ("tz", "tts"), ("z", "ts"),
        ("v", "f"), ("w", "v"), ("j", "y"),
        # Diphthongs and written length. `eu`/`äu` are /ɔʏ/ (Häuser ホイザー),
        # `ei`/`ey` are /aɪ/ (Stein シュタイン), `ie` is a long i (Lieben リーベン).
        ("eu", "oi"), ("ei", "ai"), ("ey", "ai"),
        ("ie", "i" + _CHOONPU), ("ee", "e" + _CHOONPU),
        ("aa", "a" + _CHOONPU), ("oo", "o" + _CHOONPU),
        # A bare `c` is only in loans, and it is /ts/ before a front vowel and
        # /k/ elsewhere: Cäcilia ツェツィーリア, Clemens クレメンス. Last in the
        # list so it cannot touch the c of `sch`, `tsch`, `ch` or `ck`, all of
        # which are resolved above. Without it `Clemens` was refused outright.
        ("ce", "tse"), ("ci", "tsi"), ("cy", "tsi"), ("c", "k"),
        (_H, "h"), (_CH, "ch"), (_Z, "z"),
    ],
    # Malay / Indonesian. Fully phonemic; the only digraphs are sy, kh, gh and
    # c. ng before a VOWEL needs no rule — a bare n closes the syllable as ン
    # and the g carries on (Nanga → ナンガ, Bangis → バンギス); ng before a
    # consonant is a plain ŋ and the g is not pronounced, which `_NG` handles.
    "ms": [
        ("sy", "sh"), ("kh", "h"), ("gh", "g"),
        # th and dh are Arabic-loan spellings pronounced as plain t and d:
        # Sulthan is スルタン, not スルトハン; Raudhatul is ラウダトゥル.
        ("th", "t"), ("dh", "d"),
        ("c", "ch"), ("q", "k"),
    ],
}

# Malay ŋ with no following vowel: Mungsolkanas is mung-sol, not mun-gu-sol.
_NG = re.compile(r"ng(?=[^aeiou]|$)")

# A `y` with no vowel after it is the vowel /i/, not the glide: Süleyman is
# スレイマン and Hasanbey is ハサンベイ. Written as a glide they came out
# スレユマン and ハサンベユ.
_Y_VOWEL = re.compile(r"y(?![aeiou])")

# Letters each family may contain AFTER its rules have run. Anything else is a
# word this module cannot read, and it refuses rather than improvise.
_ALLOWED = set("abcdefghijklmnopqrstuvwyz")

# Letters that do not occur in the source orthography at all. Their presence
# means the word is not that language — the cheap version of
# romance_katakana.is_romance_shaped, and it is what keeps `Donauwörther` out of
# the Macedonian rule set.
_FOREIGN = {
    "bs": set("qwxyÿäöüßıəğşàâéèêëîïôùûñç"),
    "tr": set("qwäßàâéèêëîïôùûñčćšžđ"),
    "ms": set("xäöüßàâéèêëîïôùûñčćšžđıəğş"),
    # German has no ç ñ, no Slavic háčeks, no Turkish dotless ı, and no French
    # accents. Their presence means the word is not German -- the cheap half of
    # the test; `_onset_ok` is the other half.
    "de": set("çñčćšžđıəğşàéèêëîïôùûý"),
}

# Loanword columns the bare kana grid does not carry. Turkish and Malay tu/ti
# are /tu/ and /ti/, not /tsu/ and /tʃi/: Saltuk is サルトゥク, Cipaganti is
# チパガンティ. The grid's t/d rows gave サルツク and チパガンチ.
_EXTRA = {
    "t": ("タ", "ティ", "トゥ", "テ", "ト"),
    "d": ("ダ", "ディ", "ドゥ", "デ", "ド"),
    "w": ("ワ", "ウィ", "ウ", "ウェ", "ウォ"),
    # ⛔ `ye` and `yi` are HOLES in the bare grid (`_ROWS["y"]` is "ヤ-ユ-ヨ"),
    # and a hole returns None for the whole word. German j is /j/, so `Jerusalem`
    # and `Jördenstorf` -- Emma's own example -- both fell through one.
    "y": ("ヤ", "イィ", "ユ", "イェ", "ヨ"),
}

# ⛔ Which doubled consonants become ッ, per family. bs/tr/ms needed none, so the
# module had no geminate rule at all and `Göttingen` came back ゲトティンゲン.
#
# ⚠ German is NOT Italian here: only OBSTRUENTS geminate. Müller is ミュラー and
# Mannheim マンハイム, not ミュッレル and マンンハイム, while Göttingen really is
# ゲッティンゲン and Rostock ロストック. So l/m/n/r collapse to a single consonant
# in `_pre_german` and never reach this set.
_GEMINATES = {"de": set("ptkbdgsfzh")}

# A palatal with no vowel after it takes the i column, not the u column: the nj
# of Vrbanjska is ヴルバニスカ, not ヴルバニュスカ.
_BARE_YOON = {"ny": "ニ", "ry": "リ"}

# ö and ü after a consonant that HAS a small-y row take it — Göreme is ギョレメ,
# Büyük is ビュユク. After s/z/t/d/f/v/l and word-initially they do not: Süleyman
# is スレイマン and Ömer is オメル, not スュレイマン and ョメル.
_YOON_HOSTS = set("kgbpmrnh")


def _pre_turkic_rounded(word):
    """Resolve Turkish/Azerbaijani ö and ü to a plain vowel, with the small-y
    row inserted where the preceding consonant can host it."""
    out = []
    for i, ch in enumerate(word):
        if ch not in "öü":
            out.append(ch)
            continue
        plain = "o" if ch == "ö" else "u"
        prev = word[i - 1] if i else ""
        out.append("y" + plain if prev in _YOON_HOSTS else plain)
    return "".join(out)


# ------------------------------------------------------------------ German
# Word-initial s before p or t is /ʃ/: Straße シュトラーセ, Spital シュピタール.
_DE_INITIAL_SP = re.compile(r"^s(?=[pt])")
# An h AFTER a vowel and not before one is the length mark, not a consonant:
# Kuhstall クーシュタル, Mühle ミューレ. Before a vowel it is a real h (Ehe エーエ
# is the length mark case too, but `sehen` is ze-hen and keeps its h).
_DE_LENGTH_H = re.compile(r"(?<=[aeiou])h(?![aeiou])")
# s before a vowel is /z/: Salvator ザルヴァトール, Rosen ローゼン. A DOUBLED s
# is /s/ and is parked first, or `Straße -> strasse` would come back シュトラゼ.
_DE_S_VOICED = re.compile(r"s(?=[aeiou])")


def _de_ch(w):
    """German `ch` with no vowel after it, which is most of them.

    It takes the colour of the NEAREST PRECEDING VOWEL, and that vowel may be
    several consonants back — the ch of `Kirch` is coloured by the i of Kir-.
    A regex with `([aeiou])ch` could not see it and left キルフ.

    ⚠ Front vs back matters and is not the same rule. After e or i it is the
    ich-Laut and is written ヒ regardless of the vowel: Knecht クネヒト, Licht
    リヒト. After a, o or u it is the ach-Laut and echoes: Nacht ナハト, Tochter
    トホター, Bach バハ.

    With NO preceding vowel at all it is the Greek-loan /k/: Christkönig is
    クリストケーニヒ, not フリストケニク.
    """
    out = []
    i = 0
    while i < len(w):
        if not w.startswith("ch", i):
            out.append(w[i])
            i += 1
            continue
        # `tsch` is one affricate and belongs to the rules table, not here.
        if w[max(0, i - 2):i] == "ts":
            out.append("ch")
            i += 2
            continue
        if i + 2 < len(w) and w[i + 2] in "aeiou":
            out.append("ch")            # a real syllable onset; rules handle it
            i += 2
            continue
        # `chs` is /ks/: Sachsen ザクセン, Fuchs フクス. Handled here rather than
        # in the rules table because this pass consumes every ch before the table
        # is reached, and without it Sachsen came back ザハゼン.
        #
        # ⚠ That s may already be the voiced-s sentinel — s-voicing runs first and
        # the s of Sachsen is followed by e. It is /s/ here, so the k takes the s
        # with it and the sentinel never survives to be read as ゼ.
        if i + 2 < len(w) and w[i + 2] in ("s", _Z):
            out.append("ks")
            i += 3
            continue
        prev = next((c for c in reversed(w[:i]) if c in "aeiou"), None)
        if prev is None:
            out.append("k")
        elif prev in "ei":
            out.append("hi")
        else:
            out.append("h" + prev)
        i += 2
    return "".join(out)
# Final -ig is /ɪç/: König ケーニヒ. Devoicing would otherwise make it ク.
_DE_FINAL_IG = re.compile(r"ig$")
# Only obstruents geminate in German loans; l/m/n/r collapse. Müller ミュラー.
_DE_COLLAPSE = re.compile(r"([lmnr])\1")
# Final -er is /ɐ/, written アー: Wanderer ヴァンデラー, Peter ペター.
_DE_FINAL_ER = re.compile(r"er$")
# A final obstruent devoices: Wald ヴァルト, Berg ベルク, Jakob ヤーコプ. This is
# Auslautverhärtung and it is exceptionless in the standard language.
_DE_FINAL_DEVOICE = {"b": "p", "d": "t", "g": "k"}
_SS = "Ŝ"


def _pre_german(word):
    """Umlauts, written length, s-voicing and final devoicing.

    ⚠ German ö is NOT the Turkish ö. Köln is ケルン and Göttingen ゲッティンゲン,
    so it reads as a plain e; `_pre_turkic_rounded` would have given ケョルン.
    ü is the one that takes the small-y row, and only after a consonant that can
    host it: München ミュンヘン but Übersee ウーバーゼー.
    """
    w = unicodedata.normalize("NFC", word).lower()
    w = w.replace("ß", _SS)
    w = w.replace("ss", _SS)
    w = w.replace("ä", "e").replace("ö", "e")
    out = []
    for i, ch in enumerate(w):
        if ch != "ü":
            out.append(ch)
            continue
        prev = w[i - 1] if i else ""
        out.append("yu" if prev in _YOON_HOSTS else "u")
    w = "".join(out)
    w = _DE_INITIAL_SP.sub("sh", w)
    w = _DE_S_VOICED.sub(_Z, w)
    w = w.replace(_SS, "ss")
    w = _DE_FINAL_IG.sub("ihi", w)
    w = _de_ch(w)
    w = _DE_LENGTH_H.sub(_CHOONPU, w)
    w = _DE_COLLAPSE.sub(r"\1", w)
    w = _DE_FINAL_ER.sub("a" + _CHOONPU, w)
    # ⚠ Final -ng is the velar nasal, not a devoicing g: Wolfgang is
    # ヴォルフガング. Auslautverhärtung applies to the stop, and /ŋ/ is not one.
    if w and w[-1] in _DE_FINAL_DEVOICE and not w.endswith("ng"):
        w = w[:-1] + _DE_FINAL_DEVOICE[w[-1]]
    return w


_DOUBLE_VOWEL = re.compile(r"([aeiou])\1")


# ⛔ The letters alone are not enough to tell one of these orthographies from a
# language that merely shares its alphabet. `Rzhavets` is all legal Turkish
# letters and came back サル・ルズハヴェツ from the Turkish rules — the exact
# confident-wrong failure `romance_katakana.is_romance_shaped` exists to stop.
# PHONOTACTICS catch it: Turkish has no native initial consonant cluster at all,
# and Malay only a short list of them. Slavic allows almost anything, so `bs`
# only refuses the extreme case.
_MS_ONSETS = {"br", "bl", "dr", "kr", "kl", "pr", "pl", "tr", "gr", "gl",
              "sp", "st", "sk", "sw", "sl", "sn", "sm"}
# German really does cluster three deep -- `Strasse` is s-t-r, and after
# `^s[pt] -> sh` the sh counts as one, so the cap is 3.
_MAX_ONSET = {"tr": 1, "ms": 2, "bs": 3, "de": 3}

# Digraphs that are ONE consonant by the time the kana grid reads them.
_DIGRAPHS = ("sh", "ch", "ts", "ny", "ry", "ky", "gy", "hy", "by", "py", "my")


def _onset_ok(w, rules):
    collapsed = w
    for d in _DIGRAPHS:
        collapsed = collapsed.replace(d, "C")
    m = re.match(r"^([^aeiouー]+)", collapsed)
    if not m:
        return True
    onset = m.group(1)
    if len(onset) > _MAX_ONSET[rules]:
        return False
    if rules == "ms" and len(onset) == 2 and w[:2] not in _MS_ONSETS:
        return False
    return True


def _romanise(word, rules):
    """Source spelling → a plain consonant/vowel string the kana grid can read,
    or None when the word is not of that orthography."""
    w = unicodedata.normalize("NFC", word).lower()
    if not w or any(c.isdigit() for c in w):
        return None
    if _FOREIGN[rules] & set(w):
        return None
    if rules == "tr":
        w = _pre_turkic_rounded(w)
    if rules == "de":
        w = _pre_german(w)
    for a, b in _RULES[rules]:
        w = w.replace(a, b)
    if rules == "ms":
        w = _NG.sub("n", w)
    w = _Y_VOWEL.sub("i", w)
    # Turkish ğ is deleted above, which leaves the vowels it separated adjacent:
    # Ağa → aa. Japanese writes that as a long vowel, not as two — アー, not アア.
    w = _DOUBLE_VOWEL.sub(r"\1" + _CHOONPU, w)
    if not set(w) <= (_ALLOWED | {_CHOONPU}):
        return None
    if not w or not _onset_ok(w, rules):
        return None
    return w


def to_katakana(word, rules):
    """Katakana for one word, or None if it cannot be read.

    No vowel lengthening is applied. That is the whole reason this is not
    `romance_katakana`: Romance writes a stressed open penult long, and none of
    these three families does. The only ー this emits is the one Turkish ğ
    leaves behind.
    """
    if rules not in _RULES:
        return None
    w = _romanise(word, rules)
    if not w:
        return None
    out = []
    i = 0
    geminates = _GEMINATES.get(rules, frozenset())
    while i < len(w):
        if w[i] == _CHOONPU:
            out.append(_CHOONPU)
            i += 1
            continue
        if (w[i] in geminates and i + 1 < len(w) and w[i] == w[i + 1]):
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
                    out.append(_BARE_YOON.get(cons, _YOON[cons][2]))
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
        if ch in _EXTRA:
            if i + 1 < len(w) and w[i + 1] in _ORDER:
                out.append(_EXTRA[ch][_ORDER.index(w[i + 1])])
                i += 2
            else:
                out.append(_EXTRA[ch][2] if ch == "w" else _BARE[ch])
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
                # n closes a syllable; so does m before a labial. The rest take
                # the u column, except t and d, which take ト/ド in loanwords.
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


def name_to_katakana(phrase, rules):
    """Katakana for a multi-word name, ・-joined, or None if ANY word fails.

    All-or-nothing for the same reason `romance_katakana.place_to_katakana` is:
    a half-transliterated name looks deliberate and is not.
    """
    if not phrase or rules not in _RULES:
        return None
    words = [w for w in re.split(r"[\s\-–—'’]+", phrase.strip()) if w]
    if not words:
        return None
    parts = []
    for w in words:
        kana = to_katakana(w, rules)
        if not kana:
            return None
        parts.append(kana)
    return "・".join(parts)


# --------------------------------------------------------------------------
# P17 country → which family. Unlisted means refuse, never a default.
# --------------------------------------------------------------------------
COUNTRY_RULES = {
    # Balkans, Latin orthography
    "Q221": "bs",   # North Macedonia
    "Q225": "bs",   # Bosnia and Herzegovina
    "Q403": "bs",   # Serbia
    "Q224": "bs",   # Croatia
    "Q236": "bs",   # Montenegro
    "Q215": "bs",   # Slovenia
    # Turkic
    "Q43": "tr",    # Turkey
    "Q227": "tr",   # Azerbaijan
    # Malay world
    "Q252": "ms",   # Indonesia
    "Q833": "ms",   # Malaysia
    "Q921": "ms",   # Brunei
    "Q334": "ms",   # Singapore
    # German-speaking. 3,357 of the 6,627 religious buildings still refused at
    # the dedication gate on 2026-09-19 are these three.
    "Q183": "de",   # Germany
    "Q40": "de",    # Austria
    "Q39": "de",    # Switzerland
    "Q347": "de",   # Liechtenstein
}


def rules_for_country(qid):
    """Which family an item's P17 implies, or None to refuse."""
    return COUNTRY_RULES.get(qid)
