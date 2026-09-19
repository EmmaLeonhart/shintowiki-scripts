#!/usr/bin/env python3
"""
religious_building_morphemes.py
===============================
The tables and the parser behind religious-building labels in ja/zh/ko. Pure
logic, no network, so it can be tested without touching Wikidata.

**Full write-up:** `docs/script-rationale/religious_building_morphemes_2026-09.md` — the slots,
every table, the parse order, why the place is mandatory, the three Romance rule sets, and the
register choices.

**Why a morpheme table and not per-item translation.** Emma, 2026-09-17:
*"We look at common words and morphemes across all of the things lol."* Measured
over all 22,548 stage-1 labels, that is the right read: **62.3% are a known frame
plus at most ONE unknown token**, using only a top-200 word vocabulary, and the
frame is tiny and concentrated —

    of 30.5%   de 23.4%   Church 22.7%   in 17.9%   San 15.5%
    St 11.7%   Saint 8.8%  Santa 7.6%    Kirche 5.3%  Chapel 4.8%

German also glues the type on: `kirche` appears in 2,521 labels (11.2%),
`kapelle` in 1,226, `kapel` in 1,289 — so the type must be strippable as a
compound tail, not only as a separate word.

**The TYPE never comes from the label.** It comes from the item's `P31`, which
stage 1 already queried by and then threw away. That is what makes this tractable
across a corpus where two thirds of the labels carry no English type word at all.

⛔ **Category-shaped labels are refused, not translated.** The stage-1 corpus is
Commons *category* names, and some of those are administrative groupings rather
than buildings: ~418 are "Cultural heritage monuments in X", 295 carry a PLURAL
"Synagogues", and there are estates and districts in there too. Translating those
produces a label for a thing that is not the item. Emma, 2026-09-17: filter them
out of stage 2.
"""

import re
import unicodedata

# --------------------------------------------------------------------------
# Types, keyed by the P31 QID. The value is the type word per language.
# --------------------------------------------------------------------------
TYPES = {
    "Q16970":   {"en": "Church",     "ja": "教会",   "zh": "教堂",   "ko": "교회"},
    "Q317557":  {"en": "Church",     "ja": "教会",   "zh": "教堂",   "ko": "교회"},
    "Q2977":    {"en": "Cathedral",  "ja": "大聖堂", "zh": "主教座堂", "ko": "대성당"},
    "Q108325":  {"en": "Chapel",     "ja": "礼拝堂", "zh": "礼拜堂", "ko": "예배당"},
    "Q32815":   {"en": "Mosque",     "ja": "モスク", "zh": "清真寺", "ko": "모스크"},
    "Q34627":   {"en": "Synagogue",  "ja": "シナゴーグ", "zh": "犹太会堂", "ko": "시나고그"},
    "Q160742":  {"en": "Abbey",      "ja": "修道院", "zh": "修道院", "ko": "수도원"},
    "Q44613":   {"en": "Monastery",  "ja": "修道院", "zh": "修道院", "ko": "수도원"},
    "Q163687":  {"en": "Basilica",   "ja": "バシリカ", "zh": "宗座圣殿", "ko": "바실리카"},

    # ── The temple family (2026-09-18) ──────────────────────────────────────────
    # Emma: "Temples that aren't Japanese go in the 10%." Selected by
    # generate_religious_building_labels.TEMPLE_CLASSES, which excludes P17=Japan —
    # a Japanese Buddhist temple is Shinto and belongs to the 90% pipeline.
    #
    # Transliterated, not translated, which is what the table already does: モスク and
    # シナゴーグ above are loanwords, not 礼拝所. So a wat stays a wat and does not
    # collapse into 寺院, and the classes Wikidata keeps apart stay apart.
    "Q44539":   {"en": "Temple",     "ja": "神殿",   "zh": "神殿",   "ko": "신전"},
    "Q5393308": {"en": "Temple",     "ja": "仏教寺院", "zh": "佛寺",   "ko": "불교 사원"},
    "Q842402":  {"en": "Temple",     "ja": "ヒンドゥー教寺院", "zh": "印度教寺廟", "ko": "힌두교 사원"},
    "Q337986":  {"en": "Gurdwara",   "ja": "グルドワーラー", "zh": "謁師所", "ko": "구르드와라"},
    "Q2613100": {"en": "Temple",     "ja": "ジャイナ教寺院", "zh": "耆那教寺廟", "ko": "자이나교 사원"},
    "Q427287":  {"en": "Wat",        "ja": "ワット", "zh": "瓦寺",   "ko": "왓"},
    "Q199451":  {"en": "Pagoda",     "ja": "仏塔",   "zh": "塔",     "ko": "탑"},
    "Q180987":  {"en": "Stupa",      "ja": "仏塔",   "zh": "佛塔",   "ko": "탑"},
    "Q1151612": {"en": "Temple",     "ja": "道観",   "zh": "道觀",   "ko": "도관"},
    "Q618618":  {"en": "Temple",     "ja": "孔子廟", "zh": "孔廟",   "ko": "공자묘"},
    "Q2680845": {"en": "Temple",     "ja": "廟",     "zh": "廟",     "ko": "묘"},
    "Q115278":  {"en": "Fire Temple", "ja": "拝火神殿", "zh": "拜火廟", "ko": "배화교 사원"},
}

# --------------------------------------------------------------------------
# Frame morphemes: the recurring non-name words. Stripped to find the name, and
# for the connective ones, simply dropped — ja/zh/ko do not use them.
#
# Every entry here was taken from the measured frequency list, not invented.
# --------------------------------------------------------------------------
# Type words as they appear IN labels, in any of the source languages. Used only
# to strip; the emitted type comes from P31.
TYPE_WORDS = {
    "church", "churches", "kirche", "kirke", "kyrka", "kerk", "chiesa",
    "iglesia", "igreja", "église", "eglise", "chapel", "chapelle", "kapelle",
    "kapel", "cappella", "capilla", "capela", "ermita", "kaple", "kostel",
    "kościół", "kosciol", "cerkiew", "crkva", "templom", "biserica", "dom",
    "münster", "munster", "kathedrale", "cathedral", "catedral", "cattedrale",
    "basilika", "basilica", "synagogue", "synagoge", "sinagoga", "mosque",
    "moschee", "mezquita", "kloster", "monastery", "abbey", "abbaye",
    "tempel", "temple", "oratorio", "oratory", "pfarrkirche", "stadtkirche",
    "dorfkirche", "klosterkirche", "wallfahrtskirche", "evangelische",
    "evangelisch", "katholische", "reformierte", "parish",
    # Denominations and building modifiers, measured: neuapostolische 150,
    # friedhofs 57, lutheran 47. These qualify the building, they do not name it.
    "neuapostolische", "neuapostolisch", "lutherische", "lutheran", "lutherisch",
    "friedhofskapelle", "friedhofs", "friedhofskirche", "cemetery", "orthodox",
    "orthodoxe", "anglican", "methodist", "baptist_church", "chiesetta",
    "pfarrkirchlein", "kirchlein", "bethaus", "betsaal",
    # German compound heads that describe WHERE or WHOSE, not who it is for:
    # Wegkapelle (wayside), Hofkapelle (farm), Ortskapelle (village),
    # Schlosskapelle (castle), plus more denominations.
    "weg", "wegkapelle", "hof", "hofkapelle", "orts", "ortskapelle",
    "schloss", "schlosskapelle", "burgkapelle", "burg", "friedhof",
    "protestantische", "protestantisch", "hervormde", "evangelical",
    "lutherkirche", "luther", "templo", "iglesia_parroquial",
    # ⭐ Measured 2026-09-19, once the transliteration fallback started READING
    # whatever it found in the name slot: these were being read as dedicatees.
    # `Església` is Catalan for church (18), `gereja` Indonesian (14),
    # `hermitage` the English of `ermita` (18), and `convento` / `parroquia` /
    # `santuario` / `ermida` the same kind of word. A type word read as a name
    # is the failure this whole module is built to avoid.
    "església", "esglesia", "gereja", "hermitage", "convento", "convent",
    "abbazia", "badia", "abadia", "abadía", "abbaziale",
    "parroquia", "parróquia", "paróquia", "ermida", "santuario", "santuário",
    "santuari",
}

# Connectives and articles — dropped entirely.
STOPWORDS = {
    "of", "the", "in", "de", "da", "do", "di", "del", "della", "dei", "delle",
    "des", "du", "la", "le", "les", "el", "los", "las", "and", "e", "y", "et",
    "und", "zu", "zum", "zur", "am", "an", "auf", "im", "van", "von", "der",
    "die", "das", "a", "o", "al", "all", "alla", "ai", "i",
    # Modifiers, measured: paroquial 158, filial 54, old 73, new 61.
    "paroquial", "parroquial", "filial", "old", "new", "alte", "alten", "neue",
    "neuen", "former", "ancienne", "vecchia", "nuova",
    # ⛔ Fragments the apostrophe split produces. Splitting on ' was needed for
    # Sant'Anna, and it also turns "St. Nicholas's" into [nicholas, s] and
    # "d'Agnane" into [d, agnane]. Measured: s 56, d 46 -- the two biggest
    # "unknown names" in the corpus were not names at all.
    "s", "d", "l", "dell", "nell", "sull", "all", "quell",
    # Roles, not names: "San Pietro Apostolo" is Peter (apostolo 48 in the corpus).
    "apostolo", "apostle", "apostel", "apostol", "evangelista", "evangelist",
    "martire", "martyr", "martir", "confessor", "bispo", "obispo", "vescovo",
    "bishop", "papa", "pope", "abad", "abbot", "the", "athonite",
    "prophet", "profeta", "sts", "ss", "at", "casa", "misericordia",
    "misericórdia", "reformed", "nederlands", "hervormd", "borromeo",
    "kolbe", "tours", "loyola", "sales",
}

# Saint / dedication markers — recognised so the following token is read as a
# dedicatee, and rendered with the language's own saint marker.
SAINT_MARKERS = {
    "st", "st.", "saint", "sainte", "san", "santa", "santo", "sant", "sankt",
    "hl", "hl.", "heilig", "heilige", "heiligen", "sao", "são", "sveti",
    "svaty", "svatý", "święty", "swiety", "szent", "sfantul", "sfântul",
    # Measured misses from the corpus scan, 2026-09-17. `sint` is the Dutch
    # marker and was absent entirely; `santi`/`saints`/`santos` are the PLURAL
    # marker, which is a marker and not a dedicatee.
    "sint", "santi", "saints", "santos", "santas", "ss", "ss.", "sant'",
    "szentharomsag", "sv", "sv.",
}

SAINT_PREFIX = {"ja": "聖", "zh": "圣", "ko": "성"}

# --------------------------------------------------------------------------
# The mosque family — a separate slot system, because the dedication slot is
# not a saint (Emma, 2026-09-18: "translate the generic, transliterate the
# name", with `Old Mosque` → 旧モスク, `Upper Mosque` → 上モスク, `Omer Mosque`
# → オメル・モスク).
# --------------------------------------------------------------------------
# `dedication()` is a Christian saint vocabulary and there is nothing in it a
# mosque can match, so all 245 mosques in the corpus produced ZERO labels. The
# shapes, measured 2026-09-19 over those 245:
#
#     bare type word only      77   "Mosque", "Džamija", "Masjid"
#     generic modifier only    18   "Old Mosque", "Nova Džamija", "Merkez-Moschee"
#     carries a name          137   "Omer Mosque", "Surau Bulian"
#     not named as a mosque    10   "Nablus", "WikiBanua 2.0", "Donauwörther Straße 165"
#     category-shaped           3   "Mosques in Dubai"
#
# The first two buckets render in all three languages, because a translation of
# `old` is a translation and not a reading. The third is ja-only, for the same
# reason `romance_katakana` is — see `plain_latin_katakana`.
MOSQUE_P31 = {"Q32815"}

