"""
Generate multi-language labels for the "List of Shikinaisha" (式内社一覧) items.

Q11064932 (Engishiki Jinmyōchō / 延喜式神名帳) has P527 (has part) pointing at 69
per-province "List of Shikinaisha in X Province" items. Those 70 items currently
carry labels only in ja/en/ar/tok (and fr on the 69). This script mass-generates
labels for every OTHER language the sub-project already produces shrine/temple
names for (language_registry.COVERED), reusing the existing transliteration
machinery, and writes a single standalone QuickStatements file:

    quickstatements/shikinaisha_lists.txt

Framing convention (from the already-present ar/tok/fr labels):
    [list-word] [Shikinaisha] [in] [province-word] {ProvinceName}
where the province name is transliterated per-script (Latin-script languages keep
the plain romaji, e.g. fr "Yamashiro"; ar/Cyrillic/etc. transliterate). The
loanword "Shikinaisha" and the parent proper-name "Engishiki Jinmyōchō" are
transliterated the same way.

CJK (zh family + ko) is derived from the JAPANESE kanji label rather than the
romaji, because the kanji province name is the accurate source there.

Non-destructive: for each (item, language) pair, a label is emitted ONLY when the
item does not already have a label in that language. So ar/tok are skipped
everywhere, fr only fills the one missing parent item, etc.

The per-language frame phrasing below is hand-authored from each Wikipedia's
list-title conventions; the province/loanword slots are automated. Frames flagged
"best-effort" are the ones most worth a native-speaker check later.

Output: quickstatements/shikinaisha_lists.txt
"""

import os
import sys
import io
import re
import time
import requests

# Reuse the transliteration machinery from the sibling generators.
from generate_multilang_quickstatements import (
    cyrillicize, arabify, farsify, hindify, bengalify, marathify, assamify,
    grecify, hebraify, czechify, slovenify, lithuanize,
)
from generate_chinese_quickstatements import japanese_to_chinese, zh_variants
from koreanizer import koreanize
import hanja

from language_registry import COVERED

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": WIKIDATA_USER_AGENT}
PARENT_QID = "Q11064932"
API = "https://www.wikidata.org/w/api.php"


def _ensure_utf8_stdout():
    if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    elif hasattr(sys.stdout, "encoding") and sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-language frames.
#
# Each entry: (prov_tmpl, palace_tmpl, parent_tmpl, translit)
#   prov_tmpl   : "List of {shiki} in {prov} Province" form, {shiki}+{prov} slots
#   palace_tmpl : the "Imperial Palace" special case, {shiki} slot
#   parent_tmpl : Engishiki Jinmyōchō itself, {engi} slot (transliterated name)
#   translit    : function(romaji)->script for the prov/shiki/engi slots, or None
#                 to keep the plain romaji (Latin-script languages).
#
# CJK languages (zh family + ko) are NOT in this table; they are built from the
# Japanese kanji label in build_cjk().
# ---------------------------------------------------------------------------

def _arz(n):
    return arabify(n).replace("غ", "ج")


def _ru(n):
    return cyrillicize(n, "ru")


def _uk(n):
    return cyrillicize(n, "uk")


