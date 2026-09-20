#!/usr/bin/env python3
"""
saint_qids.py
=============
The dedication terms of `paused/table_audit.tsv` resolved to Wikidata QIDs, and
**validated**, so a `P825` (dedicated to) statement can be built from a parsed
dedication.

## Why the validation is the whole point

`table_audit.tsv` was a lookup done for the LABEL work, where a wrong QID costs
nothing — the labels come from the morpheme table, not from the resolved item.
Used for `P825` it would be asserting a fact, and measured against the live P31
of all 101 rows on 2026-09-19 the table is **52% wrong**:

    painting                    11   the Transfiguration -> Raphael's painting of it
    commune of France            6   Saint Joseph -> a commune in Martinique
    Catholic church building     5   Our Lady Queen of Heaven -> a church in Bayswater
    church building              4
    icon                         3   Our Lady of Kazan -> the icon itself
    film                         2   the Holy Innocents -> a 1984 Mario Camus film
    album, audio track,          6   the Ascension -> a Sufjan Stevens album
    scholarly article, TV
    episode, girl group,
    family name
    city, island, parish,        7   Saint Thomas -> a US Virgin Islands island
    municipality, comune
    no QID resolved              7

The queue item named one of these — *"All Saints -> Q165386 is a girl group"*.
It is not an outlier. **Unvalidated, this table would have dedicated churches to
French communes, a film and an album.**

## ⛔ An explicit allow-list, because unlisted means refuse

`ALLOWED_CLASSES` is what a dedicatee may BE: a person, an angel, a deity, a
Marian title, a dogma, a feast. Anything whose P31 is not in it refuses, which
is the same doctrine `romance_katakana.rules_for_country` holds — a default is
how the wrong answer gets in.

⛔ **A DEPICTION of X is not X.** Paintings, panel paintings, triptychs, icons,
statues and artistic themes are all refused, and they are the largest refused
group. `the Transfiguration -> Q2344437` is Raphael's canvas; the feast has its
own item and this lookup did not find it. `Our Lady of Kazan -> Q540173` is the
physical icon in Kazan Cathedral, which is a real thing a church could be
dedicated to and is still not the Marian title the label names. Both refuse, and
the line is the same one `generate_honzon_quickstatements` holds when it refuses
`P825 -> 重要文化財`: a designation, or a depiction, is not the dedicatee.

⚠ **A REFUSED row is not a resolved-and-rejected term** — it is a term whose QID
is unknown. `REFUSED` records the wrong answer so the next lookup does not
rediscover it, not so the term is written off.

## ⭐ The QID identifies; the TABLE renders (Emma, 2026-09-19)

The queue item said *"the saint reading comes from WIKIDATA's label on the
resolved QID, not from my table"*. Measured over the 49 validated terms, **25 of
the ja labels and 36 of the zh differ** — and the differences are not noise:

    ja   mine フランチェスコ      wikidata アッシジのフランチェスコ
         mine ニコラオス         wikidata ミラのニコラオス
         mine カタリナ          wikidata アレクサンドリアのカタリナ
    zh   mine 安德肋            wikidata 安得烈      (Catholic -> Protestant)
         mine 巴尔巴拉           wikidata 白芭蕾      (Catholic -> transliteration)

Wikidata's labels are **disambiguated full names**, which is the right way to
identify a person and the wrong way to name a church: the place slot already
carries a の, so `リヨンのアッシジのフランチェスコ教会` reads with two, and
Assisi is not where the building is. And the zh column would reverse the
deliberate Catholic register that `docs/script-rationale/religious_building_
morphemes_2026-09.md` §9 records.

Put to Emma as a conflict between two documented rules, she chose to split the
two uses rather than pick a side: **the resolved QID is what goes in `P825`, and
the table is what renders the label.** So this module supplies identity and
never a string.

## What this does NOT do

It does not emit anything. `P825` generation is a separate step and is not built
yet: the morpheme table keys on bare tokens (`andrew`, `nicholas`) while these
terms are phrases (`Saint Andrew`, `Our Lady of Kazan`), and joining them is its
own job with its own measurement.
"""