# Words that just mean "mosque", in every source language the corpus uses. Kept
# OUT of the global TYPE_WORDS on purpose: that set is consulted for all 22,548
# items and `_strip_compound_type` matches it as a suffix, so adding `cami` or
# `mosk` there would change how 18,148 church labels parse for no gain.
MOSQUE_TYPE_WORDS = {
    "mosque", "mosques", "moschee", "moske", "mosk", "moské", "moskee",
    "mosquee", "mosquée", "mezquita", "meczet",
    "džamija", "dzamija", "džamije", "dzamija", "xhamia", "xhamija",
    "cami", "camii", "camisi", "camia", "mescit", "mescidi", "məscidi",
    "masjid", "masjids", "mesjid", "musalla", "musholla", "moschea",
}

# ⛔ A *surau* is not a mosque (Emma, 2026-09-19): a small Malay/Minangkabau
# prayer hall, filed under P31 mosque because Wikidata has no closer class. She
# chose the loanword over folding it into モスク, which is the same call the
# TYPES table already makes for ワット and グルドワーラー — the classes Wikidata
# keeps apart stay apart. 9 items.
#
# ⚠ The zh cell is MINE, not hers: 苏劳 is a Xinhua-style transliteration, since
# Chinese has no settled term and the alternative (祈祷室) is a translation,
# which is the option she did not pick.
SURAU_WORDS = {"surau", "suraus"}
SURAU_TYPE = {"ja": "スラウ", "zh": "苏劳", "ko": "수라우"}

# A *jāmi'* / *juma* mosque is the congregational one — the Friday mosque — as
# against a neighbourhood *masjid*. Emma, 2026-09-19, chose to translate the
# distinction rather than strip it. 18 items.
FRIDAY_WORDS = {
    "jami", "jame", "jami'", "jamik", "jamig", "jamia", "juma", "jumah",
    "jama", "djami", "djamik", "cuma", "cümə", "cume", "jame'", "jum'a",
}
FRIDAY_MODIFIER = {"ja": "金曜", "zh": "聚礼", "ko": "금요 "}

# Generic modifiers: translated, never transliterated. Every key was taken from
# the measured token list over the 245, not invented — the Slavic, Turkish and
# Malay forms are there because the labels are not all English.
#
# ⚠ The ko column is NATIVE Korean (옛/새/위/아래/큰), Emma's choice on
# 2026-09-19 over the Sino-Korean 구/신/상/하/대 that would have paralleled the
# ja column one-for-one. It is spaced; ja and zh are not.
GENERIC_MODIFIERS = {
    "old":     {"ja": "旧",   "zh": "旧",   "ko": "옛 "},
    "new":     {"ja": "新",   "zh": "新",   "ko": "새 "},
    "great":   {"ja": "大",   "zh": "大",   "ko": "큰 "},
    "upper":   {"ja": "上",   "zh": "上",   "ko": "위 "},
    "lower":   {"ja": "下",   "zh": "下",   "ko": "아래 "},
    "middle":  {"ja": "中",   "zh": "中",   "ko": "가운데 "},
    "central": {"ja": "中央", "zh": "中央", "ko": "중앙 "},
}

# Source spellings → the modifier they are. Measured spellings only.
MODIFIER_ALIASES = {
    "old": "old", "stara": "old", "stari": "old", "staro": "old",
    "eski": "old", "alte": "old", "alten": "old", "ancienne": "old",
    "vieux": "old", "usang": "old", "tuo": "old", "lama": "old",
    "new": "new", "nova": "new", "novi": "new", "novo": "new",
    "yeni": "new", "neue": "new", "neu": "new", "nouvelle": "new",
    "baru": "new",
    "great": "great", "grand": "great", "grande": "great", "gran": "great",
    "büyük": "great", "buyuk": "great", "kebir": "great", "velika": "great",
    "agung": "great", "raya": "great", "besar": "great",
    "upper": "upper", "yukarı": "upper", "yukari": "upper",
    "gornja": "upper", "gorna": "upper", "atas": "upper",
    "lower": "lower", "aşağı": "lower", "asagi": "lower", "ashaghi": "lower",
    "donja": "lower", "dolna": "lower", "bawah": "lower",
    "middle": "middle", "orta": "middle", "srednja": "middle",
    "sredna": "middle", "tengah": "middle",
    "central": "central", "merkez": "central", "centrale": "central",
    "centralna": "central", "pusat": "central",
}

# Ordinal disambiguators on an otherwise identical name — "Nova Džamija I" beside
# "Nova Džamija II". They say nothing about the building, and rendering them as a
# transliterated name gave イイ. Dropped; the duplicate guard then decides which
# of the colliding labels survives, which is what it is for.
_ROMAN = re.compile(r"^[ivx]+$")

# ⛔ An ENGLISH word in the name slot means the label is English, and none of the
# three orthographies `plain_latin_katakana` reads is English. Reading one with
# Malay rules gave ブルネイ・インテルナティオナル・アイルポルト・モスク for
# `Brunei International Airport Mosque` — confident, systematic and wrong, the
# same failure `romance_katakana` had when it read French as Italian. The
# transliterator cannot detect this (the letters are all legal), so the parser
# refuses the item instead.
ENGLISH_MARKERS = {
    "international", "airport", "police", "village", "station", "kiosk",
    "prophet", "queen", "tiled", "complex", "monastery", "cemetery", "city",
    "town", "district", "street", "north", "south", "east", "west", "main",
    "royal", "national", "memorial", "university", "hospital", "market",
}