# translit=None  -> keep plain romaji (Latin-script languages)
FRAMES = {
    # ---- Latin-script, plain-romaji province ----
    "tr":  ("{prov} vilayetindeki {shiki} listesi", "İmparatorluk Sarayı'ndaki {shiki} listesi", "{engi}", None),
    "de":  ("Liste der {shiki} in der Provinz {prov}", "Liste der {shiki} im Kaiserpalast", "{engi}", None),
    "nl":  ("Lijst van {shiki} in de provincie {prov}", "Lijst van {shiki} in het keizerlijk paleis", "{engi}", None),
    "es":  ("Lista de {shiki} en la provincia de {prov}", "Lista de {shiki} en el Palacio Imperial", "{engi}", None),
    "it":  ("Lista degli {shiki} nella provincia di {prov}", "Lista degli {shiki} nel Palazzo Imperiale", "{engi}", None),
    "eu":  ("{prov} probintziako {shiki} zerrenda", "Jauregi Inperialeko {shiki} zerrenda", "{engi}", None),
    "fr":  ("liste des {shiki} dans la province de {prov}", "liste des {shiki} du palais impérial", "{engi}", None),
    "pt":  ("Lista de {shiki} na província de {prov}", "Lista de {shiki} no Palácio Imperial", "{engi}", None),
    "vi":  ("Danh sách {shiki} ở tỉnh {prov}", "Danh sách {shiki} trong Hoàng cung", "{engi}", None),
    "ca":  ("Llista de {shiki} a la província de {prov}", "Llista de {shiki} al Palau Imperial", "{engi}", None),
    "gl":  ("Lista de {shiki} na provincia de {prov}", "Lista de {shiki} no Palacio Imperial", "{engi}", None),
    "sv":  ("Lista över {shiki} i provinsen {prov}", "Lista över {shiki} i det kejserliga palatset", "{engi}", None),
    "nb":  ("Liste over {shiki} i provinsen {prov}", "Liste over {shiki} i det keiserlige palasset", "{engi}", None),
    "da":  ("Liste over {shiki} i provinsen {prov}", "Liste over {shiki} i det kejserlige palads", "{engi}", None),
    "nn":  ("Liste over {shiki} i provinsen {prov}", "Liste over {shiki} i det keisarlege palasset", "{engi}", None),
    "hu":  ("{prov} tartomány {shiki}-listája", "A császári palota {shiki}-listája", "{engi}", None),        # best-effort
    "la":  ("Index {shiki} in provincia {prov}", "Index {shiki} in Palatio Imperatorio", "{engi}", None),    # best-effort
    "ast": ("Llista de {shiki} na provincia de {prov}", "Llista de {shiki} nel Palaciu Imperial", "{engi}", None),
    "sh":  ("Popis {shiki} u provinciji {prov}", "Popis {shiki} u Carskoj palači", "{engi}", None),
    "hr":  ("Popis {shiki} u provinciji {prov}", "Popis {shiki} u Carskoj palači", "{engi}", None),
    "az":  ("{prov} əyalətindəki {shiki} siyahısı", "İmperiya Sarayındakı {shiki} siyahısı", "{engi}", None),  # best-effort
    "tl":  ("Listahan ng mga {shiki} sa Lalawigan ng {prov}", "Listahan ng mga {shiki} sa Palasyong Imperyal", "{engi}", None),
    "war": ("Talaan han mga {shiki} ha Probinsya han {prov}", "Talaan han mga {shiki} ha Imperyal nga Palasyo", "{engi}", None),  # best-effort
    "min": ("Daftar {shiki} di Provinsi {prov}", "Daftar {shiki} di Istano Kaisar", "{engi}", None),
    "eo":  ("Listo de {shiki} en la provinco {prov}", "Listo de {shiki} en la Imperia Palaco", "{engi}", None),
    "jv":  ("Dhaptar {shiki} ing Provinsi {prov}", "Dhaptar {shiki} ing Kadhaton Kaisar", "{engi}", None),     # best-effort
    "ms":  ("Senarai {shiki} di Wilayah {prov}", "Senarai {shiki} di Istana Diraja", "{engi}", None),
    "br":  ("Roll {shiki} e provins {prov}", "Roll {shiki} e Palez an Impalaer", "{engi}", None),              # best-effort
    "ceb": ("Listahan sa mga {shiki} sa Lalawigan sa {prov}", "Listahan sa mga {shiki} sa Imperyal nga Palasyo", "{engi}", None),
    "pl":  ("Lista {shiki} w prowincji {prov}", "Lista {shiki} w Pałacu Cesarskim", "{engi}", None),
    "ro":  ("Lista {shiki} din provincia {prov}", "Lista {shiki} din Palatul Imperial", "{engi}", None),
    "fi":  ("Luettelo {prov}n provinssin {shiki}-pyhäköistä", "Luettelo keisarillisen palatsin {shiki}-pyhäköistä", "{engi}", None),  # best-effort
    "id":  ("Daftar {shiki} di Provinsi {prov}", "Daftar {shiki} di Istana Kekaisaran", "{engi}", None),

    # ---- Slavic Latin transcription (province + loanword transliterated) ----
    "cs":  ("Seznam {shiki} v provincii {prov}", "Seznam {shiki} v císařském paláci", "{engi}", czechify),
    "sl":  ("Seznam {shiki} v provinci {prov}", "Seznam {shiki} v cesarski palači", "{engi}", slovenify),

    # ---- Cyrillic ----
    "ru":  ("Список {shiki} провинции {prov}", "Список {shiki} императорского дворца", "{engi}", _ru),
    "uk":  ("Список {shiki} провінції {prov}", "Список {shiki} імператорського палацу", "{engi}", _uk),

    # ---- Perso-Arabic ----
    "fa":  ("فهرست {shiki} در استان {prov}", "فهرست {shiki} در کاخ امپراتوری", "{engi}", farsify),
    "ur":  ("صوبہ {prov} کے {shiki} کی فہرست", "شاہی محل کے {shiki} کی فہرست", "{engi}", farsify),  # best-effort

    # ---- Arabic (ar already present everywhere; arz still missing) ----
    "arz": ("قايمة {shiki} فى مقاطعة {prov}", "قايمة {shiki} فى القصر الإمبراطورى", "{engi}", _arz),  # best-effort

    # ---- Devanagari ----
    "hi":  ("{prov} प्रांत के {shiki} की सूची", "शाही महल के {shiki} की सूची", "{engi}", hindify),
    "mai": ("{prov} प्रांत केर {shiki} केर सूची", "शाही महल केर {shiki} केर सूची", "{engi}", hindify),  # best-effort
    "mr":  ("{prov} प्रांतातील {shiki} यांची यादी", "राजवाड्यातील {shiki} यांची यादी", "{engi}", marathify),  # best-effort

    # ---- Bengali script ----
    "bn":  ("{prov} প্রদেশের {shiki} তালিকা", "রাজপ্রাসাদের {shiki} তালিকা", "{engi}", bengalify),
    "as":  ("{prov} প্ৰদেশৰ {shiki} তালিকা", "ৰাজপ্ৰাসাদৰ {shiki} তালিকা", "{engi}", assamify),  # best-effort

    # ---- Greek ----
    "el":  ("Κατάλογος {shiki} στην επαρχία {prov}", "Κατάλογος {shiki} στο Αυτοκρατορικό Παλάτι", "{engi}", grecify),

    # ---- Hebrew ----
    "he":  ("רשימת {shiki} במחוז {prov}", "רשימת {shiki} בארמון הקיסרי", "{engi}", hebraify),

    # ---- Lithuanian ----
    "lt":  ("{prov} provincijos {shiki} sąrašas", "Imperatoriaus rūmų {shiki} sąrašas", "{engi}", lithuanize),
}

