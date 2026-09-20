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
# ⛔ Polish ł is /w/ and Polish w is /v/, so the two collide: `Łódź` became
# `wudź` and the `w -> v` rule one pass later turned it into ヴジュ. It is ウッチ,
# and ロッチ or ヴジュ is a different town.
_W = "Ŵ"
# French nasal vowels close with ン, and that ン must survive the silent-final
# pass: `Jean` is ジャン, and letter-wise the n looked like a silent final and
# was stripped, leaving ジェア. Same for the ny of `gn` (Bourgogne ブルゴーニュ).
_N = "Ň"
_NY = "Ņ"
# The mute final e, kept as a sentinel rather than deleted. It is what stops the
# consonant before it from nasalising or falling silent: `Dame` is ダム and not
# ダン, `Sainte` サント and not サン. Removed after both of those passes.
_E = "Ə"

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
        # ⚠ `qu -> kw`, not `kv`. Written `kv`, the `v -> f` rule two lines down
        # ate it and `Quelle` came back クフェレ, `Quirinus` クフィリヌス — found
        # 2026-09-20 while building the Dutch family, which has the same pair.
        # `kw` survives that rule and German's own `w -> v` restores it: クヴェレ.
        # 2 labels in the corpus are affected, both `St. Quirin`.
        ("ck", "kk"), ("ph", "f"), ("th", "t"), ("qu", "kw"), ("x", "ks"),
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
    # French. 594 of the 6,627 (France 556, Belgium and Quebec the rest).
    #
    # ⛔ THE ONE EMMA WAS WARNED ABOUT. `romance_katakana.rules_for_country`
    # refuses French by design and says why in its own docstring: French
    # orthography is not close to phonemic, and reading it with Italian rules
    # gave `Chapelle Notre-Dame-de-Pitié de Trouville-sur-Mer` ->
    # ピーチエ・トロウヴィッレ・スル・メル. Shown that and asked which families
    # to build, Emma answered "All of them, French included" on 2026-09-19. So
    # this exists, and what makes it defensible rather than a guess is that the
    # hard parts are handled EXPLICITLY rather than fallen through:
    #
    #   * silent final consonants, which is most of them
    #   * the four nasal vowel series, which are the thing a letter-wise reader
    #     gets most wrong
    #   * the digraph vowels (eau, ou, oi, ai, eu), which are not the sum of
    #     their letters
    #
    # `_pre_french` does all three before the table below runs.
    # ⚠ Everything French does is order-dependent, so it all lives in
    # `_pre_french` and this table only puts the sentinels back. Restoring them
    # earlier is what turned `Chapelle` into サペルル: the `h -> ""` rule deleted
    # the h of the `sh` the `ch` rule had just written.
    # ⚠ `_CH` restores to `sh`, not `ch`: French ch is /ʃ/, so Chapelle is
    # シャペル. Restored as ch the kana grid read it チャペル.
    # ⛔ `_NY` is NOT restored here. `_Y_VOWEL` runs after this table and would
    # read the y of `ny` as the vowel /i/ — `Bourgogne` came back ブルゴニ. It is
    # restored after that pass instead. A lookbehind was tried first and was too
    # blunt: it also spared the b of Polish `Bydgoszcz`, whose y IS the vowel.
    "fr": [(_CH, "sh"), (_N, "n"), (_Z, "z")],
    # Romanised Russian and Ukrainian. 529 of the 6,627.
    #
    # ⚠ This family reads a TRANSCRIPTION, not an orthography. Stage 1's labels
    # write Russian names in the English scholarly-ish romanisation
    # (`Spaso-Preobrazhensky`, `Verkhnii Startsevo`, `Konevskaya`), so the
    # digraphs are English conventions for Cyrillic letters and the rules are a
    # map back to those letters: zh = ж, kh = х, shch = щ, ts = ц.
    "ru": [
        ("shch", "sh" + _CH), ("zh", _J), ("kh", "h"), ("ph", "f"),
        # A consonant + y + vowel is a PALATALISED consonant, not two syllables:
        # Lyubov is リュボフ and came back ルユボヴ.
        ("ly", "ry"), ("ny", "ny"), ("ty", "ty"), ("dy", "dy"),
        ("yo", "yo"), ("ya", "ya"), ("yu", "yu"), ("ye", "ye"), ("yi", "i"),
        ("ie", "ye"), ("io", "yo"),
        ("j", "y"),
        (_J, "j"), (_CH, "ch"),
    ],
    # Polish. 748 of the 6,627. Fully phonemic once the digraphs and the two
    # nasal vowels are resolved, which `_pre_polish` does first.
    #
    # ⚠ `szcz` must beat `sz` and `cz`; `dz`-family must beat a bare `d` + `z`;
    # `rz` must run before `z` becomes anything.
    "pl": [
        ("szcz", "sh" + _CH), ("sz", "sh"), ("cz", _CH),
        # ⚠ A palatal followed by i + VOWEL is one syllable, not two: `Kościan`
        # is コシチャン, not コシュチアン. The i is the palatalisation sign and
        # is not itself a vowel. Listed before the bare forms so it wins.
        ("dzia", _J + "a"), ("dzie", _J + "e"), ("dzio", _J + "o"),
        ("dziu", _J + "u"), ("dzi", _J + "i"),
        ("dź", _J), ("dż", _J), ("dz", _J),
        ("rz", _J), ("ż", _J), ("ź", _J),
        ("ch", "h"),
        ("cia", _CH + "a"), ("cie", _CH + "e"), ("cio", _CH + "o"),
        ("ciu", _CH + "u"), ("ci", _CH + "i"), ("ć", _CH),
        ("sia", "sha"), ("sie", "she"), ("sio", "sho"), ("siu", "shu"),
        ("si", "shi"), ("ś", "sh"),
        ("nia", "nya"), ("nie", "nye"), ("nio", "nyo"), ("niu", "nyu"),
        ("ni", "nyi"), ("ń", "ny"),
        ("zia", _J + "a"), ("zie", _J + "e"), ("zio", _J + "o"),
        ("ziu", _J + "u"), ("zi", _J + "i"),
        ("c", "ts"), ("w", "v"), ("j", "y"),
        (_J, "j"), (_CH, "ch"), (_W, "w"),
    ],
    # Czech and Slovak. 289 of the 6,627. The háčeks are the phonemes and the
    # acutes are LENGTH, which is the one thing this family writes that the
    # Balkan one does not -- `_pre_czech` turns them into ー.
    #
    # ⛔ `ř` reads as a plain r. It is /r̝/, a sound with no kana at all, and the
    # established ドヴォルザーク for Dvořák is a convention rather than a
    # derivation. A village name has no such convention to borrow, so the honest
    # output is the r.
    "cs": [
        ("ch", "h"),
        ("č", _CH), ("š", "sh"), ("ž", _J), ("ř", "r"),
        # ⚠ `dě` `tě` `ně` are the PALATALS /ɟɛ cɛ ɲɛ/, not d + ye: České
        # Budějovice is ブジェヨヴィツェ, and read as d + ye it was ブドイェ-.
        # `ď` and `ť` are the same two sounds under a different sign.
        ("dě", _J + "e"), ("tě", _CH + "e"), ("ně", "nye"), ("mě", "mnye"),
        ("ď", _J), ("ť", _CH), ("ě", "ye"), ("ň", "ny"),
        ("ľ", "ry"), ("ĺ", "l"), ("ŕ", "r"),
        # Czech j is /j/, so `ji` is イ: Jihlava イフラヴァ, Trojice トロイツェ.
        ("ji", "i"),
        ("c", "ts"), ("w", "v"), ("j", "y"),
        (_J, "j"), (_CH, "ch"),
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
    # Dutch. 304 of the 492 native-language long-tail labels, and the most
    # regular of the four Germanic families Emma asked for on 2026-09-20.
    #
    # ⚠ Order is load-bearing, as everywhere here. `sch` must beat `ch`; `ij`
    # must be resolved before the bare `j -> y` rule, or Rijk becomes リユク;
    # `ui`/`ou`/`ei` must beat their own single letters.
    "nl": [
        # ⚠ `sch` and `cht` are BOTH resolved in `_pre_dutch` — the first because
        # a bare s beside an h is read as one consonant by the kana grid, the
        # second because its fricative takes a different column. What reaches
        # here is the remaining plain `ch`.
        ("ch", _H),
        # ⛔ `qu` FIRST, before the vowel digraphs. `Quirinuskerk` — the one word
        # of the 304 this family could not read — contains `ui` inside its `qui`,
        # and the vowel rule fired there, leaving a bare `q` that nothing can
        # read: quirinuskerk -> qaurinuskerk -> refused.
        # ⚠ And `kw`, not `kv`: German writes `kv` and its own `v -> f` two rules
        # later turns that into `kf` (Quelle -> クフェレ). Dutch leaves `w` alone,
        # so `kw` lands on the ワ row: クウィリヌスケルク.
        ("qu", "kw"),
        # The digraph vowels. `ij` is /ɛi/ (Rijn ライン), `ui` is /œy/, which
        # Japanese has written アウ since Huis ten Bosch ハウステンボス.
        ("ij", "ai"), ("ui", "au"), ("ou", "au"), ("au", "au"),
        ("ei", "ai"), ("ey", "ai"),
        ("oe", "u" + _CHOONPU), ("eu", "u" + _CHOONPU), ("ie", "i" + _CHOONPU),
        ("ph", "f"), ("th", "t"), ("x", "ks"),
        # ⚠ v is /v/ but word-initial Dutch devoices it, and Japanese has
        # followed that for centuries: Van Gogh is ファン, Vermeer フェルメール.
        # w is NOT German w — it is /ʋ/, the ワ row, which `_EXTRA["w"]` carries.
        ("v", "f"),
        ("j", "y"),
        # A bare c is a loan letter: /s/ before a front vowel, /k/ elsewhere.
        # Last, so it cannot touch the c of `sch` or `ch`, both resolved above.
        ("ce", "se"), ("ci", "si"), ("cy", "si"), ("c", "k"),
        (_H, "h"),
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
    # Polish has no háčeks, no umlauts, no Romance accents, and no q/v/x at all.
    "pl": set("qvxçñčćšžđıəğşäöüßàâéèêëîïôùûýğ"),
    # Czech/Slovak have no Polish ogoneks or ł, no umlauts except Slovak ä, and
    # no French accents.
    "cs": set("qąęłńśźżçñđıəğşöüßàèêëîïùû"),
    # French has no háčeks, no Polish letters, no German ß, no Turkish ı.
    "fr": set("čćšžđłąęńśźżıəğşßñ"),
    # A romanised name is plain ASCII by definition: any diacritic at all means
    # the string is not a transcription and this family has no business reading
    # it. The apostrophe of a soft sign is stripped by `_pre_russian` first.
    "ru": set("čćšžđłąęńśźżıəğşßñçäöüàâéèêëîïôùûý"),
    # Dutch has no haceks, no Polish letters, no Romance accents beyond the
    # trema (which `_pre_dutch` removes before this runs), no Turkish letters,
    # and no German szlig. ⚠ It DOES have q/x/y, unlike Polish, and it is the
    # only family here whose ij is a letter pair rather than a diacritic.
    "nl": set("čćšžđłąęńśźżıəğşßñçàâêîôùûáíóúýéè"),
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
    "y": ("ヤ", "イ", "ユ", "イェ", "ヨ"),
}

# ⛔ Which doubled consonants become ッ, per family. bs/tr/ms needed none, so the
# module had no geminate rule at all and `Göttingen` came back ゲトティンゲン.
#
# ⚠ German is NOT Italian here: only OBSTRUENTS geminate. Müller is ミュラー and
# Mannheim マンハイム, not ミュッレル and マンンハイム, while Göttingen really is
# ゲッティンゲン and Rostock ロストック. So l/m/n/r collapse to a single consonant
# in `_pre_german` and never reach this set.
# ⚠ Dutch doubles a consonant to mark the vowel BEFORE it short, not to
# geminate the consonant: Bakker is バッケル and Hogendijk ホーヘンダイク,
# so the obstruent set is the same as German's and l/m/n/r stay single for
# the same reason — Willem is ウィレム, not ウィッレム.
_GEMINATES = {"de": set("ptkbdgsfzh"), "nl": set("ptkbdgsfzh")}

# A palatal with no vowel after it takes the i column, not the u column: the nj
# of Vrbanjska is ヴルバニスカ, not ヴルバニュスカ.
_BARE_YOON = {"ny": "ニ", "ry": "リ"}

# ⚠ A word-final affricate is チ in the Slavic families -- Czech Třebíč, Polish
# Łódź, both full of final č/ć -- and チュ in German, whose -tsch is a cluster
# with an audible off-glide: Deutsch is ドイチュ. So the override is per family,
# not global; set globally it broke German.
_BARE_YOON_BY_RULES = {"pl": {"ch": "チ"}, "cs": {"ch": "チ"},
                       # French -gne is /ɲ/ with an audible off-glide:
                       # Bourgogne ブルゴーニュ, not ブルゴニ.
                       "fr": {"ny": "ニュ"}}

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


# ------------------------------------------------------------------ Polish
# The two nasal vowels. Before a labial they close with m, elsewhere with n, and
# a word-final ę is plain e -- Łódź's neighbours are full of both.
_PL_NASAL = [("ą", "on"), ("ę", "en")]
# ⚠ The DIGRAPHS come first and the single letters must not touch them.
# `Bydgoszcz` ends in a z that belongs to `cz`, and devoicing it letter-wise gave
# ビドゴシュツス; `Łódź` ends in the affricate `dź`, whose voiceless partner is
# `ć`, not `d` + `ś`.
_PL_FINAL_DIGRAPH = {"dź": "ć", "dż": "cz", "dz": "c"}
_PL_FINAL_KEEP = ("cz", "sz", "rz", "ch", "ść", "szcz")
_PL_FINAL_DEVOICE = {"w": "f", "b": "p", "d": "t", "g": "k", "z": "s",
                     "ż": "sz", "ź": "ś"}
_PL_NASAL_LABIAL = [("ąb", "omb"), ("ąp", "omp"), ("ęb", "emb"), ("ęp", "emp")]


def _pre_polish(word):
    """Nasal vowels, ó and ł.

    ⚠ `ł` is /w/, not /l/: Łódź is ウッチ and Łagiewniki ワギェヴニキ. Read as an
    l it would be ロッチ, which is a different town.
    """
    w = unicodedata.normalize("NFC", word).lower()
    for a, b in _PL_NASAL_LABIAL:
        w = w.replace(a, b)
    if w.endswith("ę"):
        w = w[:-1] + "e"
    for a, b in _PL_NASAL:
        w = w.replace(a, b)
    w = w.replace("ó", "u").replace("ł", _W)
    # Final obstruents devoice, and the commonest of them by far is the -ów of a
    # genitive plural place name: Rzeszów is ジェシュフ, Tczew トチェフ.
    for a, b in _PL_FINAL_DIGRAPH.items():
        if w.endswith(a):
            w = w[: -len(a)] + b
            return w
    if (w and w[-1] in _PL_FINAL_DEVOICE
            and not any(w.endswith(k) for k in _PL_FINAL_KEEP)):
        w = w[:-1] + _PL_FINAL_DEVOICE[w[-1]]
    return w


# ------------------------------------------------------------ Czech / Slovak
# ⭐ The acutes are LENGTH, and they are the reason this is not the `bs` family:
# Bosnian writes no vowel length, Czech writes it on every long vowel. `ů` is the
# same long u under a different sign (Dvůr ドヴール).
_CS_LONG = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ý": "i",
            "ů": "u"}
