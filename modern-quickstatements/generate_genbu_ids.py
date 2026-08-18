"""
Entity-resolution → P13930 (Genbu.net ID). Two sources, unioned:

  A. BROAD — crawl genbu.net's own regional indexes (place/index<region>.htm), which
     list every shrine as <a href="../data/<prov>/<name>_title.htm">名称(所在)</a>.
     The P13930 id is the path after genbu.net/ minus ".htm" (formatter
     https://www.genbu.net/$1.htm). Match the shrine name (parenthetical location
     stripped) to a Wikidata item by EXACT ja label, restricted to Shinto-shrine
     items (P31/P279* Q845945). Emit only when a name maps to exactly ONE genbu path
     AND exactly ONE shrine item — high precision across the whole database.

  B. CITATIONS — genbu.net URLs already cited in our synced *.wiki articles, mapped
     to the page's QID via P11250. Human-linked, so this also covers shrines whose
     name is ambiguous (skipped by A). (Live-wiki exturlusage would add the rest of
     the cited pages, but shinto.miraheze.org is Cloudflare-403'd.)

Union, dedup by QID (citations win on conflict). Add-only; skips items that already
have P13930. Output: modern-quickstatements/genbu_ids.txt
Read-only (genbu.net + local files + WDQS); writes only the .txt. 429 => bail.
"""

import os
import re
import sys
import time
import urllib.parse
import requests
from shinto_miraheze.ua_contact import contact

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "genbu_ids.txt")
# query-main, not query.wikidata.org. The 2026-08-03 jinjacho rematch — which
# imports this module's _sparql — hit repeated 503/504 from the old endpoint on
# its 17,549-candidate P131 batch and only finished on retries. query-main is the
# main-graph split endpoint the newer scripts here already use. 24 other scripts
# in this repo are still on the old one; see queue.md A3.
SPARQL = "https://query-main.wikidata.org/sparql"
GENBU = "https://www.genbu.net"
SHRINE_CLASS = "Q845945"                 # Shinto shrine
REGIONS = ["tohoku", "kanto", "kousinetu", "hokuriku", "tokai", "kansai",
           "cyugoku", "sikoku", "kyusyu", "hokkaido", "okinawa"]
UA = {"User-Agent": "ShintoWikiGenbu/1.0 ({contact('wikidata')})"}
SPARQL_HDR = dict(UA, **{"Accept": "application/sparql-results+json"})

GENBU_URL_RE = re.compile(r"https?://(?:www\.)?genbu\.net/(.+?)\.htm", re.I)
INDEX_LINK_RE = re.compile(r'href="([^"]*data/[^"]+_title)\.htm"[^>]*>([^<]+)<')
PAREN_RE = re.compile(r"[(（].*?[)）]\s*$")

# genbu.net writes shrine names in kyūjitai (old kanji); our Wikidata labels are
# shinjitai (modern). Normalise the common old→new forms so the names match.
KYUJI = dict(zip(
    "櫻國靈稻眞邊邉齋齊濱澤廣圓榮惠壽禮樂氣學應藝龍縣號舊會觀關峽狹溪劍嚴兒寫從莊增藏傳德拜賣寶豐萬滿與樣來亂覽兩綠圖團斷鐵轉點燈當佛變步藥錄淺淨靜瀨髙鹽惡醫假價擧據驅徑溫穩勸歡樞禰祿",
    "桜国霊稲真辺辺斎斉浜沢広円栄恵寿礼楽気学応芸竜県号旧会観関峡狭渓剣厳児写従荘増蔵伝徳拝売宝豊万満与様来乱覧両緑図団断鉄転点灯当仏変歩薬録浅浄静瀬高塩悪医仮価挙拠駆径温穏勧歓枢禰禄"))


def to_shinjitai(name):
    return name.translate({ord(k): v for k, v in KYUJI.items()})


_MACRON = str.maketrans("āīūēōĀĪŪĒŌ", "aiueoAIUEO")