# CJK families handled separately (from the Japanese kanji label).
ZH_CODES = ["zh", "zh-hant", "zh-tw", "zh-hk", "zh-hans", "zh-cn", "zh-sg", "gan", "zh-mo"]

# The two loanwords, in plain romaji, that fill the {shiki} / {engi} slots.
SHIKI_ROMAJI = "shikinaisha"
ENGI_ROMAJI = "engishiki jinmyocho"
SHIKI_LATIN = "Shikinaisha"
ENGI_LATIN = "Engishiki Jinmyōchō"


# ---------------------------------------------------------------------------
# Fetch the 70 items and their existing labels.
# ---------------------------------------------------------------------------

def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fetch_items():
    """Return [{qid, ja, en, langs:set, kind, prov_romaji, ja_core}] for the parent
    + all 69 P527 parts."""
    r = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{PARENT_QID}.json",
                     headers=UA, timeout=60)
    r.raise_for_status()
    parent = r.json()["entities"][PARENT_QID]
    parts = [s["mainsnak"]["datavalue"]["value"]["id"] for s in parent["claims"]["P527"]]
    all_qids = [PARENT_QID] + parts
    print(f"Parent {PARENT_QID} has {len(parts)} P527 parts -> {len(all_qids)} items total.")

    items = []
    for chunk in _chunks(all_qids, 50):
        r = requests.get(API, headers=UA, timeout=60, params={
            "action": "wbgetentities", "ids": "|".join(chunk),
            "props": "labels", "format": "json"})
        r.raise_for_status()
        ents = r.json()["entities"]
        for qid in chunk:
            L = ents[qid].get("labels", {})
            ja = L.get("ja", {}).get("value", "")
            en = L.get("en", {}).get("value", "")
            items.append(_classify(qid, ja, en, set(L.keys())))
        time.sleep(0.3)
    return items


