"""Throwaway (2026-09-27): how much of each static drip file is already on Wikidata.

Read-only. WDQS only, VALUES-batched, 2.5s apart, bail on 429. Deleted after use.
"""
import io, json, os, re, sys, time
import requests

MQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modern-quickstatements")
S = requests.Session()
S.headers["User-Agent"] = "shintowiki-scripts/1.0 (https://github.com/EmmaLeonhart/shintowiki-scripts)"
EP = "https://query.wikidata.org/sparql"
BATCH = 300

FILES = ["reisai.txt", "bunrei.txt", "beppyo_p612.txt", "bunrei_shinwa_otaku.txt", "bunrei_ikkojin.txt",
         "bunrei_animism.txt", "bunrei_onkamui.txt", "bunrei_nicovideo.txt", "bunrei_toranomaki.txt",
         "shintai_p825.txt", "jinjacho_p973.txt", "hisousha_p119_p547.txt", "en_labels_sonnet.txt",
         "label_typo_fixes.txt", "name_in_kana.txt", "ronsha_ranking_qualifiers.txt",
         "p6262_fandom_links.txt", "p11250_miraheze_links.txt"]


def split(line):
    line = line.strip()
    if "\t" in line and "|" not in line:
        line = line.replace("\t", "|")
    return [p for p in re.split(r'\|(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]


def val(v):
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return ("str", v[1:-1])
    if re.match(r"^[a-z-]+:\"", v):
        return ("str", v.split(":", 1)[1].strip('"'))
    if re.match(r"^Q\d+$", v):
        return ("item", v)
    if v.startswith("+"):
        return ("time", v.split("/")[0].lstrip("+"))
    return ("raw", v)


def sparql(q):
    for attempt in range(3):
        r = S.post(EP, data={"query": q, "format": "json"}, timeout=120)
        if r.status_code == 429:
            print("429 from WDQS - bailing", flush=True)
            sys.exit(2)
        if r.status_code in (500, 502, 503, 504):
            time.sleep(15 * 3 ** attempt)
            continue
        r.raise_for_status()
        time.sleep(2.5)
        return r.json()["results"]["bindings"]
    raise RuntimeError("WDQS kept failing")


def live_values(items, prop):
    """{item: set(values)} for truthy+non-truthy statements of prop (item ids / strings / dates)."""
    out = {}
    items = sorted(items)
    for i in range(0, len(items), BATCH):
        vals = " ".join("wd:" + q for q in items[i:i + BATCH])
        rows = sparql(f"SELECT ?s ?o WHERE {{ VALUES ?s {{ {vals} }} ?s p:{prop}/ps:{prop} ?o }}")
        for b in rows:
            s = b["s"]["value"].rsplit("/", 1)[-1]
            o = b["o"]["value"]
            if o.startswith("http://www.wikidata.org/entity/"):
                o = o.rsplit("/", 1)[-1]
            out.setdefault(s, set()).add(o)
    return out


def live_labels(items, lang):
    out = {}
    items = sorted(items)
    for i in range(0, len(items), BATCH):
        vals = " ".join("wd:" + q for q in items[i:i + BATCH])
        rows = sparql(f'SELECT ?s ?l WHERE {{ VALUES ?s {{ {vals} }} ?s rdfs:label ?l FILTER(LANG(?l)="{lang}") }}')
        for b in rows:
            out[b["s"]["value"].rsplit("/", 1)[-1]] = b["l"]["value"]
    return out


results = {}
for fn in FILES:
    path = os.path.join(MQ, fn)
    if not os.path.exists(path):
        continue
    lines = [l for l in io.open(path, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    parsed = []
    for l in lines:
        p = split(l.split("    #")[0])
        if len(p) >= 3 and re.match(r"^Q\d+$", p[0]):
            parsed.append((l.rstrip("\n"), p[0], p[1], val(p[2])))
    by_prop = {}
    for _, s, prop, v in parsed:
        by_prop.setdefault(prop, set()).add(s)
    live = {}
    for prop, items in by_prop.items():
        if re.match(r"^L[a-z-]+$", prop):
            live[prop] = live_labels(items, prop[1:])
        elif re.match(r"^P\d+$", prop):
            live[prop] = live_values(items, prop)
        print(f"  {fn}: {prop} checked ({len(items)} items)", flush=True)
    landed, pending, unknown = [], [], 0
    for l, s, prop, (kind, v) in parsed:
        if prop not in live:
            unknown += 1
            continue
        got = live[prop].get(s)
        if prop.startswith("L"):
            ok = got == v
        else:
            got = got or set()
            if kind == "time":
                ok = any(g.startswith(v.split("T")[0][:4]) or g.lstrip("+").startswith(v[:10]) for g in got)
            else:
                ok = v in got
        (landed if ok else pending).append(l)
    results[fn] = {"lines": len(lines), "checked": len(parsed), "landed": len(landed),
                   "pending": len(pending), "unchecked": unknown + (len(lines) - len(parsed))}
    json.dump({"results": results}, io.open("_static_landed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    io.open(f"_landed_{fn}", "w", encoding="utf-8").write("\n".join(landed))
    print(fn, results[fn], flush=True)
print("DONE", flush=True)