ALLOWED_CLASSES = {
    "Q5": "human",
    "Q20643955": "human biblical figure",
    "Q21070568": "human whose existence is disputed",
    "Q113371917": "legendary saint",
    "Q28914": "patron saint",
    "Q13002315": "legendary figure",
    "Q3375731": "historical character",
    "Q4271324": "mythical character",
    "Q178342": "archangel",
    "Q10822464": "angels in Christianity",
    "Q690175": "angel in Judaism",
    "Q4306757": "Mukarrabun",
    "Q18563360": "Quranic character",
    "Q178885": "deity",
    "Q825": "God in Christianity",
    "Q1509831": "titles of Mary, mother of Jesus",
    "Q507850": "Marian apparition",
    "Q620749": "dogma",
    # ⭐ Added 2026-09-20 from measured evidence, not intuition: the 101-row seed
    # was people-heavy and never contained a devotion or a feast, so the first
    # allow-list refused `Holy Trinity`, `Sacred Heart` and `Intercession of the
    # Theotokos` — each of them the correct answer, each refused for a class the
    # sample happened not to include.
    "Q3045134": "Christian dogma",
    "Q2634521": "title of Jesus",          # the parallel of Q1509831 for Mary
    "Q1445650": "holiday",                 # a feast; the narrower Q375011 missed it
    # ⭐ Round three, 2026-09-20, same method: the class of the item being wrongly
    # refused, read rather than guessed. `Holy Family` is a GROUP of dedicatees
    # and `Holy Spirit` a person of the Trinity.
    "Q22813674": "group of biblical humans",
    "Q651118": "hypostasis",
    # ⛔ NOT added, though both sit on those same two items: `family` (Q8436) and
    # `triad` (Q29430681) are ordinary classes of ordinary things, and
    # `biblical concept` (Q30149195) would admit covenant and sin. The allow-list
    # earns its name by refusing the classes that merely happen to be attached.
    "Q375011": "religious holiday",
    "Q106355253": "gospel episode",
    "Q13418847": "historical event",
    "Q1363686": "entering heaven alive",
    "Q82821": "tradition",
    "Q12827256": "myth",
}

SAINT_QIDS = {
    "Our Lady":                        "Q345",       # Mary
    "Our Lady Help of Christians":     "Q1895556",   # Mary Help of Christians
    "Our Lady Star of the Sea":        "Q1186717",   # Our Lady, Star of the Sea
    "Our Lady of Consolation":         "Q2457205",   # Our Lady of Consolation
    "Our Lady of Częstochowa":         "Q573619",    # Black Madonna of Częstochowa
    "Our Lady of Fátima":              "Q719524",    # Our Lady of Fátima
    "Our Lady of Grace":               "Q1636804",   # Our Lady of Graces
    "Our Lady of Guadalupe":           "Q31877",     # Our Lady of Guadalupe
    "Our Lady of Guidance":            "Q18216847",  # Our Lady of Guidance
    "Our Lady of Light":               "Q240236",    # Our Lady of Zeitoun
    "Our Lady of Loreto":              "Q9094350",   # Our Lady of Loreto
    "Our Lady of Lourdes":             "Q21532387",  # Our Lady of Lourdes
    "Our Lady of Mercy":               "Q176813",    # Virgin of Mercy
    "Our Lady of Miracles":            "Q19863175",  # Our Lady of Miracles
    "Our Lady of Mount Carmel":        "Q1065053",   # Our Lady of Mount Carmel
    "Our Lady of Perpetual Help":      "Q178754",    # Our Lady of Perpetual Help
    "Our Lady of Remedies":            "Q28804196",  # Our Lady of Remedies
    "Our Lady of Sorrows":             "Q1196075",   # Our Lady of Sorrows
    "Our Lady of the Angels":          "Q3949145",   # Virgin of the Angels
    "Our Lady of the Rosary":          "Q54875",     # Our Lady of the Rosary
    "Our Lady of the Snows":           "Q263827",    # Our Lady of the Snows
    "Saint Andrew":                    "Q43399",     # Andrew the Apostle
    "Saint Anne":                      "Q164294",    # Saint Anne
    "Saint Anthony":                   "Q170547",    # Anthony the Great
    "Saint Barbara":                   "Q192816",    # Saint Barbara
    "Saint Boniface":                  "Q160445",    # Saint Boniface
    "Saint Catherine":                 "Q179718",    # Catherine of Alexandria
    "Saint Christopher":               "Q193507",    # Saint Christopher
    "Saint Elijah":                    "Q133507",    # Elijah
    "Saint Francis":                   "Q676555",    # Francis of Assisi
    "Saint George":                    "Q48438",     # Saint George
    "Saint John the Baptist":          "Q40662",     # John the Baptist
    "Saint Mamas":                     "Q532019",    # Mammes of Caesarea
    "Saint Mary":                      "Q345",       # Mary
    "Saint Matthew":                   "Q43600",     # Matthew the Apostle
    "Saint Michael":                   "Q45581",     # Michael
    "Saint Nicholas":                  "Q44269",     # Saint Nicholas
    "Saint Peregrine":                 "Q141838",    # Peregrine Laziosi
    "Saint Peter":                     "Q33923",     # Saint Peter
    "Saint Pius":                      "Q43739",     # Pius X
    "Saint Stanislaus":                "Q203437",    # Stanislaus Kostka
    "Saint Stephen":                   "Q161775",    # Saint Stephen
    "Saint Teresa":                    "Q174880",    # Teresa of Ávila
    "the Annunciation":                "Q154326",    # Annunciation
    "the Archangel":                   "Q45581",     # Michael
    "the Assumption":                  "Q162691",    # Assumption of Mary
    "the Nativity":                    "Q51628",     # Nativity of Jesus
    "the Saviour":                     "Q302",       # Jesus Christ
}