# ⚠ NOT length. Slovak ô is the diphthong /uo/ and ä is a plain open e; both
# were taking a ー from the long-vowel table they do not belong in.
_CS_PLAIN = {"ô": "uo", "ä": "e"}


def _pre_czech(word):
    w = unicodedata.normalize("NFC", word).lower()
    out = []
    for ch in w:
        if ch in _CS_LONG:
            out.append(_CS_LONG[ch] + _CHOONPU)
        else:
            out.append(_CS_PLAIN.get(ch, ch))
    return "".join(out)


# ------------------------------------------------------------------ French
# ⛔ The silent final consonant is the single biggest thing French spelling does
# that its letters do not say, and it is why `romance_katakana` refuses the
# language: `Planty` ends in a pronounced y, `Plants` would not sound its s.
# c, f, l and r ARE sounded finally (the traditional CaReFuL set), and so is a
# final consonant followed by e.
# ⛔ The silent final consonant is the single biggest thing French spelling does
# that its letters do not say, and it is why `romance_katakana` refuses the
# language. c, f, l and r ARE sounded finally -- the traditional CaReFuL set --
# and so is any consonant followed by a mute e.
_FR_SILENT_FINAL = "stdxzpgbn"
# The four nasal series. Each is a VOWEL, not vowel + consonant.
_FR_NASALS = [
    ("ean", "a" + _N),          # Jean is ジャン, not ジェアン
    ("aim", "a" + _N), ("ain", "a" + _N), ("eim", "a" + _N),
    ("ein", "a" + _N), ("oin", "wa" + _N), ("ien", "ya" + _N),
    ("yn", "a" + _N), ("ym", "a" + _N), ("im", "a" + _N), ("in", "a" + _N),
    ("um", "a" + _N), ("un", "a" + _N),
    ("am", "a" + _N), ("em", "a" + _N), ("om", "o" + _N),
    ("an", "a" + _N), ("en", "a" + _N), ("on", "o" + _N),
]
# Vowel digraphs, longest first. None is the sum of its letters.
_FR_VOWELS = [("eau", "o"), ("œu", "u"), ("eu", "u"), ("au", "o"),
              ("ou", "u"), ("oi", "wa"), ("ai", "e"), ("ei", "e"),
              ("œ", "e")]
