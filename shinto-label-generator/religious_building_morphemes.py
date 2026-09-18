#!/usr/bin/env python3
"""
religious_building_morphemes.py
===============================
The tables and the parser behind religious-building labels in ja/zh/ko. Pure
logic, no network, so it can be tested without touching Wikidata.

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
}

# Multi-token saint names that must be read as ONE dedicatee. Without this,
# "San Giovanni Battista" renders Giovanni AND Battista and comes out as
# 聖ヨハネ洗礼者ヨハネ教会 — John twice. Checked before single tokens.
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
        # A hyphenated cluster like "st.-petri" carries its own marker.
        parts = [p for p in re.split(r"[-–—]", stem) if p]
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


def dedication(label, lang):
    """The dedication rendered in `lang`, or None if any part is unknown."""
    # Hyphens joined the phrase in the corpus ("Notre-Dame", "Herz-Jesu"), so the
    # phrase lookup saw "notre-dame" and missed. 111 labels turned on this alone.
    low = re.sub(r"[-–—']", " ", _norm(label))
    low = re.sub(r"\s+", " ", low)
    # Longest phrase first, so "sacred heart" beats a bare "heart".
    for phrase in sorted(DEDICATIONS, key=len, reverse=True):
        if phrase in low:
            return DEDICATIONS[phrase][lang]
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
        if t not in NAMES:
            return None          # unknown name — caller decides, not this module
        rendered.append(NAMES[t][lang])
    core = "".join(rendered)
    if saw_saint:
        core = SAINT_PREFIX[lang] + core
    return core


# A place label often carries its own disambiguator -- "Freden (Leine)" gives
# フレーデン (ライネ), and without this the building's label inherits it as
# "フレーデン (ライネ)の聖ラウレンティウス教会". The parenthetical disambiguates the
# PLACE from another place; it says nothing about the building.
_PLACE_PAREN = re.compile(r"\s*[（(\[][^）)\]]*[）)\]]\s*$")


def clean_place(place):
    if not place:
        return place
    return _PLACE_PAREN.sub("", place).strip()


def render(label, p31, lang, place=None):
    """The label in `lang`, or None when any piece is unknown.

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
    ded = dedication(label, lang)
    if not ded:
        return None
    return place + _PLACE_JOIN[lang] + ded + type_words[lang]