# ⚠ THE zh COLUMN IS CATHOLIC REGISTER, AND THAT IS A CHOICE (audited 2026-09-18)
#
# Chinese has two parallel Christian vocabularies and they disagree on almost
# every name. Mine are consistently the CATHOLIC forms; Wikidata's own labels are
# frequently the Protestant or transliterated ones:
#
#     saint        mine (Catholic)   Wikidata      register
#     Michael      弥额尔             米迦勒         Protestant
#     Matthew      玛窦               馬太           Protestant
#     Elijah       厄里亚             以利亞         Protestant
#     Andrew       安德肋             安得烈         Protestant
#     Christopher  圣基道             聖克里斯多福    transliteration
#
# This is not an error either way, and Catholic register is the right one here:
# these are overwhelmingly Catholic parish churches, chapels and basilicas. It
# is written down because it was an unflagged decision, and because a future
# audit against Wikidata labels will "find" all of these again.
#
# ⚠ The ko column was audited too (2026-09-18), after I twice claimed it could
# not be. Wikidata has a ko label for **45%** of these concepts, not "mostly
# absent" as I reported without looking. 17 are identical to mine; of the 28 that
# differ, all but one are a bad item match, a disambiguator a dedication does not
# want, or a case where MINE is the current Korean Catholic term and Wikidata's
# is the older one -- 주님 탄생 예고 for the Annunciation is the post-2011 form,
# 성모 영보 the pre-2011 one. The single real fix was Mount Carmel, where 산
# belongs in the title.
#
# ⚠ The ja column was audited the same way: of the 58 entries where Wikidata has
# a ja label, 19 are IDENTICAL to mine and most of the rest differ only by a
# disambiguator (アレクサンドリアのカタリナ vs カタリナ) or a 聖 prefix this module
# adds separately. Three were genuinely wrong and are corrected above -- each was
# a literal translation where Japanese Catholicism has a settled term
# (絶えざる御助けの聖母, 扶助者聖マリア, 慈悲の聖母).
#
# --------------------------------------------------------------------------
# Known dedicatees. The measured list — Maria/María 1,393, Mary 341,
# Nicholas 314, Pedro 310, Michael 271 — plus the obvious companions. Only
# names in here are rendered in-script; anything else is a transliteration
# decision, which is the caller's to make.
# --------------------------------------------------------------------------
NAMES = {
    "maria":     {"ja": "マリア", "zh": "玛利亚", "ko": "마리아"},
    "maría":     {"ja": "マリア", "zh": "玛利亚", "ko": "마리아"},
    "mary":      {"ja": "マリア", "zh": "玛利亚", "ko": "마리아"},
    "marien":    {"ja": "マリア", "zh": "玛利亚", "ko": "마리아"},
    "peter":     {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "petri":     {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "pietro":    {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "pedro":     {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "pierre":    {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "paul":      {"ja": "パウロ", "zh": "保罗",   "ko": "바울로"},
    "pauli":     {"ja": "パウロ", "zh": "保罗",   "ko": "바울로"},
    "paolo":     {"ja": "パウロ", "zh": "保罗",   "ko": "바울로"},
    "pablo":     {"ja": "パウロ", "zh": "保罗",   "ko": "바울로"},
    "john":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "johannes":  {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "giovanni":  {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "juan":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "joão":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "jean":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "nicholas":  {"ja": "ニコラオス", "zh": "尼古拉", "ko": "니콜라오"},
    "nikolaus":  {"ja": "ニコラオス", "zh": "尼古拉", "ko": "니콜라오"},
    "nicola":    {"ja": "ニコラオス", "zh": "尼古拉", "ko": "니콜라오"},
    "nicolás":   {"ja": "ニコラオス", "zh": "尼古拉", "ko": "니콜라오"},
    "michael":   {"ja": "ミカエル", "zh": "弥额尔", "ko": "미카엘"},
    "michele":   {"ja": "ミカエル", "zh": "弥额尔", "ko": "미카엘"},
    "miguel":    {"ja": "ミカエル", "zh": "弥额尔", "ko": "미카엘"},
    "george":    {"ja": "ゲオルギオス", "zh": "乔治", "ko": "게오르기오스"},
    "georg":     {"ja": "ゲオルギオス", "zh": "乔治", "ko": "게오르기오스"},
    "giorgio":   {"ja": "ゲオルギオス", "zh": "乔治", "ko": "게오르기오스"},
    "andrew":    {"ja": "アンデレ", "zh": "安德肋", "ko": "안드레아"},
    "andreas":   {"ja": "アンデレ", "zh": "安德肋", "ko": "안드레아"},
    "jacob":     {"ja": "ヤコブ", "zh": "雅各",   "ko": "야고보"},
    "james":     {"ja": "ヤコブ", "zh": "雅各",   "ko": "야고보"},
    "jakob":     {"ja": "ヤコブ", "zh": "雅各",   "ko": "야고보"},
    "giacomo":   {"ja": "ヤコブ", "zh": "雅各",   "ko": "야고보"},
    "martin":    {"ja": "マルティヌス", "zh": "玛尔定", "ko": "마르티노"},
    "martino":   {"ja": "マルティヌス", "zh": "玛尔定", "ko": "마르티노"},
    "laurentius": {"ja": "ラウレンティウス", "zh": "老楞佐", "ko": "라우렌시오"},
    "lawrence":  {"ja": "ラウレンティウス", "zh": "老楞佐", "ko": "라우렌시오"},
    "anna":      {"ja": "アンナ", "zh": "亚纳",   "ko": "안나"},
    "anne":      {"ja": "アンナ", "zh": "亚纳",   "ko": "안나"},
    "joseph":    {"ja": "ヨセフ", "zh": "若瑟",   "ko": "요셉"},
    "josef":     {"ja": "ヨセフ", "zh": "若瑟",   "ko": "요셉"},
    "giuseppe":  {"ja": "ヨセフ", "zh": "若瑟",   "ko": "요셉"},
    "josé":      {"ja": "ヨセフ", "zh": "若瑟",   "ko": "요셉"},
    # --- widened 2026-09-17 from the measured unknown-token list ---
    # Galician and Portuguese forms are heavily represented (the corpus has a
    # large Galician slice: xoán 184, martiño 160, estevo 81, mamede 69).
    "xoán":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "xoan":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "joan":      {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "battista":  {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "baptist":   {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "bautista":  {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "martiño":   {"ja": "マルティヌス", "zh": "玛尔定", "ko": "마르티노"},
    "martinho":  {"ja": "マルティヌス", "zh": "玛尔定", "ko": "마르티노"},
    "estevo":    {"ja": "ステファノ", "zh": "斯德望", "ko": "스테파노"},
    "stephen":   {"ja": "ステファノ", "zh": "斯德望", "ko": "스테파노"},
    "stephan":   {"ja": "ステファノ", "zh": "斯德望", "ko": "스테파노"},
    "stefano":   {"ja": "ステファノ", "zh": "斯德望", "ko": "스테파노"},
    "esteban":   {"ja": "ステファノ", "zh": "斯德望", "ko": "스테파노"},
    "mamede":    {"ja": "マメス", "zh": "玛默德", "ko": "마메스"},
    "lourenzo":  {"ja": "ラウレンティウス", "zh": "老楞佐", "ko": "라우렌시오"},
    "lorenzo":   {"ja": "ラウレンティウス", "zh": "老楞佐", "ko": "라우렌시오"},
    "laurentiuskirche": {"ja": "ラウレンティウス", "zh": "老楞佐", "ko": "라우렌시오"},
    "cristovo":  {"ja": "クリストフォロス", "zh": "圣基道", "ko": "크리스토포로"},
    "christopher": {"ja": "クリストフォロス", "zh": "圣基道", "ko": "크리스토포로"},
    "andré":     {"ja": "アンデレ", "zh": "安德肋", "ko": "안드레아"},
    "andrea":    {"ja": "アンデレ", "zh": "安德肋", "ko": "안드레아"},
    "vicente":   {"ja": "ウィンケンティウス", "zh": "文生", "ko": "빈첸시오"},
    "vincent":   {"ja": "ウィンケンティウス", "zh": "文生", "ko": "빈첸시오"},
    "santiago":  {"ja": "ヤコブ", "zh": "雅各",   "ko": "야고보"},
    "jakobus":   {"ja": "ヤコブ", "zh": "雅各",   "ko": "야고보"},
    "francesco": {"ja": "フランチェスコ", "zh": "方济各", "ko": "프란치스코"},
    "francis":   {"ja": "フランチェスコ", "zh": "方济各", "ko": "프란치스코"},
    "franziskus": {"ja": "フランチェスコ", "zh": "方济各", "ko": "프란치스코"},
    "rocco":     {"ja": "ロクス", "zh": "圣罗格", "ko": "로코"},
    "roque":     {"ja": "ロクス", "zh": "圣罗格", "ko": "로코"},
    "roch":      {"ja": "ロクス", "zh": "圣罗格", "ko": "로코"},
    "antonius":  {"ja": "アントニオ", "zh": "安多尼", "ko": "안토니오"},
    "antonio":   {"ja": "アントニオ", "zh": "安多尼", "ko": "안토니오"},
    "anthony":   {"ja": "アントニオ", "zh": "安多尼", "ko": "안토니오"},
    "stanislaus": {"ja": "スタニスラウス", "zh": "斯坦尼斯劳", "ko": "스타니슬라오"},
    "stanislaw": {"ja": "スタニスラウス", "zh": "斯坦尼斯劳", "ko": "스타니슬라오"},
    "demetrius": {"ja": "デメトリオス", "zh": "德米特里", "ko": "데메트리오"},
    "elijah":    {"ja": "エリヤ", "zh": "厄里亚", "ko": "엘리야"},
    "barbara":   {"ja": "バルバラ", "zh": "巴尔巴拉", "ko": "바르바라"},
    "catherine": {"ja": "カタリナ", "zh": "加大肋纳", "ko": "가타리나"},
    "katharina": {"ja": "カタリナ", "zh": "加大肋纳", "ko": "가타리나"},
    "salvador":  {"ja": "救世主", "zh": "救主",   "ko": "구세주"},
    "salvatore": {"ja": "救世主", "zh": "救主",   "ko": "구세주"},
    "christus":  {"ja": "キリスト", "zh": "基督", "ko": "그리스도"},
    "christi":   {"ja": "キリスト", "zh": "基督", "ko": "그리스도"},
    "mariä":     {"ja": "マリア", "zh": "玛利亚", "ko": "마리아"},
    "mariña":    {"ja": "マリナ", "zh": "玛丽娜", "ko": "마리나"},
    "petka":     {"ja": "パラスケヴィ", "zh": "帕拉斯克娃", "ko": "파라스케바"},
    "archangel": {"ja": "大天使", "zh": "总领天使", "ko": "대천사"},
    "arcangelo": {"ja": "大天使", "zh": "总领天使", "ko": "대천사"},
    # Italian and Catalan forms, from the labels that actually reached Wikidata.
    "caterina":  {"ja": "カタリナ", "zh": "加大肋纳", "ko": "가타리나"},
    "anna":      {"ja": "アンナ", "zh": "亚纳",   "ko": "안나"},
    "isidoro":   {"ja": "イシドロ", "zh": "依西多禄", "ko": "이시도로"},
    "pellegrino": {"ja": "ペレグリヌス", "zh": "培肋格利诺", "ko": "펠레그리노"},
    "maurici":   {"ja": "マウリティウス", "zh": "毛里丘", "ko": "마우리시오"},
    "terenziano": {"ja": "テレンティアヌス", "zh": "德肋左", "ko": "테렌시아노"},
    "innocenti": {"ja": "幼子殉教者", "zh": "诸圣婴孩", "ko": "무죄한 어린이"},
    "teresa":    {"ja": "テレサ", "zh": "德肋撒", "ko": "데레사"},
    "pio":       {"ja": "ピオ", "zh": "碧岳",   "ko": "비오"},
    "bonifatius": {"ja": "ボニファティウス", "zh": "波尼法爵", "ko": "보니파시오"},
    "matthew":   {"ja": "マタイ", "zh": "玛窦",   "ko": "마태오"},
    # --- widened 2026-09-18 from the measured unknown-token frequency list ---
    "bartholomew": {"ja": "バルトロマイ", "zh": "巴尔多禄茂", "ko": "바르톨로메오"},
    "bartholomäus": {"ja": "バルトロマイ", "zh": "巴尔多禄茂", "ko": "바르톨로메오"},
    "bartolomeo": {"ja": "バルトロマイ", "zh": "巴尔多禄茂", "ko": "바르톨로메오"},
    "bartolomeu": {"ja": "バルトロマイ", "zh": "巴尔多禄茂", "ko": "바르톨로메오"},
    "bartolomé": {"ja": "バルトロマイ", "zh": "巴尔多禄茂", "ko": "바르톨로메오"},
    "lucia":     {"ja": "ルチア", "zh": "路济亚", "ko": "루치아"},
    "lucy":      {"ja": "ルチア", "zh": "路济亚", "ko": "루치아"},
    "vitus":     {"ja": "ウィトゥス", "zh": "维托", "ko": "비토"},
    "veit":      {"ja": "ウィトゥス", "zh": "维托", "ko": "비토"},
    "petrus":    {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "paulus":    {"ja": "パウロ", "zh": "保罗",   "ko": "바울로"},
    "stephanus": {"ja": "ステファノ", "zh": "斯德望", "ko": "스테파노"},
    "nepomuk":   {"ja": "ネポムクのヨハネ", "zh": "内波穆克的若望", "ko": "네포무크의 요한"},
    "elisabeth": {"ja": "エリーザベト", "zh": "依撒伯尔", "ko": "엘리사벳"},
    "elizabeth": {"ja": "エリーザベト", "zh": "依撒伯尔", "ko": "엘리사벳"},
    "hedwig":    {"ja": "ヘドヴィヒ", "zh": "海德维希", "ko": "헤드비히"},
    "jadwiga":   {"ja": "ヘドヴィヒ", "zh": "海德维希", "ko": "헤드비히"},
    "leonhard":  {"ja": "レオンハルト", "zh": "良纳", "ko": "레오나르도"},
    "leonard":   {"ja": "レオンハルト", "zh": "良纳", "ko": "레오나르도"},
    "leonardo":  {"ja": "レオンハルト", "zh": "良纳", "ko": "레오나르도"},
    "magdalene": {"ja": "マグダラのマリア", "zh": "抹大拉的玛利亚", "ko": "막달레나 마리아"},
    "magdalena": {"ja": "マグダラのマリア", "zh": "抹大拉的玛利亚", "ko": "막달레나 마리아"},
    "athanasius": {"ja": "アタナシオス", "zh": "亚大纳西", "ko": "아타나시오"},
    "ulrich":    {"ja": "ウルリヒ", "zh": "吾尔利", "ko": "울리히"},
    "mauritius": {"ja": "マウリティウス", "zh": "毛里丘", "ko": "마우리시오"},
    "cristina":  {"ja": "クリスティーナ", "zh": "基利斯汀", "ko": "크리스티나"},
    "christina": {"ja": "クリスティーナ", "zh": "基利斯汀", "ko": "크리스티나"},
    "martín":    {"ja": "マルティヌス", "zh": "玛尔定", "ko": "마르티노"},
    "agatha":    {"ja": "アガタ", "zh": "亚加大", "ko": "아가타"},
    "margaret":  {"ja": "マルガリタ", "zh": "玛加利大", "ko": "마르가리타"},
    "margareta": {"ja": "マルガリタ", "zh": "玛加利大", "ko": "마르가리타"},
    "gallus":    {"ja": "ガルス", "zh": "加卢斯", "ko": "갈루스"},
    "wenceslaus": {"ja": "ヴァーツラフ", "zh": "瓦茨拉夫", "ko": "바츨라프"},
    "adalbert":  {"ja": "アダルベルト", "zh": "圣达德", "ko": "아달베르토"},
    # Galician saints -- the corpus has a large Galician slice
    "baia":      {"ja": "エウラリア", "zh": "欧拉利亚", "ko": "에울랄리아"},
    "eulalia":   {"ja": "エウラリア", "zh": "欧拉利亚", "ko": "에울랄리아"},
    "tomé":      {"ja": "トマス", "zh": "多默",   "ko": "토마스"},
    "paio":      {"ja": "ペラギウス", "zh": "培拉吉", "ko": "펠라기오"},
    "xiao":      {"ja": "ユリアヌス", "zh": "儒略", "ko": "율리아노"},
    "fiz":       {"ja": "フェリクス", "zh": "斐理斯", "ko": "펠릭스"},
    "felix":     {"ja": "フェリクス", "zh": "斐理斯", "ko": "펠릭스"},
    "xurxo":     {"ja": "ゲオルギオス", "zh": "乔治", "ko": "게오르기오스"},
    # --- pass 2, 2026-09-18, again from the measured frequency list ---
    # more Galician: the corpus is 15% gl and this is where the tail lives
    "xulián":    {"ja": "ユリアヌス", "zh": "儒略", "ko": "율리아노"},
    "xián":      {"ja": "ユリアヌス", "zh": "儒略", "ko": "율리아노"},
    "julián":    {"ja": "ユリアヌス", "zh": "儒略", "ko": "율리아노"},
    "bieito":    {"ja": "ベネディクトゥス", "zh": "本笃", "ko": "베네딕토"},
    "benedict":  {"ja": "ベネディクトゥス", "zh": "本笃", "ko": "베네딕토"},
    "benito":    {"ja": "ベネディクトゥス", "zh": "本笃", "ko": "베네딕토"},
    "madanela":  {"ja": "マグダラのマリア", "zh": "抹大拉的玛利亚", "ko": "막달레나 마리아"},
    "santalla":  {"ja": "エウラリア", "zh": "欧拉利亚", "ko": "에울랄리아"},
    "antón":     {"ja": "アントニオ", "zh": "安多尼", "ko": "안토니오"},
    "xosé":      {"ja": "ヨセフ", "zh": "若瑟",   "ko": "요셉"},
    "vicenzo":   {"ja": "ウィンケンティウス", "zh": "文生", "ko": "빈첸시오"},
    "cibrao":    {"ja": "キプリアヌス", "zh": "西彼廉", "ko": "치프리아노"},
    "cyprian":   {"ja": "キプリアヌス", "zh": "西彼廉", "ko": "치프리아노"},
    "andrés":    {"ja": "アンデレ", "zh": "安德肋", "ko": "안드레아"},
    # the Sebastian family -- 81 items across three spellings
    "sebastian": {"ja": "セバスティアヌス", "zh": "圣塞巴斯弟盎", "ko": "세바스티아노"},
    "sebastiano": {"ja": "セバスティアヌス", "zh": "圣塞巴斯弟盎", "ko": "세바스티아노"},
    "sebastián": {"ja": "セバスティアヌス", "zh": "圣塞巴斯弟盎", "ko": "세바스티아노"},
    "sebastião": {"ja": "セバスティアヌス", "zh": "圣塞巴斯弟盎", "ko": "세바스티아노"},
    # German saints
    "hubertus":  {"ja": "フベルトゥス", "zh": "胡伯特", "ko": "후베르토"},
    "florian":   {"ja": "フロリアヌス", "zh": "圣佛罗里安", "ko": "플로리아노"},
    "wendelin":  {"ja": "ヴェンデリン", "zh": "文德林", "ko": "벤델리노"},
    "maximilian": {"ja": "マキシミリアノ", "zh": "国柏", "ko": "막시밀리아노"},
    "johann":    {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "johannis":  {"ja": "ヨハネ", "zh": "约翰",   "ko": "요한"},
    "nikolai":   {"ja": "ニコラオス", "zh": "尼古拉", "ko": "니콜라오"},
    "carlo":     {"ja": "カルロ", "zh": "嘉禄", "ko": "가롤로"},
    "carlos":    {"ja": "カルロ", "zh": "嘉禄", "ko": "가롤로"},
    "quiteria":  {"ja": "キテリア", "zh": "基德利亚", "ko": "퀴테리아"},
    "pedro":     {"ja": "ペトロ", "zh": "彼得",   "ko": "베드로"},
    "thomas":    {"ja": "トマス", "zh": "多默",   "ko": "토마스"},
}

# Multi-token saint names that must be read as ONE dedicatee. Without this,
# "San Giovanni Battista" renders Giovanni AND Battista and comes out as
# 聖ヨハネ洗礼者ヨハネ教会 — John twice. Checked before single tokens.
# ⭐ Spelling variants of saints the table ALREADY names, measured 2026-09-19 over
# the population the transliteration fallback reaches. These are here so ONE saint
# never gets two different Japanese forms — `francesco` was フランチェスコ from the
# table while `francisco`, absent, was read as フランシースコ. That is the table's
# own precedent, which already lists five spellings of Nicholas and eight of John.
#
# ⛔ A saint the table does NOT name is NOT added here. Gregorio, Filippo, Marco,
# Marta, Agostino, Domenico, Biagio, Vittore, Bernardo, Román and the Galician
# saints (Amaro, Breixo, Cibrán, Comba, Santaia, Xillao) are absent, and absent is
# what "no dedication means transliteration" is FOR. Naming them would be a
# per-saint translation call; reading them is the rule Emma gave.
NAMES.update({
    "francisco": NAMES["francesco"], "francisca": NAMES["francesco"],
    "agata": NAMES["agatha"],
    "tommaso": NAMES["thomas"],
    "benedetto": NAMES["benedict"],
    "ana": NAMES["anna"],
    "nicolò": NAMES["nicola"], "niccolò": NAMES["nicola"],
    "margherita": NAMES["margaret"],
    "cristo": NAMES["christus"],
    "vito": NAMES["vitus"],
})

NAME_PHRASES = {
    "giovanni battista": {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "juan bautista":     {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "xoán bautista":     {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "joão batista":      {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "john baptist":      {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "johannes täufer":   {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "pedro pablo":       {"ja": "ペトロとパウロ", "zh": "伯多禄和保禄", "ko": "베드로와 바오로"},
    "peter paul":        {"ja": "ペトロとパウロ", "zh": "伯多禄和保禄", "ko": "베드로와 바오로"},
    "pietro paolo":      {"ja": "ペトロとパウロ", "zh": "伯多禄和保禄", "ko": "베드로와 바오로"},
    # ⛔ Compound saints, or both halves render and the name doubles:
    # "St. John of Nepomuk" came out 聖ヨハネネポムクのヨハネ.
    "john nepomuk":      {"ja": "ネポムクのヨハネ", "zh": "内波穆克的若望", "ko": "네포무크의 요한"},
    "johannes nepomuk":  {"ja": "ネポムクのヨハネ", "zh": "内波穆克的若望", "ko": "네포무크의 요한"},
    "anthony padua":     {"ja": "パドヴァのアントニオ", "zh": "帕多瓦的安多尼", "ko": "파도바의 안토니오"},
    "antonius padua":    {"ja": "パドヴァのアントニオ", "zh": "帕多瓦的安多尼", "ko": "파도바의 안토니오"},
    "antonio padua":     {"ja": "パドヴァのアントニオ", "zh": "帕多瓦的安多尼", "ko": "파도바의 안토니오"},
    "antónio padua":     {"ja": "パドヴァのアントニオ", "zh": "帕多瓦的安多尼", "ko": "파도바의 안토니오"},
    "mary magdalene":    {"ja": "マグダラのマリア", "zh": "抹大拉的玛利亚", "ko": "막달레나 마리아"},
    "francis assisi":    {"ja": "アッシジのフランチェスコ", "zh": "亚西西的方济各", "ko": "아시시의 프란치스코"},
    "francesco assisi":  {"ja": "アッシジのフランチェスコ", "zh": "亚西西的方济各", "ko": "아시시의 프란치스코"},
    "demetrius thessaloniki": {"ja": "テッサロニキのデメトリオス", "zh": "得撒洛尼的德米特里", "ko": "테살로니카의 데메트리오"},
    "anthony padova":    {"ja": "パドヴァのアントニオ", "zh": "帕多瓦的安多尼", "ko": "파도바의 안토니오"},
    "antonio padova":    {"ja": "パドヴァのアントニオ", "zh": "帕多瓦的安多尼", "ko": "파도바의 안토니오"},
    "boris gleb":        {"ja": "ボリスとグレプ", "zh": "鲍里斯和格列布", "ko": "보리스와 글레프"},
    "maria magdalena":   {"ja": "マグダラのマリア", "zh": "抹大拉的玛利亚", "ko": "막달레나 마리아"},
}

# Names that ALREADY contain the saint marker, so the prefix must be supplied
# even though no separate marker token appeared. Santiago = Sant + Iago.
SELF_SAINT = {"santiago", "santiago.", "sanjuan", "sanpedro"}

# Whole dedications that are not a single saint.
DEDICATIONS = {
    "holy trinity":     {"ja": "至聖三者", "zh": "圣三一", "ko": "삼위일체"},
    "holy cross":       {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "holy spirit":      {"ja": "聖霊",     "zh": "圣神",   "ko": "성령"},
    "our lady":         {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "madonna":          {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "assumption":       {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    # --- widened 2026-09-17, measured: nativity 170, transfiguration 78,
    # ascension 75, dormition 66, immaculate 69, annunciation 48 ---
    "nativity":         {"ja": "降誕",     "zh": "圣诞",   "ko": "성탄"},
    "transfiguration":  {"ja": "主の変容", "zh": "主显圣容", "ko": "주님 거룩한 변모"},
    "ascension":        {"ja": "主の昇天", "zh": "耶稣升天", "ko": "예수 승천"},
    "dormition":        {"ja": "生神女就寝", "zh": "圣母安息", "ko": "성모 안식"},
    "annunciation":     {"ja": "受胎告知", "zh": "圣母领报", "ko": "주님 탄생 예고"},
    "visitation":       {"ja": "聖母訪問", "zh": "圣母访亲", "ko": "성모 방문"},
    "intercession":     {"ja": "生神女庇護", "zh": "圣母帡幪", "ko": "성모 보호"},
    "immaculate":       {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    "sacred heart":     {"ja": "イエスの聖心", "zh": "耶稣圣心", "ko": "예수 성심"},
    "heilig kreuz":     {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "theotokos":        {"ja": "生神女",   "zh": "圣母",   "ko": "성모"},
    "notre dame":       {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "nosa señora":      {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "nossa senhora":    {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "nuestra señora":   {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "virxe":            {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    # --- second widening pass, 2026-09-17, from the remaining unknown list ---
    "himmelfahrt":      {"ja": "被昇天",   "zh": "升天",   "ko": "승천"},
    "mariä himmelfahrt": {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    "assunta":          {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    # ⛔ Bare "santissima"/"santissimo" was here and produced 354 wrong labels --
    # 至聖教会, "Most Holy Church", a modifier qualifying nothing. The phrase
    # lookup is substring-based, so "Chiesa della Santissima Trinità" matched the
    # bare modifier and the Trinità was lost. The full phrases are below; an
    # unmatched remainder is now refused, which is the correct outcome.
    "santissima trinità":   {"ja": "至聖三者", "zh": "圣三一", "ko": "삼위일체"},
    "santissima trinita":   {"ja": "至聖三者", "zh": "圣三一", "ko": "삼위일체"},
    "santissima annunziata": {"ja": "受胎告知", "zh": "圣母领报", "ko": "주님 탄생 예고"},
    "santissimo sacramento": {"ja": "聖体",   "zh": "基督圣体", "ko": "성체"},
    "santissimo redentore": {"ja": "救世主", "zh": "救主",   "ko": "구세주"},
    "santissimo crocifisso": {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "santissimo rosario":   {"ja": "ロザリオ", "zh": "玫瑰经", "ko": "로사리오"},
    "santissima vergine":   {"ja": "聖母",   "zh": "圣母",   "ko": "성모"},
    "kreuz":            {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "santa cruz":       {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "vera cruz":        {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "herz jesu":        {"ja": "イエスの聖心", "zh": "耶稣圣心", "ko": "예수 성심"},
    "sagrado corazón":  {"ja": "イエスの聖心", "zh": "耶稣圣心", "ko": "예수 성심"},
    "friedens":         {"ja": "平和",     "zh": "和平",   "ko": "평화"},
    "beata vergine":    {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "resurrection":     {"ja": "復活",     "zh": "复活",   "ko": "부활"},
    "epiphany":         {"ja": "主の公現", "zh": "主显节", "ko": "주님 공현"},
    "presentation":     {"ja": "奉献",     "zh": "献堂",   "ko": "봉헌"},
    "all saints":       {"ja": "諸聖人",   "zh": "诸圣",   "ko": "모든 성인"},
    "corpus christi":   {"ja": "聖体",     "zh": "基督圣体", "ko": "성체"},
    # --- the feasts in the corpus's OWN languages, 2026-09-17 ---
    # The table was English-only while the corpus is Italian, Spanish, Galician,
    # Portuguese and German, so the specificity fix could not fire: "visitation"
    # is not a substring of "Visitazione della Beata Vergine", and "assumption"
    # is not one of "Nuestra Señora de la Asunción". Both feasts were already
    # mapped and both were being lost to the generic Marian title.
    "visitazione":      {"ja": "聖母訪問", "zh": "圣母访亲", "ko": "성모 방문"},
    "visitación":       {"ja": "聖母訪問", "zh": "圣母访亲", "ko": "성모 방문"},
    "visitação":        {"ja": "聖母訪問", "zh": "圣母访亲", "ko": "성모 방문"},
    "heimsuchung":      {"ja": "聖母訪問", "zh": "圣母访亲", "ko": "성모 방문"},
    "asunción":         {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    "asuncion":         {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    "assunção":         {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    "asunta":           {"ja": "聖母被昇天", "zh": "圣母升天", "ko": "성모 승천"},
    "natività":         {"ja": "降誕",     "zh": "圣诞",   "ko": "성탄"},
    "natividad":        {"ja": "降誕",     "zh": "圣诞",   "ko": "성탄"},
    "natividade":       {"ja": "降誕",     "zh": "圣诞",   "ko": "성탄"},
    "trasfigurazione":  {"ja": "主の変容", "zh": "主显圣容", "ko": "주님 거룩한 변모"},
    "transfiguración":  {"ja": "主の変容", "zh": "主显圣容", "ko": "주님 거룩한 변모"},
    "verklärung":       {"ja": "主の変容", "zh": "主显圣容", "ko": "주님 거룩한 변모"},
    "annunciazione":    {"ja": "受胎告知", "zh": "圣母领报", "ko": "주님 탄생 예고"},
    "anunciación":      {"ja": "受胎告知", "zh": "圣母领报", "ko": "주님 탄생 예고"},
    "anunciação":       {"ja": "受胎告知", "zh": "圣母领报", "ko": "주님 탄생 예고"},
    "verkündigung":     {"ja": "受胎告知", "zh": "圣母领报", "ko": "주님 탄생 예고"},
    "esaltazione":      {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    "exaltation":       {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    "exaltación":       {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    "immacolata":       {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    "inmaculada":       {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    "concepción":       {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    "conceição":        {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    "dolores":          {"ja": "悲しみの聖母", "zh": "痛苦圣母", "ko": "통고의 성모"},
    "sorrows":          {"ja": "悲しみの聖母", "zh": "痛苦圣母", "ko": "통고의 성모"},
    "dolorosa":         {"ja": "悲しみの聖母", "zh": "痛苦圣母", "ko": "통고의 성모"},
    "carmen":           {"ja": "カルメル山の聖母", "zh": "加尔默罗圣母", "ko": "가르멜 산의 성모"},
    "carmine":          {"ja": "カルメル山の聖母", "zh": "加尔默罗圣母", "ko": "가르멜 산의 성모"},
    "rosario":          {"ja": "ロザリオの聖母", "zh": "玫瑰圣母", "ko": "로사리오의 성모"},
    "rosenkranz":       {"ja": "ロザリオの聖母", "zh": "玫瑰圣母", "ko": "로사리오의 성모"},
    "milagres":         {"ja": "奇跡の聖母", "zh": "显灵圣母", "ko": "기적의 성모"},
    "remedios":         {"ja": "救いの聖母", "zh": "济助圣母", "ko": "구원의 성모"},
    "guadalupe":        {"ja": "グアダルーペの聖母", "zh": "瓜达卢佩圣母", "ko": "과달루페의 성모"},
    "lourdes":          {"ja": "ルルドの聖母", "zh": "露德圣母", "ko": "루르드의 성모"},
    "fátima":           {"ja": "ファティマの聖母", "zh": "法蒂玛圣母", "ko": "파티마의 성모"},
    # Full phrases, because "exaltation" and "holy cross" are both 10 characters
    # and the tie was broken arbitrarily -- Exaltation of the Holy Cross came out
    # as plain 聖十字架 and lost the feast.
    "exaltation of the holy cross": {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    "esaltazione della santa croce": {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    "esaltazione della croce": {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    "kreuzerhöhung":    {"ja": "十字架挙栄", "zh": "光荣十字圣架", "ko": "십자가 현양"},
    # --- found by auditing what the emitted labels DROPPED, 2026-09-17 ---
    # Each of these was being silently discarded while a less specific
    # dedication rendered in its place.
    "täufer":           {"ja": "洗礼者ヨハネ", "zh": "施洗约翰", "ko": "세례자 요한"},
    "grazie":           {"ja": "恩寵の聖母", "zh": "宠爱圣母", "ko": "은총의 성모"},
    "gracia":           {"ja": "恩寵の聖母", "zh": "宠爱圣母", "ko": "은총의 성모"},
    "neve":             {"ja": "雪の聖母", "zh": "雪地圣母", "ko": "눈의 성모"},
    "nieves":           {"ja": "雪の聖母", "zh": "雪地圣母", "ko": "눈의 성모"},
    "snows":            {"ja": "雪の聖母", "zh": "雪地圣母", "ko": "눈의 성모"},
    "addolorata":       {"ja": "悲しみの聖母", "zh": "痛苦圣母", "ko": "통고의 성모"},
    "loreto":           {"ja": "ロレートの聖母", "zh": "罗雷托圣母", "ko": "로레토의 성모"},
    "rosary":           {"ja": "ロザリオの聖母", "zh": "玫瑰圣母", "ko": "로사리오의 성모"},
    "königin":          {"ja": "天の元后", "zh": "天上元后", "ko": "천상 모후"},
    "reina":            {"ja": "天の元后", "zh": "天上元后", "ko": "천상 모후"},
    "concezione":       {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    "conception":       {"ja": "無原罪の御宿り", "zh": "圣母无染原罪", "ko": "원죄 없으신 잉태"},
    # --- the individual Marian qualifiers, 2026-09-18 (Emma: "refuse each one
    # until the table individual qualifier is done"). Measured from what the
    # refusal rule rejected; the head of that distribution is almost entirely
    # established devotions and icons, not place names as I had assumed.
    "protection":       {"ja": "生神女庇護", "zh": "圣母帡幪", "ko": "성모 보호"},
    "pokrov":           {"ja": "生神女庇護", "zh": "圣母帡幪", "ko": "성모 보호"},
    "kazan":            {"ja": "カザンの生神女", "zh": "喀山圣母", "ko": "카잔의 성모"},
    "częstochowa":      {"ja": "チェンストホヴァの聖母", "zh": "琴斯托霍瓦圣母", "ko": "쳉스토호바의 성모"},
    "czestochowa":      {"ja": "チェンストホヴァの聖母", "zh": "琴斯托霍瓦圣母", "ko": "쳉스토호바의 성모"},
    "queen of poland":  {"ja": "ポーランドの元后聖母", "zh": "波兰之后圣母", "ko": "폴란드의 모후 성모"},
    "carme":            {"ja": "カルメル山の聖母", "zh": "加尔默罗圣母", "ko": "가르멜 산의 성모"},
    "carmo":            {"ja": "カルメル山の聖母", "zh": "加尔默罗圣母", "ko": "가르멜 산의 성모"},
    "perpetual help":   {"ja": "絶えざる御助けの聖母", "zh": "永援圣母", "ko": "영원한 도움의 성모"},
    "perpétuo socorro": {"ja": "永遠の助けの聖母", "zh": "永援圣母", "ko": "영원한 도움의 성모"},
    "perpetuo socorro": {"ja": "永遠の助けの聖母", "zh": "永援圣母", "ko": "영원한 도움의 성모"},
    "help of christians": {"ja": "扶助者聖マリア", "zh": "进教之佑", "ko": "신자들의 도움이신 성모"},
    "scapular":         {"ja": "スカプラリオの聖母", "zh": "圣衣圣母", "ko": "스카풀라의 성모"},
    "szkaplerznej":     {"ja": "スカプラリオの聖母", "zh": "圣衣圣母", "ko": "스카풀라의 성모"},
    "smolensk":         {"ja": "スモレンスクの生神女", "zh": "斯摩棱斯克圣母", "ko": "스몰렌스크의 성모"},
    "vladimir":         {"ja": "ウラジーミルの生神女", "zh": "弗拉基米尔圣母", "ko": "블라디미르의 성모"},
    "of the sign":      {"ja": "しるしの生神女", "zh": "神视圣母", "ko": "표징의 성모"},
    "znamenie":         {"ja": "しるしの生神女", "zh": "神视圣母", "ko": "표징의 성모"},
    "dores":            {"ja": "悲しみの聖母", "zh": "痛苦圣母", "ko": "통고의 성모"},
    "angustias":        {"ja": "悲しみの聖母", "zh": "痛苦圣母", "ko": "통고의 성모"},
    "entry of the theotokos": {"ja": "生神女進堂", "zh": "圣母献堂", "ko": "성모 자헌"},
    "joy of all who sorrow": {"ja": "全ての悲しむ者の喜び", "zh": "苦者之乐圣母", "ko": "모든 슬픈 이의 기쁨"},
    "of the angels":    {"ja": "天使の聖母", "zh": "天神之后圣母", "ko": "천사의 성모"},
    "consolation":      {"ja": "慰めの聖母", "zh": "安慰之母", "ko": "위로의 성모"},
    "bon secours":      {"ja": "善き助けの聖母", "zh": "善佑圣母", "ko": "좋은 도움의 성모"},
    "merced":           {"ja": "慈悲の聖母", "zh": "赎虏圣母", "ko": "자비의 성모"},
    "piedade":          {"ja": "憐れみの聖母", "zh": "怜悯圣母", "ko": "자비의 성모"},
    "guia":             {"ja": "導きの聖母", "zh": "引导圣母", "ko": "인도의 성모"},
    "luz":              {"ja": "光の聖母", "zh": "光明圣母", "ko": "빛의 성모"},
    "grace of nieppe":  {"ja": "恩寵の聖母", "zh": "宠爱圣母", "ko": "은총의 성모"},
    # --- found by auditing residue on SPECIFIC matches, 2026-09-18 ---
    # ⛔ "Immaculate HEART of Mary" is not the Immaculate CONCEPTION. `immaculate`
    # matched first and 30 labels came out as 無原罪の御宿り. Longer phrases, so
    # they win the within-group sort.
    "immaculate heart": {"ja": "聖母の汚れなき御心", "zh": "圣母无玷圣心", "ko": "성모 성심"},
    "cuore immacolato": {"ja": "聖母の汚れなき御心", "zh": "圣母无玷圣心", "ko": "성모 성심"},
    "corazón inmaculado": {"ja": "聖母の汚れなき御心", "zh": "圣母无玷圣心", "ko": "성모 성심"},
    # "Nativity of the Lord" is Christmas; "Nativity of the Theotokos" is the
    # Virgin's birth. Bare `nativity` cannot tell them apart, so both explicit
    # forms are named and the bare one stays as the fallback.
    "nativity of the lord": {"ja": "主の降誕", "zh": "主诞", "ko": "주님 성탄"},
    "nativity of christ": {"ja": "主の降誕", "zh": "主诞", "ko": "주님 성탄"},
    "nativity of the theotokos": {"ja": "生神女誕生", "zh": "圣母诞辰", "ko": "성모 탄생"},
    "nativity of the virgin": {"ja": "生神女誕生", "zh": "圣母诞辰", "ko": "성모 탄생"},
    "nostra signora":   {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "blessed virgin":   {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "vergine":          {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    # German, Italian and Latin forms of dedications the table had in English
    # only -- all six came from the labels that actually reached Wikidata.
    "auferstehung":     {"ja": "復活",     "zh": "复活",   "ko": "부활"},
    "risurrezione":     {"ja": "復活",     "zh": "复活",   "ko": "부활"},
    "sacro cuore":      {"ja": "イエスの聖心", "zh": "耶稣圣心", "ko": "예수 성심"},
    "sagrado coração":  {"ja": "イエスの聖心", "zh": "耶稣圣心", "ko": "예수 성심"},
    "frauenkirche":     {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "liebfrauen":       {"ja": "聖母",     "zh": "圣母",   "ko": "성모"},
    "heiligen geist":   {"ja": "聖霊",     "zh": "圣神",   "ko": "성령"},
    "heiliger geist":   {"ja": "聖霊",     "zh": "圣神",   "ko": "성령"},
    "espírito santo":   {"ja": "聖霊",     "zh": "圣神",   "ko": "성령"},
    "stella maris":     {"ja": "海の星の聖母", "zh": "海星圣母", "ko": "바다의 별 성모"},
    "antonio abate":    {"ja": "大アントニオ", "zh": "圣安当", "ko": "대 안토니오"},
    "antonio abad":     {"ja": "大アントニオ", "zh": "圣安当", "ko": "대 안토니오"},
    "purissima sang":   {"ja": "尊き御血", "zh": "宝血",   "ko": "보혈"},
    "santa croce":      {"ja": "聖十字架", "zh": "圣十字", "ko": "성십자가"},
    "dreifaltigkeit":   {"ja": "至聖三者", "zh": "圣三一", "ko": "삼위일체"},
    "erlöser":          {"ja": "救世主", "zh": "救主",   "ko": "구세주"},
    "cristo re":        {"ja": "王たるキリスト", "zh": "基督君王", "ko": "그리스도 왕"},
    "christ the king":  {"ja": "王たるキリスト", "zh": "基督君王", "ko": "그리스도 왕"},
    "mandylion":        {"ja": "自印聖像", "zh": "不由人手所画的救主圣像", "ko": "만딜리온"},
    "heilig geist":     {"ja": "聖霊",   "zh": "圣神",   "ko": "성령"},
    "holy shroud":      {"ja": "聖骸布", "zh": "都灵裹尸布", "ko": "성해포"},
    "versöhnung":       {"ja": "和解",   "zh": "和好",   "ko": "화해"},
    "archangels":       {"ja": "大天使", "zh": "总领天使", "ko": "대천사"},
    "virgin mary queen": {"ja": "天の元后", "zh": "天上元后", "ko": "천상 모후"},
}

# A feast or event names WHICH dedication; a Marian title alone only names who it
# is to. When both appear, the feast is the dedication.
SPECIFIC_DEDICATIONS = {
    "holy trinity", "santissima trinità", "santissima trinita", "holy cross",
    "santa cruz", "vera cruz", "heilig kreuz", "kreuz", "holy spirit",
    "assumption", "assunta", "mariä himmelfahrt", "himmelfahrt",
    "nativity", "transfiguration", "ascension", "dormition", "annunciation",
    "santissima annunziata", "visitation", "intercession", "immaculate",
    "sacred heart", "herz jesu", "sagrado corazón", "resurrection", "epiphany",
    "presentation", "all saints", "corpus christi", "santissimo sacramento",
    "santissimo redentore", "santissimo crocifisso", "santissimo rosario",
    # the same feasts in the corpus's own languages
    "visitazione", "visitación", "visitação", "heimsuchung",
    "asunción", "asuncion", "assunção", "asunta",
    "natività", "natividad", "natividade",
    "trasfigurazione", "transfiguración", "verklärung",
    "annunciazione", "anunciación", "anunciação", "verkündigung",
    "esaltazione", "exaltation", "exaltación",
    "immacolata", "inmaculada", "concepción", "conceição",
    "dolores", "sorrows", "dolorosa", "carmen", "carmine",
    "rosario", "rosenkranz", "milagres", "remedios",
    "guadalupe", "lourdes", "fátima",
    "exaltation of the holy cross", "esaltazione della santa croce",
    "esaltazione della croce", "kreuzerhöhung",
    # devotions the audit found being dropped
    "täufer", "grazie", "gracia", "neve", "nieves", "snows", "addolorata",
    "loreto", "rosary", "königin", "reina", "concezione", "conception",
    # the individual Marian qualifiers
    "protection", "pokrov", "kazan", "częstochowa", "czestochowa",
    "queen of poland", "carme", "carmo", "perpetual help",
    "perpétuo socorro", "perpetuo socorro", "help of christians",
    "scapular", "szkaplerznej", "smolensk", "vladimir", "of the sign",
    "znamenie", "dores", "angustias", "entry of the theotokos",
    "joy of all who sorrow", "of the angels", "consolation", "bon secours",
    "merced", "piedade", "guia", "luz", "grace of nieppe",
    "holy shroud", "versöhnung", "archangels", "virgin mary queen",
    "santa croce", "dreifaltigkeit", "erlöser", "cristo re",
    "christ the king", "mandylion", "heilig geist",
    "immaculate heart", "cuore immacolato", "corazón inmaculado",
    "nativity of the lord", "nativity of christ",
    "nativity of the theotokos", "nativity of the virgin",
    "auferstehung", "risurrezione", "sacro cuore", "sagrado coração",
    "heiligen geist", "heiliger geist", "espírito santo", "stella maris",
    "antonio abate", "antonio abad", "purissima sang",
}

# Generic titles — checked only after every feast has had its chance.
GENERIC_DEDICATIONS = {
    "our lady", "madonna", "theotokos", "notre dame", "nosa señora",
    "nossa senhora", "nuestra señora", "virxe", "beata vergine",
    "santissima vergine", "friedens",
    # Italian carrier, missing until the residue audit -- 12 labels were reading
    # "Nostra Signora" as a qualifier rather than as the title it is.
    "nostra signora", "blessed virgin", "vergine",
    "frauenkirche", "liebfrauen",
}

# --------------------------------------------------------------------------
# Category-shaped labels — refused outright.
# --------------------------------------------------------------------------
_CATEGORY_PATTERNS = [
    re.compile(r"\bcultural heritage\b", re.I),
    re.compile(r"\bmonuments?\s+in\b", re.I),
    re.compile(r"\bheritage\s+(sites?|monuments?)\b", re.I),
    re.compile(r"\bdistrict\b", re.I),
    re.compile(r"\bestate\b", re.I),
    re.compile(r"\bmunicipality\b", re.I),
    re.compile(r"\bbuildings\s+in\b", re.I),
    # A PLURAL type word is a grouping, not a building.
    re.compile(r"\b(churches|chapels|synagogues|mosques|cathedrals|temples|"
               r"monasteries|kirchen|kapellen|chiese|iglesias)\b", re.I),
]


def is_category_shaped(label):
    """True when the label names a GROUPING rather than one building."""
    return any(p.search(label) for p in _CATEGORY_PATTERNS)


def _norm(token):
    return unicodedata.normalize("NFC", token).strip(" .,'’").lower()


def _strip_compound_type(token):
    """German-style glued types: Jerusalemkirche -> Jerusalem, St.-Petri-Kirche
    -> St.-Petri. Returns the token with a recognised type tail removed, or the
    token unchanged. Only fires when something is LEFT, so `Kirche` alone is not
    reduced to the empty string."""
    low = _norm(token)
    for tail in sorted(TYPE_WORDS, key=len, reverse=True):
        if len(tail) < 4 or not low.endswith(tail):
            continue
        stem = low[: -len(tail)].rstrip("-­ ")
        if stem:
            return stem
    return low


def parse_name(label):
    """(name_tokens, saw_saint) — the label with frame words removed.

    The TYPE is not taken from here; it comes from P31. This only finds the name.
    """
    saw_saint = False
    out = []
    for raw in re.split(r"[\s/]+", label):
        tok = _norm(raw)
        if not tok:
            continue
        if tok in SAINT_MARKERS:
            saw_saint = True
            continue
        if tok in STOPWORDS or tok in TYPE_WORDS:
            continue
        stem = _strip_compound_type(tok)
        if stem in TYPE_WORDS or not stem:
            continue
        if stem in SAINT_MARKERS:
            saw_saint = True
            continue
        # A hyphenated or apostrophised cluster carries its own marker:
        # "st.-petri", and the Italian "Sant'Anna" / "Sant'Antonio", which were
        # arriving here as a single unknown token.
        parts = [p for p in re.split(r"[-–—'’]", stem) if p]
        for p in parts:
            if p in SAINT_MARKERS:
                saw_saint = True
            elif p in STOPWORDS or p in TYPE_WORDS:
                continue
            else:
                out.append(p)
    return out, saw_saint


# Place goes FIRST, possessive (Emma, 2026-09-17: "Place first, possessive").
# ja and ko take a genitive particle; zh simply juxtaposes.
_PLACE_JOIN = {"ja": "の", "zh": "", "ko": "의 "}


def _fold(text):
    """Accent-folded for matching only — never for output."""
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c))


_FOLDED = {}


def _folded_group(group):
    """Phrase-set folded once, cached: {folded: original}."""
    key = id(group)
    if key not in _FOLDED or len(_FOLDED[key]) != len(group):
        _FOLDED[key] = {_fold(p): p for p in group}
    return _FOLDED[key]


try:
    from romance_katakana import place_to_katakana as _romance_kana
except ImportError:                                    # pragma: no cover
    _romance_kana = None

# ⛔ ja ONLY. Emma, 2026-09-18: handle the place-name qualifiers too. A Romance
# locality can be read into kana by rule, so "Madonna del Pero" becomes
# ペロの聖母. There is no equivalent route to Chinese characters or hangul --
# those are conventions, not derivations -- so zh and ko keep refusing rather
# than invent a reading.
_QUALIFIER_LANGS = {"ja"}


def qualifier_kana(tokens, rules=None):
    """Katakana for an unmapped place qualifier, or None.

    `rules` picks the source language's orthography and comes from the item's
    own P17 -- Italian ce is /tʃe/ while Portuguese and Spanish ce is /s/, and
    guessing one for all of them was backwards for the larger slice of this
    corpus. Absent a country, the module default applies.

    Refuses unless EVERY token reads as Romance, so a mixed or non-Romance
    qualifier produces nothing instead of a half-transliteration.
    """
    if not tokens or _romance_kana is None or rules is None:
        return None
    return _romance_kana(" ".join(tokens), rules)


def _qualifier_residue(folded_label, matched_phrase):
    """Tokens left after removing a matched generic title and all known frame.

    Anything here is a qualifier the table cannot render — "del Pero", "delle
    Grazie" before it was added, "of Vladimir". Its presence means the generic
    title would understate the source.
    """
    rest = folded_label.replace(matched_phrase, " ")
    out = []
    for raw in re.split(r"[\s/,\.]+", rest):
        tok = _norm(raw)
        if not tok:
            continue
        if (tok in STOPWORDS or tok in TYPE_WORDS or tok in SAINT_MARKERS
                or tok in NAMES or tok in SELF_SAINT):
            continue
        stem = _strip_compound_type(tok)
        if (not stem or stem in TYPE_WORDS or stem in STOPWORDS
                or stem in NAMES or stem in SAINT_MARKERS):
            continue
        # A folded generic title that is not the one we matched (e.g. "beata"
        # left over from "beata vergine") is still carrier, not a qualifier.
        if any(tok in _fold(g) for g in GENERIC_DEDICATIONS):
            continue
        out.append(tok)
    return out


def name_key(token):
    """The NAMES key a token resolves to, or None.

    German compounds carry a GENITIVE: Martinskirche is Martin-s-kirche, so
    stripping the type tail leaves `martins`, and Peterskirche leaves `peters`.
    Listing every saint twice would be the wrong fix -- the -s is grammar. The
    Latin genitive -i (Nikolai, Pauli) is the same story.
    """
    if token in NAMES:
        return token
    for suffix in ("s", "i", "is", "us", "en"):
        if token.endswith(suffix):
            stem = token[: -len(suffix)]
            if stem in NAMES:
                return stem
    return None


def _unfold_tokens(label, folded_tokens):
    """Map folded residue tokens back to their ORIGINAL spelling.

    ⛔ `dedication()` folds accents before matching, so by the time a qualifier
    is extracted its ç and ã are already gone -- Graças reached the
    transliterator as "gracas" and came out グラーカス however good the
    Portuguese rules were. The diacritics are exactly what those rules need, so
    the residue is mapped back to the source spelling before it is read.
    """
    originals = {}
    for raw in re.split(r"[\s/,\.]+",
                        re.sub(r"[-–—'’]", " ", label)):
        tok = raw.strip(" .,'’").lower()
        if tok:
            originals.setdefault(_fold(tok), tok)
    return [originals.get(t, t) for t in folded_tokens]


def dedication(label, lang, rules="it"):
    """The dedication rendered in `lang`, or None if any part is unknown."""
    # Hyphens joined the phrase in the corpus ("Notre-Dame", "Herz-Jesu"), so the
    # phrase lookup saw "notre-dame" and missed. 111 labels turned on this alone.
    low = re.sub(r"[-–—']", " ", _norm(label))
    low = re.sub(r"\s+", " ", low)
    # ...and accents. The corpus spans five source languages and the same feast
    # appears as "Fátima"/"Fatima", "Asunción"/"Asuncion", "Natività"/"Nativita".
    # Listing every accented variant is a losing game, so both sides of the
    # comparison are folded instead.
    low = _fold(low)
    # ⛔ Priority, NOT string length. Sorting by length let "beata vergine" (13)
    # beat "visitation" (10) on `Visitazione della Beata Vergine`, and
    # "nuestra señora" beat "assumption" on `Nuestra Señora de la Asunción` --
    # dropping the very feast the label names, which the table already had. A
    # feast or event is always more specific than the Marian title carrying it,
    # so SPECIFIC is checked first and only then the generic titles; within each
    # group, longest first so "sacred heart" still beats a bare "heart".
    folded = _folded_group(SPECIFIC_DEDICATIONS)
    for phrase in sorted(folded, key=len, reverse=True):
        if phrase in low:
            # A feast names WHICH dedication, so the Marian title it rides on is
            # correctly subsumed and any residue is that carrier.
            return DEDICATIONS[folded[phrase]][lang]

    # ⛔ A GENERIC title is only acceptable when there is nothing left over.
    # Emma, 2026-09-18: "Refuse each one until the table individual qualifier is
    # done." "Madonna del Pero" and "Madonna del Cardello" both rendered 聖母教会
    # — true, unique once the place is prefixed, and less specific than the
    # source said. A bare "Madonna" has no qualifier to lose and still resolves.
    folded = _folded_group(GENERIC_DEDICATIONS)
    for phrase in sorted(folded, key=len, reverse=True):
        if phrase in low:
            residue = _qualifier_residue(low, phrase)
            if not residue:
                return DEDICATIONS[folded[phrase]][lang]
            # A qualifier the table cannot name. For ja it can still be read by
            # rule if it is a Romance locality; for zh/ko it cannot, and the
            # refusal stands.
            if lang not in _QUALIFIER_LANGS:
                return None
            kana = qualifier_kana(_unfold_tokens(label, residue), rules)
            if not kana:
                return None
            return kana + "の" + DEDICATIONS[folded[phrase]][lang]
    tokens, saw_saint = parse_name(label)
    if not tokens:
        return None
    joined = " ".join(tokens)
    if joined in NAME_PHRASES:
        return SAINT_PREFIX[lang] + NAME_PHRASES[joined][lang] if saw_saint             else NAME_PHRASES[joined][lang]
    rendered = []
    for t in tokens:
        if t in SELF_SAINT:
            saw_saint = True
        key = name_key(t)
        if key is None:
            return None          # unknown name — caller decides, not this module
        rendered.append(NAMES[key][lang])
    core = "".join(rendered)
    if saw_saint:
        core = SAINT_PREFIX[lang] + core
    return core


# --------------------------------------------------------------------------
# English, keyed by the canonical ja rendering
# --------------------------------------------------------------------------
# Stage 1's English is paused, but Emma asked (2026-09-18) for the handful that
# reached Wikidata to be REPLACED with stage-2 quality English rather than
# removed. Keying off the ja form means one map of ~90 entries instead of an
# "en" on every one of the ~200 table rows, and it cannot drift out of step
# with them — a name with no entry here simply does not render in English.
EN_FROM_JA = {
    # saints
    "アンデレ": "Andrew", "アントニオ": "Anthony", "アンナ": "Anne",
    "ウィンケンティウス": "Vincent", "エリヤ": "Elijah", "カタリナ": "Catherine",
    "キリスト": "Christ", "クリストフォロス": "Christopher",
    "ゲオルギオス": "George", "スタニスラウス": "Stanislaus",
    "ステファノ": "Stephen", "デメトリオス": "Demetrius",
    "ニコラオス": "Nicholas", "バルバラ": "Barbara", "パウロ": "Paul",
    "パラスケヴィ": "Paraskeva", "フランチェスコ": "Francis", "ペトロ": "Peter",
    "マメス": "Mamas", "マリア": "Mary", "マリナ": "Marina",
    "マルティヌス": "Martin", "ミカエル": "Michael", "ヤコブ": "James",
    "ヨセフ": "Joseph", "ヨハネ": "John", "ラウレンティウス": "Lawrence",
    "ロクス": "Roch", "大天使": "the Archangel", "救世主": "the Saviour",
    "洗礼者ヨハネ": "John the Baptist",
    "イシドロ": "Isidore", "ペレグリヌス": "Peregrine",
    "マウリティウス": "Maurice", "テレンティアヌス": "Terentian",
    "幼子殉教者": "the Holy Innocents", "テレサ": "Teresa", "ピオ": "Pius",
    "ボニファティウス": "Boniface", "マタイ": "Matthew", "トマス": "Thomas",
    # dedications
    "しるしの生神女": "Our Lady of the Sign",
    "イエスの聖心": "the Sacred Heart",
    "ウラジーミルの生神女": "Our Lady of Vladimir",
    "カザンの生神女": "Our Lady of Kazan",
    "カルメル山の聖母": "Our Lady of Mount Carmel",
    "扶助者聖マリア": "Our Lady Help of Christians",
    "グアダルーペの聖母": "Our Lady of Guadalupe",
    "スカプラリオの聖母": "Our Lady of the Scapular",
    "スモレンスクの生神女": "Our Lady of Smolensk",
    "チェンストホヴァの聖母": "Our Lady of Częstochowa",
    "ファティマの聖母": "Our Lady of Fátima",
    "ポーランドの元后聖母": "Our Lady Queen of Poland",
    "慈悲の聖母": "Our Lady of Mercy",
    "ルルドの聖母": "Our Lady of Lourdes",
    "ロザリオ": "the Rosary", "ロザリオの聖母": "Our Lady of the Rosary",
    "ロレートの聖母": "Our Lady of Loreto",
    "主の公現": "the Epiphany", "主の変容": "the Transfiguration",
    "主の昇天": "the Ascension", "主の降誕": "the Nativity of the Lord",
    "光の聖母": "Our Lady of Light",
    "全ての悲しむ者の喜び": "Our Lady Joy of All Who Sorrow",
    "十字架挙栄": "the Exaltation of the Holy Cross",
    "受胎告知": "the Annunciation",
    "善き助けの聖母": "Our Lady of Good Help",
    "天の元后": "Our Lady Queen of Heaven",
    "天使の聖母": "Our Lady of the Angels",
    "奇跡の聖母": "Our Lady of Miracles",
    "奉献": "the Presentation", "導きの聖母": "Our Lady of Guidance",
    "平和": "Peace", "復活": "the Resurrection",
    "恩寵の聖母": "Our Lady of Grace",
    "悲しみの聖母": "Our Lady of Sorrows",
    "慰めの聖母": "Our Lady of Consolation",
    "憐れみの聖母": "Our Lady of Pity",
    "救いの聖母": "Our Lady of Remedies",
    "絶えざる御助けの聖母": "Our Lady of Perpetual Help",
    "無原罪の御宿り": "the Immaculate Conception",
    "生神女": "the Theotokos", "生神女就寝": "the Dormition",
    "生神女庇護": "the Protection of the Theotokos",
    "生神女誕生": "the Nativity of the Theotokos",
    "生神女進堂": "the Entry of the Theotokos",
    "聖体": "Corpus Christi", "聖十字架": "the Holy Cross",
    "聖母": "Our Lady", "聖母の汚れなき御心": "the Immaculate Heart of Mary",
    "聖母被昇天": "the Assumption", "聖母訪問": "the Visitation",
    "聖霊": "the Holy Spirit", "至聖三者": "the Holy Trinity",
    "被昇天": "the Assumption", "諸聖人": "All Saints",
    "降誕": "the Nativity", "雪の聖母": "Our Lady of the Snows",
    "海の星の聖母": "Our Lady Star of the Sea", "大アントニオ": "Saint Anthony the Abbot",
    "尊き御血": "the Most Precious Blood",
}

# A place label often carries its own disambiguator -- "Freden (Leine)" gives
# フレーデン (ライネ), and without this the building's label inherits it as
# "フレーデン (ライネ)の聖ラウレンティウス教会". The parenthetical disambiguates the
# PLACE from another place; it says nothing about the building.
_PLACE_PAREN = re.compile(r"\s*[（(\[][^）)\]]*[）)\]]\s*$")


_INVISIBLE = re.compile(r"[­​-‏⁠﻿]")


def clean_place(place):
    """Strip the parenthetical disambiguator and any invisible characters.

    A soft hyphen (U+00AD) in a place label reached the output as
    "­ラドヴィシュ" -- invisible in a terminal, a real character in the label.
    """
    if not place:
        return place
    place = _INVISIBLE.sub("", place)
    return _PLACE_PAREN.sub("", place).strip()


def render_en(label, p31):
    """English label, or None when any piece is unknown.

    English word order is "Church of X", not the place-first form the CJK
    languages take, and no place is prefixed — the labels this replaces do not
    carry one. Saints get "Saint"; dedications already read as noun phrases.
    """
    if is_category_shaped(label):
        return None
    type_words = TYPES.get(p31)
    if not type_words:
        return None
    ja = dedication(label, "ja")
    if not ja:
        return None
    # dedication() has already applied the saint prefix for a SAINT, and
    # EN_FROM_JA is keyed by the bare name. But the prefix is 聖, and 聖母 /
    # 聖霊 / 聖体 / 聖十字架 are dedications that legitimately BEGIN with it — a
    # naive startswith reduced them to 母 and 霊 and returned None. So the whole
    # string is looked up first, and only a miss falls back to stripping.
    en = EN_FROM_JA.get(ja)
    if en is None and ja.startswith(SAINT_PREFIX["ja"]):
        bare = ja[len(SAINT_PREFIX["ja"]):]
        en = EN_FROM_JA.get(bare)
        if en is not None and not en.startswith("the "):
            en = "Saint " + en
    if not en:
        return None
    return "%s of %s" % (type_words["en"], en)


try:
    from plain_latin_katakana import name_to_katakana as _plain_kana
except ImportError:                                    # pragma: no cover
    _plain_kana = None

# ⛔ ja only, for the reason `_QUALIFIER_LANGS` gives: a transliteration is a
# reading, and there is no rule-based reading of a Macedonian village name into
# hanzi or hangul. The generic mosques still reach zh and ko, because a
# translation of `old` is a translation.
_MOSQUE_NAME_LANGS = {"ja"}

_KATAKANA = re.compile(r"[ァ-ヺー]")


def _kana_join(left, right):
    """`・` between two katakana runs, nothing between anything else.

    Emma's own example is オメル・モスク, and without the separator オメルモスク
    reads as one word. A kanji type word (教会, 金曜モスク's 金曜) needs no
    separator and must not get one.
    """
    if not left or not right:
        return (left or "") + (right or "")
    if _KATAKANA.match(left[-1]) and _KATAKANA.match(right[0]):
        return left + "・" + right
    return left + right


def mosque_parse(label):
    """(modifiers, friday, surau, name_tokens, saw_type) for a mosque label.

    The generic-vs-name test, and it is a lookup rather than a heuristic: a
    token is generic when `MODIFIER_ALIASES` names it, and everything left over
    after the type words, the modifiers, the stopwords and the ordinals is a
    name. Anything guessed at here would be guessed at in 245 different
    languages at once.
    """
    modifiers, names = [], []
    friday = surau = saw_type = False
    for raw in re.split(r"[\s/,\.\-–—'’]+", label):
        tok = _norm(raw)
        if not tok:
            continue
        if tok in MOSQUE_TYPE_WORDS:
            saw_type = True
        elif tok in SURAU_WORDS:
            saw_type = surau = True
        elif tok in FRIDAY_WORDS:
            saw_type = friday = True
        elif tok in MODIFIER_ALIASES:
            alias = MODIFIER_ALIASES[tok]
            if alias not in modifiers:
                modifiers.append(alias)
        elif tok in STOPWORDS or _ROMAN.match(tok) or len(tok) == 1:
            # A one-letter leftover is an initial or an honorific abbreviation —
            # the H. of `Masjid H. Bakri` (Haji), which read as フ.
            continue
        else:
            names.append(raw.strip(" .,'’"))
    return modifiers, friday, surau, names, saw_type


def render_mosque(label, p31, lang, place, latin_rules=None):
    """A mosque-family label in `lang`, or None.

    Slots, in this order: `<place>の` `<name>` `<modifiers>` `<friday>` `<type>`.
    A modifier is translated, a name is transliterated, and both modifier and
    Friday marker sit against the type word they qualify.

    ⚠ The modifier goes AFTER the name, not before it. First written the other
    way round, `Adana New Mosque` came out 新アダナ・モスク — which reads as a
    mosque in a place called New Adana, because a Japanese prefix attaches to
    whatever follows it. アダナ新モスク is the new mosque at Adana, which is what
    the label says. The same mistake turned `Ashaghi Mosque in Buzovna` into
    下ブゾヴナ・モスク, "the Lower Buzovna mosque".
    """
    modifiers, friday, surau, names, saw_type = mosque_parse(label)
    if not saw_type:
        # "Nablus", "WikiBanua 2.0", "Donauwörther Straße 165" — filed under
        # P31 mosque but not named as one. There is no slot to put them in.
        return None
    type_word = SURAU_TYPE[lang] if surau else TYPES[p31][lang]
    tail = ("".join(GENERIC_MODIFIERS[m][lang] for m in modifiers)
            + (FRIDAY_MODIFIER[lang] if friday else "") + type_word)

    if not names:
        return place + _PLACE_JOIN[lang] + tail
    if any(_norm(n) in ENGLISH_MARKERS for n in names):
        return None
    if lang not in _MOSQUE_NAME_LANGS or _plain_kana is None:
        return None
    kana = _plain_kana(" ".join(names), latin_rules)
    if not kana:
        return None
    # A name word that IS the place is already in the place slot: "Mosque in
    # Pirshagi" would otherwise read ピルシャギのピルシャギ・モスク.
    kept = [k for k in kana.split("・") if k != place]
    if not kept:
        return place + _PLACE_JOIN[lang] + tail
    return place + _PLACE_JOIN[lang] + _kana_join("・".join(kept), tail)


# --------------------------------------------------------------------------
# The transliteration fallback — "No dedication means transliteration"
# --------------------------------------------------------------------------
# Emma, 2026-09-18. `dedication()` refuses the moment ONE name token is absent
# from `NAMES`, and measured over the 22,548-item corpus that refusal is the
# single biggest gate in the pipeline: **13,470 items**, against 7,599 that
# resolve. `Santo André de Lourizán` is not an unknown saint — it is Andrew, at
# a place the table has never heard of.
#
# ⛔ ja only, for the third time and the same reason (`_QUALIFIER_LANGS`,
# `_MOSQUE_NAME_LANGS`): a transliteration is a READING. Romance and plain-Latin
# orthography give a rule-based route to kana; there is no rule-based route to
# hanzi or hangul, and inventing one fabricates a reading instead of deriving it.
_TRANSLIT_LANGS = {"ja"}

# Genitive and locative links — where a dedicatee ENDS and its qualifier begins.
# `San Francesco di Paola` is Francis *of Paola*, not a person called Francesco
# Paola, and the shape that says so is the one the generic-title branch already
# emits: `qualifier + の + dedication`, e.g. ペーロの聖母教会. These are all in
# STOPWORDS already and stay dropped from the output; what they add here is the
# SPLIT POINT.
_LINKERS = {
    "of", "in", "at", "near", "de", "da", "do", "di", "del", "della", "dello",
    "dei", "degli", "delle", "des", "du", "dos", "das", "van", "von", "zu",
    "zum", "zur", "am", "im", "an", "auf", "bei", "alle", "alla", "allo", "ai",
    "al", "all", "sul", "sulla", "na", "nad", "w", "en", "u",
}


def _dedicatee_split(label):
    """(head_tokens, qualifier_tokens, saw_saint) — the dedicatee and its qualifier.

    The split is the first `_LINKERS` word (or comma) that follows at least one
    name token, so the `of` in `Church of Santa Clara` links the TYPE to the
    dedicatee and does not split, while the comma in `…Santa Clara, Vitoria-Gasteiz`
    does.

    ⚠ A saint marker after the split is not read as one: `Chapel of St Anne in
    San Pedro` is Anne, in a place called San Pedro, and prefixing 聖 to the
    qualifier would say the place is a saint.
    """
    head, qual = [], []
    saw_saint = False
    split = False

    def bucket():
        return qual if split else head

    def frame(tok, group):
        """Membership, accent-folded. `dedication()` folds its whole input before
        matching and this splitter cannot — the transliterator needs the
        diacritics — so the frame sets are folded here instead. `apóstol` is in
        STOPWORDS as `apostol` and was reaching the name slot as a dedicatee."""
        return tok in group or _fold(tok) in _folded_group(group)

    for raw in re.split(r"[\s/]+", label):
        if not raw:
            continue
        breaks = raw.rstrip().endswith((",", ";", "("))
        tok = _norm(raw)
        if not tok:
            continue
        if frame(tok, _LINKERS):
            if head:
                split = True
            continue
        if frame(tok, SAINT_MARKERS):
            if not split:
                saw_saint = True
            continue
        if frame(tok, STOPWORDS) or frame(tok, TYPE_WORDS):
            if head and breaks:
                split = True
            continue
        stem = _strip_compound_type(tok)
        if not stem or frame(stem, TYPE_WORDS):
            if head and breaks:
                split = True
            continue
        for p in [p for p in re.split(r"[-–—'’]", stem) if p]:
            if frame(p, SAINT_MARKERS):
                if not split:
                    saw_saint = True
            elif frame(p, STOPWORDS) or frame(p, TYPE_WORDS) or frame(p, _LINKERS):
                continue
            else:
                bucket().append(p)
        if head and breaks:
            split = True
    return head, qual, saw_saint


def _echoes_place(token, place_en):
    """True when a token just repeats the P131 place's own name.

    `Church of Santa Clara, Vitoria-Gasteiz` sits in Vitoria-Gasteiz, and the
    place is already in the first slot — without this it reads
    ビトリア＝ガステイスのヴィトーリア・ガーステイスの聖クラーラ教会, naming the
    town twice in two different spellings, because the ja label is Wikidata's
    and the qualifier is derived. The comparison is therefore against the place's
    ENGLISH label, which is the same alphabet as the source string.
    """
    if not place_en:
        return False
    parts = {_fold(t) for t in re.split(r"[\s/,\.\-–—'’]+", place_en.lower()) if t}
    return _fold(token) in parts


def _translit_tokens(tokens, lang, rules=None, latin_rules=None):
    """Tokens rendered in `lang`: `NAMES` where known, kana where not, else None.

    All-or-nothing, like every other transliterator here: a half-read name looks
    deliberate and is not.
    """
    out = ""
    for t in tokens:
        # ⛔ FOLD for the table lookup, and only for the lookup. `dedication()`
        # folds its whole input before matching; this function does not, because
        # the transliterator needs the diacritics (`_unfold_tokens` exists for
        # exactly that). Looking `lucía` up unfolded missed a saint the table has
        # had all along, and measured over the reachable population that one
        # slip covered `lucía` 20, `antónio` 19, `román` 18 and 200-odd more —
        # each of which would have been READ instead of NAMED.
        key = name_key(t) or name_key(_fold(t))
        if key is not None:
            out = _kana_join(out, NAMES[key][lang])
            continue
        kana = None
        if rules is not None and _romance_kana is not None:
            kana = _romance_kana(t, rules)
        elif latin_rules is not None and _plain_kana is not None:
            kana = _plain_kana(t, latin_rules)
        if not kana:
            return None
        out = _kana_join(out, kana)
    return out or None


# Returned by `transliterate_dedication` when every name token the label carries
# turned out to BE the place — `Pančevo Synagogue` in Pančevo. There is then
# nothing to put in the dedication slot and `place + type` is the whole label,
# which is what `render_mosque` already does for `Mosque in Pirshagi`.
PLACE_ONLY = "<place-only>"


def transliterate_dedication(label, lang, rules=None, latin_rules=None,
                             place_en=None):
    """The dedication READ rather than translated, or None.

    The fallback for everything `dedication()` refuses. Slots are the ones the
    generic-title branch already established: `<qualifier>の<聖><dedicatee>`,
    which the caller then prefixes with the place and suffixes with the type.

    A qualifier that cannot be read refuses the whole label rather than dropping
    it — `_qualifier_residue` makes the same call, and for the same reason: a
    label that silently loses its qualifier claims less than the source said.
    """
    if lang not in _TRANSLIT_LANGS:
        return None
    head, qual, saw_saint = _dedicatee_split(label)
    if not head:
        return None
    head = [t for t in head if not _echoes_place(t, place_en)]
    qual = [t for t in qual if not _echoes_place(t, place_en)]
    if not head:
        return PLACE_ONLY if not qual else None
    core = _translit_tokens(head, lang, rules, latin_rules)
    if not core:
        return None
    if saw_saint:
        core = SAINT_PREFIX[lang] + core
    if qual:
        q = _translit_tokens(qual, lang, rules, latin_rules)
        if not q:
            return None
        core = q + _PLACE_JOIN[lang] + core
    return core


def render(label, p31, lang, place=None, rules=None, latin_rules=None,
           place_en=None):
    """The label in `lang`, or None when any piece is unknown.

    ⛔ `rules` DEFAULTS TO NONE, which means refuse — "unlisted means refuse,
    never a default", the same doctrine `romance_katakana.rules_for_country`
    states. It used to default to `"it"`, which was harmless while an unknown
    name was refused outright and became a live hazard the moment the
    transliteration fallback existed: `Hofkapelle Aichet` is German and was read
    as Italian, `St. Fictitious` as ホーフカペッレ・フィクチーオウス. The
    generator was never exposed — it passes `rules=_rules_for(p17)` — but four
    tests were passing only because of the default, which is how this was found.

    `place` is the P131 area's OWN label in `lang` — passed in, never derived
    here. It is what makes the output unique: measured over 200 sampled items
    there were 192 distinct P131 places, while the dedication alone collapsed
    515 different Madonna churches onto one string. Without a place this returns
    None rather than emit a label that dozens of items would share.

    Returns None rather than guessing, everywhere. An unknown dedicatee or a
    place with no label in this language is a transliteration decision, and this
    module does not make it.
    """
    if lang not in ("ja", "zh", "ko"):
        return None
    if is_category_shaped(label):
        return None
    type_words = TYPES.get(p31)
    if not type_words:
        return None
    place = clean_place(place)
    if not place:
        return None
    if p31 in MOSQUE_P31:
        return render_mosque(label, p31, lang, place, latin_rules)
    ded = dedication(label, lang, rules)
    if not ded:
        # ⛔ "No dedication means transliteration" (Emma, 2026-09-18). Until this
        # existed the refusal WAS the answer, and it was the pipeline's biggest
        # gate: 13,470 of 22,548 items. ja only — see `_TRANSLIT_LANGS`.
        ded = transliterate_dedication(label, lang, rules, latin_rules, place_en)
        if ded == PLACE_ONLY:
            return place + _PLACE_JOIN[lang] + type_words[lang]
    if not ded:
        return None
    return place + _PLACE_JOIN[lang] + _kana_join(ded, type_words[lang])