REFUSED = {
    "All Saints":                      ("Q165386",    "all-female band, girl group"),
    "Corpus Christi":                  ("Q49242",     "city in the United States, county seat, big city"),
    "Our Lady Joy of All Who Sorrow":  ("-",          "no QID resolved"),
    "Our Lady Queen of Heaven":        ("Q26521357",  "Catholic church building"),
    "Our Lady Queen of Poland":        ("Q11745453",  "church building, architectural heritage monument"),
    "Our Lady of Good Help":           ("Q137802787", "Catholic church building"),
    "Our Lady of Kazan":               ("Q540173",    "icon"),
    "Our Lady of Pity":                ("Q133250793", "church building"),
    "Our Lady of Smolensk":            ("Q1998132",   "icon"),
    "Our Lady of Vladimir":            ("Q546241",    "icon, painting"),
    "Our Lady of the Scapular":        ("Q11745268",  "church building, architectural heritage monument"),
    "Our Lady of the Sign":            ("Q597232",    "artistic theme"),
    "Peace":                           ("Q7157305",   "family name"),
    "Saint Anthony the Abbot":         ("Q3948786",   "painting"),
    "Saint Christ":                    ("Q1218032",   "commune of France"),
    "Saint Demetrius":                 ("Q106772315", "painting"),
    "Saint Isidore":                   ("Q3462458",   "municipality"),
    "Saint James":                     ("Q28723548",  "commune of France, human settlement"),
    "Saint John":                      ("Q2082",      "big city, city in Newfoundland and Labrador"),
    "Saint Joseph":                    ("Q918737",    "commune of France"),
    "Saint Lawrence":                  ("Q509090",    "parish of Jersey"),
    "Saint Marina":                    ("Q24039028",  "painting"),
    "Saint Martin":                    ("Q126125",    "overseas collectivity of France, dependent territory"),
    "Saint Maurice":                   ("Q274327",    "commune of France"),
    "Saint Paraskeva":                 ("Q46973192",  "painting"),
    "Saint Paul":                      ("Q316887",    "commune of France, big city"),
    "Saint Roch":                      ("Q961984",    "commune of France"),
    "Saint Terentian":                 ("-",          "no QID resolved"),
    "Saint Thomas":                    ("Q463937",    "island, human settlement"),
    "Saint Vincent":                   ("Q35436",     "comune of Italy"),
    "the Ascension":                   ("Q96759287",  "album"),
    "the Dormition":                   ("Q116916223", "painting"),
    "the Entry of the Theotokos":      ("-",          "no QID resolved"),
    "the Epiphany":                    ("Q2276130",   "painting, triptych"),
    "the Exaltation of the Holy Cross": ("-",          "no QID resolved"),
    "the Holy Cross":                  ("Q105104231", "church building"),
    "the Holy Innocents":              ("Q1630061",   "film"),
    "the Holy Spirit":                 ("Q139680635", "painting"),
    "the Holy Trinity":                ("Q6553555",   "painting"),
    "the Immaculate Conception":       ("Q140667408", "painting"),
    "the Immaculate Heart of Mary":    ("Q137884092", "Catholic church building"),
    "the Most Precious Blood":         ("Q137841909", "Catholic church building"),
    "the Nativity of the Lord":        ("-",          "no QID resolved"),
    "the Nativity of the Theotokos":   ("-",          "no QID resolved"),
    "the Presentation":                ("Q114487233", "television series episode"),
    "the Protection of the Theotokos": ("-",          "no QID resolved"),
    "the Resurrection":                ("Q106923112", "audio track, music track without lyrics"),
    "the Rosary":                      ("Q64225601",  "film"),
    "the Sacred Heart":                ("Q137884480", "Catholic church building"),
    "the Theotokos":                   ("Q125759304", "scholarly article"),
    "the Transfiguration":             ("Q2344437",   "painting"),
    "the Visitation":                  ("Q21806457",  "painting, panel painting"),
}