# ⚠ `ay`/`ey` are a digraph only when NOTHING follows them: in `Hayange` the y
# is the onset of the next syllable and folding it to e gave アンジュ, losing
# the first syllable outright.
_FR_AY = re.compile(r"[ae]y(?![aeiou])")
_FR_ACCENTS = {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a",
               "î": "i", "ï": "i", "ô": "o", "ù": "u", "û": "u", "ü": "u",
               "ÿ": "i"}
_FR_SOFT = [("qu", "k"), ("gu", "g"), ("ch", _CH), ("gn", _NY), ("ph", "f"),
            ("th", "t"),
            ("ce", "se"), ("ci", "si"), ("cy", "si"), ("ç", "s"),
            ("ge", "je"), ("gi", "ji"), ("gy", "ji"),
            ("c", "k"), ("h", "")]
_FR_ILL = re.compile(r"([aeiou])ill")
_FR_S_VOICED = re.compile(r"(?<=[aeiouy])s(?=[aeiouy])")
_FR_DOUBLE = re.compile(r"([bcdfgklmnprstvz])\1")


def _pre_french(word):
    """Everything French, in the one order that works.

    ⚠ The order IS the design, and three of its steps were wrong before the
    first sample was read:

      * **Soft c/g before the mute e is dropped.** Softness is caused by the
        very letter the mute-e rule deletes. `Vincent` came out ヴァンク because
        `ce` had already become a bare c by the time the c rule ran; `Hayange`
        came out エア because its -ge had lost its e.
      * **The mute e before the accents are folded.** `é` is not mute, and
        folding first made `Pitié` and `Nativité` end in a droppable e.
      * **The nasal ン on a sentinel.** A nasal is a vowel, and its n looked
        exactly like a silent final consonant to the pass that follows.
    """
    w = unicodedata.normalize("NFC", word).lower()
    # ⛔ SOFTNESS FIRST. It is caused by the very letter the mute-e rule
    # deletes: `Hayange` lost the e of its -ge and came out エアン instead of
    # アヤンジュ, `Vincent` lost the e of its -ce and came out ヴァンク.
    for a, b in _FR_SOFT:
        w = w.replace(a, b)
    # -er and -ez are /e/, and this runs AFTER the soft rules: the g of
    # `Boulanger` is soft because of that e, and folding first gave ブランゲ.
    if len(w) > 3 and (w.endswith("er") or w.endswith("ez")):
        w = w[:-2] + "é"
    # A final x is silent (-eux is /ø/), and must go before `x -> ks`, which
    # would otherwise leave a k the silent-final pass cannot remove.
    if w.endswith("x") and len(w) > 2:
        w = w[:-1]
    w = w.replace("x", "ks")
    # The mute e, which is also what makes the consonant before it SOUND, so it
    # is parked rather than deleted. ⛔ Checked against the UNFOLDED string: `é`
    # is not mute.
    for tail in ("es", "e"):
        if w.endswith(tail) and len(w) > len(tail) + 1:
            w = w[: -len(tail)] + _E
            break
    w = _FR_ILL.sub(r"\1y", w)
    w = w.replace("ss", _Z + _Z)
    w = _FR_S_VOICED.sub("z", w)
    w = w.replace(_Z + _Z, "s")
    w = "".join(_FR_ACCENTS.get(c, c) for c in w)
    for a, b in _FR_VOWELS:
        w = w.replace(a, b)
    w = _FR_AY.sub("e", w)
    # A nasal only nasalises before a consonant or at the end of the word;
    # `une` and `ami` are not nasal.
    out, i = [], 0
    while i < len(w):
        for a, b in _FR_NASALS:
            # ⚠ Not nasal before a vowel (`une`, `ami`), before the mute-e
            # sentinel (`Dame` is ダム), or before a DOUBLED n/m -- `-ienne` is
            # /jɛn/ and Étienne came out エトヤン.
            if w.startswith(a, i) and (
                    i + len(a) >= len(w)
                    or (w[i + len(a)] not in "aeiouy" + _E
                        and not (a[-1] in "nm" and w[i + len(a)] in "nm"))):
                out.append(b)
                i += len(a)
                break
        else:
            out.append(w[i])
            i += 1
    w = "".join(out)
    while w and w[-1] in _FR_SILENT_FINAL:
        w = w[:-1]
    w = w.replace(_E, "")
    # French writes double consonants and pronounces one: Chapelle シャペル,
    # Villa ヴィラ. Read letter-wise they came back サペルル and ヴィルラ.
    return _FR_DOUBLE.sub(r"\1", w)