def strip_macron(s):
    return s.translate(_MACRON)


# genbu old-province path code -> modern prefecture name(s). Used to disambiguate
# same-named shrines: the genbu path province picks which candidate (identified by
# its P131* prefecture) is the correct one. Names are matched macron-insensitively
# against the prefecture item's en label (startswith), so "Hyogo" hits "Hyōgo Prefecture".
GENBU_PROV_PREF = {
    "mutu": ["Aomori", "Iwate", "Miyagi", "Fukushima"], "tugaru": ["Aomori"],
    "sinano": ["Nagano"], "yamato": ["Nara"], "tajima": ["Hyogo"], "oumi": ["Shiga"],
    "etizen": ["Fukui"], "wakasa": ["Fukui"], "izu": ["Shizuoka"], "suruga": ["Shizuoka"],
    "toutoumi": ["Shizuoka"], "ecyu": ["Toyama"], "etigo": ["Niigata"], "sado": ["Niigata"],
    "izumo": ["Shimane"], "iwami": ["Shimane"], "oki": ["Shimane"], "kai": ["Yamanashi"],
    "awa2": ["Tokushima"], "awa": ["Chiba"], "kazusa": ["Chiba"], "simofusa": ["Chiba", "Ibaraki"],
    "yamasiro": ["Kyoto"], "tango": ["Kyoto"], "tanba": ["Kyoto", "Hyogo"],
    "ise": ["Mie"], "iga": ["Mie"], "sima": ["Mie"], "kii": ["Wakayama", "Mie"],
    "noto": ["Ishikawa"], "kaga": ["Ishikawa"], "musasi": ["Tokyo", "Saitama", "Kanagawa"],
    "sagami": ["Kanagawa"], "kouzuke": ["Gunma"], "simotuke": ["Tochigi"], "hitati": ["Ibaraki"],
    "tusima": ["Nagasaki"], "iki": ["Nagasaki"], "hizen": ["Saga", "Nagasaki"],
    "sanuki": ["Kagawa"], "mino": ["Gifu"], "hida": ["Gifu"], "mikawa": ["Aichi"], "owari": ["Aichi"],
    "bizen": ["Okayama"], "bicchuu": ["Okayama"], "mimasaka": ["Okayama"],
    "dewa": ["Yamagata", "Akita"], "iyo": ["Ehime"], "inaba": ["Tottori"], "houki": ["Tottori"],
    "tosa": ["Kochi"], "suou": ["Yamaguchi"], "nagato": ["Yamaguchi"],
    "tikuzen": ["Fukuoka"], "tikugo": ["Fukuoka"], "buzen": ["Fukuoka", "Oita"], "bungo": ["Oita"],
    "bingo": ["Hiroshima"], "aki": ["Hiroshima"], "awaji": ["Hyogo"], "harima": ["Hyogo"],
    "settu": ["Osaka", "Hyogo"], "kawati": ["Osaka"], "izumi": ["Osaka"],
    "hyuga": ["Miyazaki"], "higo": ["Kumamoto"], "oosumi": ["Kagoshima"], "satuma": ["Kagoshima"],
    "ezo": ["Hokkaido"], "ryukyu": ["Okinawa"],
}


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# WDQS throttle. Was 0.5s, which is far too fast for what this module actually
# issues: match_jinjacho_shrines.py imports _sparql and, on a 9,000-row crawl,
# fires ~365 queries per run — 65 label batches plus 300 P131 TRANSITIVE-CLOSURE
# batches, each over 60 items. At 0.5s that is ~2 expensive queries/second held
# for minutes, and three runs on 2026-08-03 drew repeated 503/504 that were
# initially blamed on the endpoint rather than on us. 2.5s matches the THROTTLE
# this repo already applies to Miraheze; a full matcher run costs ~15 minutes of
# sleep, which is the correct price for a job that runs occasionally.
WDQS_THROTTLE = 2.5