def qid_for(term):
    """The validated QID for a dedication term, or None.

    None means "no QID known", whether the term was never resolved or resolved
    to something that is not a dedicatee. A caller must never fall back to
    `REFUSED` — that is the wrong answer, kept on purpose.
    """
    return SAINT_QIDS.get(term)

# ⭐ Dedication CONCEPTS, keyed by what the table renders them as (2026-09-20).
#
# The unit is the concept, not the table key: `assunta`, `asunción` and
# `mariä himmelfahrt` are one Assumption, `martin` and `martino` one saint. Two
# table entries that render to the same Japanese string are the same thing —
# the join that took NAMES coverage from 18 keys to 63.
#
# Every line was produced by `resolve_dedication_qids.py`, which searches, then
# filters on ALLOWED_CLASSES, then accepts ONLY when exactly one candidate
# survives — and then read by hand, because a search engine's first hit is what
# made the 101-row seed 52% wrong. The refusals it printed are in the docstring
# of that script; they are refusals of behaviour, not of the concept.
QID_BY_RENDERING = {
    "至聖三者":        "Q37090",     #  297 slots  Holy Trinity — Christian conception of God a
    "聖母被昇天":       "Q162691",    #  262 slots  Assumption of Mary — the bodily taking up of
    "マルティヌス":      "Q133704",    #  232 slots  Martin of Tours — Christian saint (c.316/336
    "洗礼者ヨハネ":      "Q40662",     #  190 slots  John the Baptist — 1st-century Jewish itiner
    "イエスの聖心":      "Q408284",    #  189 slots  Sacred Heart — Christian devotion symbolisin
    "ラウレンティウス":    "Q17590",     #  143 slots  Lawrence of Rome — Christian saint, martyr a
    "生神女誕生":       "Q501107",    #  121 slots  Nativity of Mary — feast day
    "生神女庇護":       "Q1410684",   #  111 slots  Intercession of the Theotokos — protection o
    "ロクス":         "Q152457",    #  104 slots  Saint Roch — Christian saint (c.1348 - c.137
    "カルメル山の聖母":    "Q1065053",   #  103 slots  Our Lady of Mount Carmel — title of the Virg
    "主の変容":        "Q201201",    #   91 slots  Transfiguration of Jesus — episode in the li
    "主の昇天":        "Q5686605",   #   82 slots  Ascension of Jesus — in Christianity, the de
    "生神女就寝":       "Q4069073",   #   65 slots  Dormition of the Mother of God — Great Feast
    "恩寵の聖母":       "Q1636804",   #   65 slots  Our Lady of Graces — title of the Virgin Mar
}