# ----------------------------------------------------------------- Russian
_RU_SOFT = re.compile(r"['’ʹʺ]")
# `-sky`, `-skiy`, `-skii` are all the adjective ending -ский, which Japanese
# writes long: Preobrazhensky プレオブラジェンスキー.
_RU_SKY = re.compile(r"sk(?:iy|ii|y|i)$")


def _pre_russian(word):
    w = unicodedata.normalize("NFC", word).lower()
    w = _RU_SOFT.sub("", w)
    w = _RU_SKY.sub("ski" + _CHOONPU, w)
    return w


# ------------------------------------------------------------------ Dutch
# Added 2026-09-20 on Emma's "All four — nl, sv, no, da", asked with the
# measurement in front of her: of the 1,119 long-tail religious buildings with no
# family, 492 are in the local language and **304 of those are Dutch** — the
# single biggest block left.
#
# ⛔ THE COMPOUND IS THE CORPUS, and it is why this family is tractable.
# `kerk` appears in **232 of the 304** labels, almost always glued to the end of
# a name: Bonifatiuskerk, Fonteinkerk, Zeemanskerk. Dutch compounds are written
# solid, so a letter-wise reader walks straight across the seam. Splitting the
# type word off FIRST is not a convenience — it is what keeps the two halves'
# phonology apart, and it is the same move the Swedish family will need for
# `kyrka` (68 of 84) and the Nordic ones for `kirke`.
_NL_TYPE = re.compile(r"(kerk(?:je|en)?|kapel|klooster|synagoge|basiliek|"
                      r"kathedraal|moskee|tempel)$")