def _sparql(query):
    for attempt in range(4):
        time.sleep(WDQS_THROTTLE)
        try:
            r = requests.post(SPARQL, data={"query": query, "format": "json"},
                              headers=SPARQL_HDR, timeout=180)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            # Exponential, not linear: a 503/504 means the endpoint is already
            # struggling, and 5/10/15s retries add load at exactly the wrong
            # moment. 15/45/135s backs off properly.
            print(f"  [WDQS retry {attempt+1}] {e}", flush=True)
            time.sleep(15 * (3 ** attempt))
    raise RuntimeError("WDQS failed")


def clean_name(anchor):
    return PAREN_RE.sub("", anchor.strip()).strip()


def genbu_index():
    """{clean ja name -> set of genbu path ids} from all regional indexes."""
    names = {}
    for region in REGIONS:
        url = f"{GENBU}/place/index{region}.htm"
        try:
            r = requests.get(url, headers=UA, timeout=60)
            if r.status_code != 200:
                continue
            r.encoding = r.apparent_encoding
        except Exception as e:
            print(f"  index {region} failed: {e}", flush=True)
            continue
        n = 0
        for path, anchor in INDEX_LINK_RE.findall(r.text):
            gid = path.split("data/", 1)[1]
            gid = "data/" + gid.lstrip("/")
            name = clean_name(anchor)
            if name:
                names.setdefault(name, set()).add(gid)
                n += 1
        print(f"  {region}: {n} shrine links", flush=True)
        time.sleep(0.4)
    return names


def shrine_label_qids(names):
    """{ja name -> [shrine-item QIDs]} where the name matches a Shinto-shrine item's
    ja label OR ja alias (skos:altLabel — many items carry the kyūjitai form there)."""
    out, uniq = {}, sorted(set(names))
    for i in range(0, len(uniq), 50):
        chunk = uniq[i:i + 50]
        values = " ".join('"%s"@ja' % n.replace('\\', '\\\\').replace('"', '\\"') for n in chunk)
        try:
            rows = _sparql(
                "SELECT ?i ?lab WHERE { VALUES ?lab { %s } "
                "?i (rdfs:label|skos:altLabel) ?lab ; wdt:P31/wdt:P279* wd:%s }"
                % (values, SHRINE_CLASS))
        except Exception as e:
            print(f"  [chunk {i//50} skipped] {e}", flush=True)
            continue
        for b in rows:
            out.setdefault(b["lab"]["value"], []).append(b["i"]["value"].rsplit("/", 1)[1])
    return out


def cited_pages():
    """{mainspace page title -> set of genbu ids} from synced *.wiki files."""
    pages = {}
    for dirpath, _d, files in os.walk(REPO_ROOT):
        if os.sep + ".git" in dirpath:
            continue
        for fn in files:
            if not fn.endswith(".wiki"):
                continue
            title = urllib.parse.unquote(fn[:-len(".wiki")])
            if ":" in title:
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in GENBU_URL_RE.finditer(text):
                pages.setdefault(title, set()).add(m.group(1).strip("/"))
    return pages


def p11250_map():
    rows = _sparql('SELECT ?item ?t WHERE { ?item wdt:P11250 ?t }')
    out = {}
    for b in rows:
        v = b["t"]["value"]
        if v.startswith("shinto:"):
            out[v[len("shinto:"):]] = b["item"]["value"].rsplit("/", 1)[1]
    return out


def existing_p13930():
    rows = _sparql('SELECT ?item WHERE { ?item wdt:P13930 [] }')
    return {b["item"]["value"].rsplit("/", 1)[1] for b in rows}


def prefecture_name_qids():
    """{macron-stripped lowercased prefecture en label -> QID} for Japan prefectures."""
    rows = _sparql('SELECT ?p ?l WHERE { ?p wdt:P31 wd:Q50337 ; '
                   'rdfs:label ?l FILTER(LANG(?l)="en") }')
    return {strip_macron(b["l"]["value"]).lower(): b["p"]["value"].rsplit("/", 1)[1]
            for b in rows}


