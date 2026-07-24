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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "genbu_ids.txt")
SPARQL = "https://query.wikidata.org/sparql"
GENBU = "https://www.genbu.net"
SHRINE_CLASS = "Q845945"                 # Shinto shrine
REGIONS = ["tohoku", "kanto", "kousinetu", "hokuriku", "tokai", "kansai",
           "cyugoku", "sikoku", "kyusyu", "hokkaido", "okinawa"]
UA = {"User-Agent": "ShintoWikiGenbu/1.0 (immanuelleleonhart@gmail.com)"}
SPARQL_HDR = dict(UA, **{"Accept": "application/sparql-results+json"})

GENBU_URL_RE = re.compile(r"https?://(?:www\.)?genbu\.net/(.+?)\.htm", re.I)
INDEX_LINK_RE = re.compile(r'href="([^"]*data/[^"]+_title)\.htm"[^>]*>([^<]+)<')
PAREN_RE = re.compile(r"[(（].*?[)）]\s*$")


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _sparql(query):
    for attempt in range(4):
        time.sleep(0.5)
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
            print(f"  [WDQS retry {attempt+1}] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
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
    """{ja label -> [shrine-item QIDs]} for the names (Shinto-shrine items only)."""
    out, uniq = {}, sorted(set(names))
    for i in range(0, len(uniq), 120):
        chunk = uniq[i:i + 120]
        values = " ".join('"%s"@ja' % n.replace('\\', '\\\\').replace('"', '\\"') for n in chunk)
        rows = _sparql(
            "SELECT ?i ?lab WHERE { VALUES ?lab { %s } "
            "?i rdfs:label ?lab ; wdt:P31/wdt:P279* wd:%s }" % (values, SHRINE_CLASS))
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


def main():
    _utf8()
    have = existing_p13930()
    qid_to_id = {}                       # QID -> genbu id (citations take precedence)

    # A — broad genbu index
    names = genbu_index()
    print(f"genbu index: {len(names)} distinct shrine names", flush=True)
    lab_qids = shrine_label_qids(list(names))
    a_count = 0
    for name, paths in names.items():
        if len(paths) != 1:
            continue                     # ambiguous on the genbu side
        qids = lab_qids.get(name, [])
        if len(qids) != 1:
            continue                     # 0 or >1 shrine items with this label
        qid_to_id.setdefault(qids[0], next(iter(paths)))
        a_count += 1
    print(f"broad matched: {a_count}", flush=True)

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