_EN_PREFIX = "List of Shikinaisha in "
_JA_SUFFIX = "の式内社一覧"
_JA_PALACE_CORE = "宮中・京中"


def _classify(qid, ja, en, langs):
    """Determine kind + parse the province name. Kind is driven by the JAPANESE
    label (reliable: every province is '{X}国の式内社一覧', only the palace is
    '宮中・京中の...'); the romaji province name comes from the English label,
    which is irregular ('X Province', 'X Province (Chiba)', 'Iki Island',
    'Tsushima'). ja_core is the kanji core ('山城国', '安房国', ...) used for CJK."""
    prov_core, prov_disambig, ja_core = None, None, None
    ja_core_raw = ja[:-len(_JA_SUFFIX)] if ja.endswith(_JA_SUFFIX) else None
    if qid == PARENT_QID:
        kind = "parent"
    elif ja_core_raw == _JA_PALACE_CORE:
        kind = "palace"
        ja_core = ja_core_raw
    else:
        kind = "province"
        ja_core = ja_core_raw
        prov_core, prov_disambig = _parse_en_province(en)
    return {"qid": qid, "ja": ja, "en": en, "langs": langs, "kind": kind,
            "prov_core": prov_core, "prov_disambig": prov_disambig, "ja_core": ja_core}


def _parse_en_province(en):
    """'List of Shikinaisha in Awa Province (Chiba)' -> ('Awa', 'Chiba');
    'Yamashiro Province' -> ('Yamashiro', None); 'Iki Island' -> ('Iki', None);
    'Tsushima' -> ('Tsushima', None)."""
    rest = en[len(_EN_PREFIX):] if en.startswith(_EN_PREFIX) else en
    disambig = None
    m = re.search(r"\s*\(([^)]*)\)\s*$", rest)
    if m:
        disambig = m.group(1).strip()
        rest = rest[:m.start()]
    rest = re.sub(r"\s+(Province|Island)$", "", rest).strip()
    return rest, disambig


def _render_prov(translit, core, disambig):
    """Render the province name for one language: keep romaji when translit is
    None (Latin-script), otherwise transliterate core and disambiguator
    separately so 'Awa (Chiba)' -> 'Ава (Тиба)' rather than mangling the parens.
    Returns None if the core can't be rendered."""
    if translit is None:
        base = core
        return f"{base} ({disambig})" if disambig else base
    t = translit(core)
    if not t:
        return None
    if disambig:
        td = translit(disambig)
        if td:
            t = f"{t} ({td})"
    return t


# ---------------------------------------------------------------------------
# Label building.
# ---------------------------------------------------------------------------

def build_alpha(lang, item):
    """Build a label for a non-CJK covered language, or None if not buildable."""
    prov_tmpl, palace_tmpl, parent_tmpl, translit = FRAMES[lang]
    shiki = translit(SHIKI_ROMAJI) if translit else SHIKI_LATIN
    engi = translit(ENGI_ROMAJI) if translit else ENGI_LATIN
    if not shiki or not engi:
        return None
    if item["kind"] == "parent":
        return parent_tmpl.format(engi=engi)
    if item["kind"] == "palace":
        return palace_tmpl.format(shiki=shiki)
    prov = _render_prov(translit, item["prov_core"], item["prov_disambig"])
    if not prov:
        return None
    return prov_tmpl.format(shiki=shiki, prov=prov)