# Trema. Dutch ë ï ü ö do not change the vowel — they mark that it starts a new
# syllable rather than joining the one before (België, ruïne). The syllable break
# is already implied by reading the vowels separately, so the mark just goes.
# ⛔ The TREMA only — not the acute or the grave. Folding é to e let `Pitié`
# through the foreign-letter gate and this family read it as ピティー, which
# is the exact confident-wrong failure the module docstring exists to warn
# about. Measured: **0** of the 304 Netherlands labels carry an acute or a
# grave, so refusing them costs nothing and buys the French refusal back.
_NL_TREMA = {"ë": "e", "ï": "i", "ü": "u", "ö": "o"}
# ⚠ Word-final `-sch` is a fossil spelling pronounced /s/: Bosch is ボス, which
# is why Huis ten Bosch is ハウステンボス and not ハウステンボスフ. Elsewhere
# `sch` is /sx/, two sounds — Scheveningen スヘフェニンゲン.
_NL_FINAL_SCH = re.compile(r"sch(?=$|[^aeiou])")
# ⛔ `-cht` is everywhere in Dutch placenames — Utrecht, Dordrecht, Sliedrecht,
# Maastricht — and the fricative takes the ヒ column there, not フ: Utrecht is
# ユトレヒト and Maastricht マーストリヒト. Left to the grid's bare-h default it
# came back ウトレフト and マーストリフト.
_NL_CHT = re.compile(r"cht")
# ⛔ `sch` is s + the fricative, TWO sounds, and writing it as a bare `s` next to
# an `h` is not enough: the kana grid reads `sh` as one consonant, so
# Scheveningen came back シェフェニンゲン. It is スヘフェニンゲン. Forcing the
# ス explicitly is what keeps the two apart.
_NL_SCH = re.compile(r"sch")
# Dutch doubles a consonant to mark the vowel before it short. For the obstruents
# that is the ッ `_GEMINATES` writes (Bakker バッケル); for l/m/n/r there is no
# geminate at all and the pair is one consonant — Willem is ウィレム, and left
# alone it came back ウィルレム.
_NL_COLLAPSE = re.compile(r"([lmnr])\1")
# ⚠ `ieuw` is not i + eu + w. It is /iu/ and Japanese has written it ニュー since
# Nieuw Amsterdam: nieuwe -> ニューウェ. Read letter-wise, with `eu` winning over
# `ie`, it came back ニウーウェ.
_NL_IEUW = re.compile(r"ieuw")