# ── Second round, 2026-09-20 ─────────────────────────────────────────────
# Same script, same acceptance rule, same hand review. ⚠ The review earned
# its keep: the script accepted `諸聖人 -> Q10405623`, whose own description
# says "Swedish Christian festival, DISTINCT FROM THE MORE COMMON" one — 56
# churches would have been dedicated to a Swedish national holiday. It is
# refused, and the general item was not found (Q18378, my guess at it, is an
# Italian comune). A better query for it is next round's job.
QID_BY_RENDERING.update({
    "ヨセフ":         "Q128267",    #  137 slots  Saint Joseph — Christian saint; husband of
    "バルトロマイ":      "Q43982",     #   84 slots  Bartholomew the Apostle — Christian apostl
    "復活":          "Q51624",     #   78 slots  Resurrection of Jesus — event in the Chris
    "セバスティアヌス":    "Q183332",    #   70 slots  Saint Sebastian — Christian saint and mart
    "王たるキリスト":     "Q2558835",   #   57 slots  Christ the King — title of Jesus
    "パウロ":         "Q9200",      #   53 slots  Paul the Apostle — Early Christian apostle
    "ウィトゥス":       "Q212850",    #   49 slots  Vitus — 3rd or 4th-century Sicilian saint
    "レオンハルト":      "Q558148",    #   46 slots  Leonard of Noblac — Frankish saint
    "パラスケヴィ":      "Q13564538",  #   42 slots  Paraskevi of Iconium — Christian martyr
    "天の元后":        "Q1358870",   #   40 slots  Queen of Heaven — Christian devotion of Ma
    "聖母の汚れなき御心":   "Q748124",    #   40 slots  Immaculate Heart of Mary — title of Mary, 
    "マグダラのマリア":    "Q63070",     #   33 slots  Mary Magdalene — follower of Jesus (–100)
})

# ⭐ Hand-resolved where the script refused for MORE THAN ONE survivor and the
# identity is not actually in doubt. The script exists to avoid making a
# judgement silently, not to forbid one being made and written down.
QID_BY_RENDERING.update({
    # Q302 is "central figure of Christianity"; the other survivors were an
    # American Internet personality of the same name and the Last Supper.
    "キリスト": "Q302",                 #   91 slots
    # ⚠ A judgement, not an identity: Q185606 is the DOCTRINE ("Mary was
    # conceived free from original sin") and Q3538509 is the FEAST on
    # 8 December. A church called Immaculate Conception is dedicated to the
    # mystery, not to the day in the calendar. Recorded so it can be
    # overturned by anyone who reads it and disagrees.
    "無原罪の御宿り": "Q185606",          #  132 slots
})



# ── Round three, 2026-09-20 ───────────────────────────────────────────────
# `Holy Family` and `Holy Spirit` were refused by class until the allow-list
# learned "group of biblical humans" and "hypostasis"; `Visitation` needed a
# SHORTER query — `Visitation of the Blessed Virgin Mary` matched only
# churches and a monastery, because a longer query is a narrower text match
# and not a more precise one.
QID_BY_RENDERING.update({
    "聖母訪問":        "Q691810",    #   89 slots  Visitation — Christian story of Mary visit
    "聖霊":          "Q37302",     #   85 slots  Holy Spirit — conception of God, or an att
    "聖家族":         "Q618057",    #   54 slots  Holy Family — Jesus, Mary and Saint Joseph
})


# ⛔ CANDIDATES A HUMAN REVIEW HAS ALREADY REJECTED, so the resolver cannot
# re-offer them. Without this the script proposed `諸聖人 -> Q10405623` in round
# two, the review rejected it, and round three proposed the identical line —
# because nothing had recorded the rejection. A rejection that is not written
# down is a rejection that gets re-offered until somebody installs it.
#
# ⚠ Keyed by (rendering, qid): the CONCEPT is not rejected, this ANSWER for it is.
# `諸聖人` is still wanted; `Q10405623` is not the item.
REJECTED_BY_REVIEW = {
    ("諸聖人", "Q10405623"):
        "the SWEDISH All Saints' Day — its own description says 'distinct from "
        "the more common' one. One surviving candidate, correct class, and wrong "
        "by 56 churches. Q18378, reached for as the general item, is an Italian "
        "comune; the right one has not been found.",
}


def rejected(ja, qid):
    """True when a human review has already turned this exact answer down."""
    return (ja, qid) in REJECTED_BY_REVIEW