def names_to_pref_qids(names, pref_map):
    out = set()
    for name in names:
        key = strip_macron(name).lower()
        for lab, qid in pref_map.items():
            if lab.startswith(key):
                out.add(qid)
    return out


def candidate_prefectures(qids):
    """{shrine QID -> set of prefecture QIDs via P131*}."""
    out, uniq = {}, sorted(qids)
    for i in range(0, len(uniq), 80):
        vals = " ".join("wd:%s" % q for q in uniq[i:i + 80])
        try:
            rows = _sparql("SELECT ?item ?p WHERE { VALUES ?item { %s } "
                           "?item wdt:P131* ?p . ?p wdt:P31 wd:Q50337 }" % vals)
        except Exception as e:
            print(f"  [pref chunk {i//80} skipped] {e}", flush=True)
            continue
        for b in rows:
            out.setdefault(b["item"]["value"].rsplit("/", 1)[1], set()).add(
                b["p"]["value"].rsplit("/", 1)[1])
    return out


def main():
    _utf8()
    have = existing_p13930()
    qid_to_id = {}                       # QID -> genbu id (citations take precedence)

    # A — broad genbu index. Match each name in BOTH its raw (kyūjitai) form and its
    # shinjitai-normalised form, against shrine labels+aliases.
    names = genbu_index()
    print(f"genbu index: {len(names)} distinct shrine names", flush=True)
    all_forms = set()
    for name in names:
        all_forms.add(name)
        all_forms.add(to_shinjitai(name))
    lab_qids = shrine_label_qids(all_forms)
    a_count = 0
    ambiguous = {}                       # name -> (qids set, path, genbu province code)
    for name, paths in names.items():
        if len(paths) != 1:
            continue                     # ambiguous on the genbu side
        path = next(iter(paths))
        qids = set()
        for form in (name, to_shinjitai(name)):
            qids.update(lab_qids.get(form, []))
        if len(qids) == 1:
            qid_to_id.setdefault(next(iter(qids)), path)
            a_count += 1
        elif len(qids) > 1:
            m = re.match(r"data/([^/]+)/", path)
            if m:
                ambiguous[name] = (qids, path, m.group(1))
    print(f"broad matched: {a_count} | name-ambiguous: {len(ambiguous)}", flush=True)

    # province disambiguation — the genbu path province picks the right candidate
    # among same-named shrines (by each candidate's P131* prefecture).
    pref_map = prefecture_name_qids()
    all_cand = set()
    for qids, _, _ in ambiguous.values():
        all_cand |= qids
    cand_pref = candidate_prefectures(all_cand)
    d_count = 0
    for name, (qids, path, code) in ambiguous.items():
        acceptable = names_to_pref_qids(GENBU_PROV_PREF.get(code, []), pref_map)
        if not acceptable:
            continue
        survivors = [q for q in qids if cand_pref.get(q, set()) & acceptable]
        if len(survivors) == 1:
            qid_to_id.setdefault(survivors[0], path)
            d_count += 1
    print(f"province-disambiguated: {d_count}", flush=True)

    # B — citations (win on conflict)
    pages = cited_pages()
    title_qid = p11250_map()
    b_count = 0
    for title, gids in pages.items():
        if len(gids) != 1:
            continue
        qid = title_qid.get(title)
        if not qid:
            continue
        qid_to_id[qid] = next(iter(gids))   # overwrite: citation wins
        b_count += 1
    print(f"citation matched: {b_count}", flush=True)

    lines = [f'{q}|P13930|"{gid}"' for q, gid in sorted(qid_to_id.items())
             if q not in have]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"emit {len(lines)} P13930 (of {len(qid_to_id)} resolved, "
          f"{len(qid_to_id) - len(lines)} already had it) -> {OUT}")
    for ln in lines[:8]:
        print("  ", ln)


if __name__ == "__main__":
    main()
