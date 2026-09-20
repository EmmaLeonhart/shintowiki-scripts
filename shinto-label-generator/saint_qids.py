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