def _pre_dutch(word):
    """Trema, the final -sch fossil, and the digraph vowels.

    ⚠ Dutch spells its long vowels doubled (aa ee oo uu), and `_DOUBLE_VOWEL`
    below already turns any doubled vowel into vowel + ー. So they are NOT in the
    table: adding them would have written the ー twice.
    """
    w = unicodedata.normalize("NFC", word).lower()
    for a, b in _NL_TREMA.items():
        w = w.replace(a, b)
    w = _NL_FINAL_SCH.sub("s", w)
    w = _NL_IEUW.sub("yu" + _CHOONPU + "w", w)
    w = _NL_CHT.sub(_H + "it", w)
    w = _NL_SCH.sub("su" + _H, w)
    w = _NL_COLLAPSE.sub(r"\1", w)
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
# Slavic really does cluster: `Wszystkich` is w-sz-yst-, `Świętych` is św-.
# ⚠ Dutch takes 3 for the same reason German does — `schr-` (Schrijver),
# `str-` (Struisvogel), `spr-`. It is not 4: `sch` is already two sounds by the
# time this runs, s + the h-row fricative.
_MAX_ONSET = {"tr": 1, "ms": 2, "bs": 3, "de": 3, "pl": 3, "cs": 3,
              "fr": 3, "ru": 3, "nl": 3}

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
    if rules == "pl":
        w = _pre_polish(w)
    if rules == "cs":
        w = _pre_czech(w)
    if rules == "fr":
        w = _pre_french(w)
    if rules == "ru":
        w = _pre_russian(w)
    if rules == "nl":
        w = _pre_dutch(w)
    for a, b in _RULES[rules]:
        w = w.replace(a, b)
    if rules == "ms":
        w = _NG.sub("n", w)
    w = _Y_VOWEL.sub("i", w)
    w = w.replace(_NY, "ny")
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
    bare_yoon = dict(_BARE_YOON, **_BARE_YOON_BY_RULES.get(rules, {}))
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
                    out.append(bare_yoon.get(cons, _YOON[cons][2]))
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
    # Slavic Latin, added 2026-09-19 with the other four families.
    "Q36": "pl",    # Poland
    "Q213": "cs",   # Czechia
    "Q214": "cs",   # Slovakia
    # French-speaking, and romanised East Slavic. Added 2026-09-19 on Emma's
    # "All of them, French included".
    "Q142": "fr",   # France
    "Q31": "fr",    # Belgium
    "Q16": "fr",    # Canada — the refused labels are all Quebec parishes
    "Q32": "fr",    # Luxembourg
    "Q159": "ru",   # Russia
    "Q212": "ru",   # Ukraine
    "Q184": "ru",   # Belarus
    # Dutch. Added 2026-09-20 on Emma's "All four — nl, sv, no, da", the first
    # of the four and 304 of the 492 native-language long-tail labels.
    # ⚠ Belgium is already "fr" above and stays there: `COUNTRY_RULES` is one
    # family per country, and the Belgian labels in this corpus are French. The
    # same one-family limit that leaves 5 French labels in Switzerland refused
    # rather than mis-read — a refusal is the correct outcome, not a gap.
    "Q55": "nl",    # Netherlands
}


def rules_for_country(qid):
    """Which family an item's P17 implies, or None to refuse."""
    return COUNTRY_RULES.get(qid)