def _term_index():
    """{ja rendering: qid} for the TERM map, via the table key each term names.

    ⛔ `qid_for_match` originally read `QID_BY_RENDERING` alone, so the 48 terms
    in `SAINT_QIDS` — the whole first lookup — were invisible to it. The P825
    generator emitted 2,168 statements from 14 distinct dedicatees where the
    measurement had said 4,155 from all of them, and the two maps were the
    difference. A map nothing reads is not a map.

    The join is the same one used everywhere here: a term normalises to a table
    key, and a key renders to a Japanese string that identifies the concept.
    """
    import religious_building_morphemes as _m
    out = {}
    for term, qid in SAINT_QIDS.items():
        low = _m._fold(term.lower())
        forms = {low}
        for prefix in ("saint ", "st ", "st. ", "the ", "our lady of the ",
                       "our lady of ", "our lady "):
            if low.startswith(prefix):
                forms.add(low[len(prefix):].strip())
        for form in forms:
            if not form:
                continue
            row = (_m.NAMES.get(form) or _m.DEDICATIONS.get(form)
                   or _m.NAME_PHRASES.get(form))
            if row:
                out.setdefault(row["ja"], qid)
                break
    return out


_BY_RENDERING = None


def _index():
    """Both maps, keyed by rendering. `QID_BY_RENDERING` wins — it is the later,
    script-validated lookup and the terms it overlaps were cross-checked."""
    global _BY_RENDERING
    if _BY_RENDERING is None:
        merged = _term_index()
        merged.update(QID_BY_RENDERING)
        _BY_RENDERING = merged
    return _BY_RENDERING


def qids_for_match(hit):
    """EVERY dedicatee a match names, as a list — [] when any is unknown.

    `Santi Pietro e Paolo` is dedicated to two people and wants two `P825`
    statements. `qid_for_match` returns None for it on purpose, because ONE
    statement would assert the label names one dedicatee; this returns both.

    ⛔ A NAME_PHRASES entry is not automatically a pair. The table mixes two
    shapes that look identical from the key:

        peter paul       -> Peter AND Paul          two dedicatees
        antonio padova   -> Anthony OF PADUA        one dedicatee, one place
        john nepomuk     -> John OF NEPOMUK         one dedicatee, one place

    Splitting the second kind would dedicate a church to the city of Padua —
    the same class of error that put French communes in the seed. A phrase
    splits only when **every** part is itself a NAMES key: `peter` and `paul`
    are, `padova` and `nepomuk` and `assisi` and `thessaloniki` are not.

    ⚠ And a phrase whose parts are not all names is NOT resolved from its first
    part either. `antonio` happens to map to Anthony of Padua today, so
    `antonio padova` would come out right by luck; if it had resolved to Anthony
    the Abbot the same code would be silently wrong. Those phrases stay
    unresolved until the phrase itself has a QID.

    ⛔ All-or-nothing. A label naming three saints where two resolve emits
    nothing, because two statements assert the label named two.
    """
    if not hit:
        return []
    import religious_building_morphemes as _m
    kind, key, _extra = hit
    index = _index()
    if kind in ("specific", "generic"):
        row = _m.DEDICATIONS.get(key)
        qid = index.get(row["ja"]) if row else None
        return [qid] if qid else []
    if kind == "phrase":
        row = _m.NAME_PHRASES.get(key)
        qid = index.get(row["ja"]) if row else None
        if qid:
            return [qid]
        parts = key.split()
        if len(parts) > 1 and all(p in _m.NAMES for p in parts):
            qids = [index.get(_m.NAMES[p]["ja"]) for p in parts]
            if all(qids) and len(set(qids)) == len(qids):
                return qids
        return []
    qids = [index.get(_m.NAMES[k]["ja"]) if k in _m.NAMES else None for k in key]
    if not all(qids) or len(set(qids)) != len(qids):
        return []
    return qids


def qid_for_match(hit):
    """The QID for a `match_dedication()` result, or None.

    ⛔ Returns None for a multi-name match. `Santi Martino e Giorgio` is
    dedicated to two saints and `P825` would need two statements; emitting
    one of them silently asserts the label names one dedicatee. The caller
    decides whether to emit a pair, which is not a decision this file makes.
    """
    if not hit:
        return None
    kind, key, _extra = hit
    import religious_building_morphemes as _m
    if kind in ("specific", "generic"):
        row = _m.DEDICATIONS.get(key)
    elif kind == "phrase":
        row = _m.NAME_PHRASES.get(key)
    else:
        if len(key) != 1:
            return None
        row = _m.NAMES.get(key[0])
    return _index().get(row["ja"]) if row else None