def build_zh_map(item):
    """Return {zh-code: label} built from the Japanese kanji label, or {} if the
    parent (already has zh) / unparseable."""
    if item["kind"] == "parent" or not item["ja_core"]:
        return {}
    core = item["ja_core"].replace("・", "及")          # 宮中・京中 -> 宮中及京中
    simplified = japanese_to_chinese(core + "式内社列表")
    if not simplified:
        return {}
    return {"zh": simplified, **zh_variants(simplified)}


def build_ko(item):
    """Korean: phonetic province reading + 식내사 목록; hanja reading for the parent."""
    if item["kind"] == "parent":
        ko = hanja.translate("延喜式神名帳", "substitution")
        return ko if all(not ("一" <= c <= "鿿") for c in ko) else None
    if item["kind"] == "palace":
        return "궁중의 식내사 목록"
    prov = koreanize(item["prov_core"])
    if not prov:
        return None
    label = f"{prov}국의 식내사 목록"
    if item["prov_disambig"]:
        d = koreanize(item["prov_disambig"])
        if d:
            label = f"{label} ({d})"
    return label


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _ensure_utf8_stdout()
    items = fetch_items()

    # Sanity: every non-parent item parsed to a kind we can handle.
    bad = [it for it in items if it["kind"] == "province" and not it["prov_core"]]
    if bad:
        print(f"[WARN] {len(bad)} items failed province parse: {[b['qid'] for b in bad]}")
    palace = [it for it in items if it["kind"] == "palace"]
    print(f"Kinds: parent=1, province={sum(1 for it in items if it['kind']=='province')}, "
          f"palace={len(palace)}")

    covered = set(COVERED)               # every language the sub-project generates
    lines = []
    per_lang = {}

    for item in items:
        existing = item["langs"]
        # CJK
        for code, label in build_zh_map(item).items():
            if code in covered and code not in existing and label:
                lines.append((item["qid"], code, label))
                per_lang[code] = per_lang.get(code, 0) + 1
        if "ko" in covered and "ko" not in existing:
            label = build_ko(item)
            if label:
                lines.append((item["qid"], "ko", label))
                per_lang["ko"] = per_lang.get("ko", 0) + 1
        # Alphabetic / abugida / everything in FRAMES
        for lang in FRAMES:
            if lang not in covered or lang in existing:
                continue
            label = build_alpha(lang, item)
            if label:
                lines.append((item["qid"], lang, label))
                per_lang[lang] = per_lang.get(lang, 0) + 1

    # Report any covered language we produced nothing for (e.g. ar/tok already
    # present on all items, or a language missing a frame).
    produced = set(per_lang)
    framed = set(FRAMES) | set(ZH_CODES) | {"ko"}
    no_frame = sorted((covered - framed) - {"tok"})   # tok already on all 70
    if no_frame:
        print(f"[NOTE] covered languages with no frame (skipped): {no_frame}")

    outdir = os.path.join(HERE, "quickstatements")
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, "shikinaisha_lists.txt")
    with open(outpath, "w", encoding="utf-8", newline="\n") as f:
        for qid, lang, label in lines:
            esc = label.replace('"', '""')
            f.write(f'{qid}\tL{lang}\t"{esc}"\n')

    print(f"\nWrote {len(lines)} QuickStatements ({len(per_lang)} languages) to {outpath}")
    print("\nPer-language counts:")
    for lang in sorted(per_lang):
        print(f"  {lang:8s} {per_lang[lang]}")

    print("\n--- Sample (Yamashiro / Yamato / palace / parent across a few langs) ---")
    sample_qids = {items[0]["qid"]}  # parent
    for it in items:
        if it["en"] in ("List of Shikinaisha in Yamashiro Province",
                         "List of Shikinaisha in the Imperial Palace"):
            sample_qids.add(it["qid"])
    for qid, lang, label in lines:
        if qid in sample_qids and lang in ("de", "es", "ru", "el", "hi", "zh", "ko", "fr"):
            print(f"  {qid:12s} {lang:6s} | {label}")


if __name__ == "__main__":
    main()
