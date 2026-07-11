#!/usr/bin/env python3
"""
generate_saijin_deity_research.py
=================================
The *research* companion to `generate_saijin_quickstatements.py`.

`generate_saijin_quickstatements.py` is high-precision: it imports 祭神 P825 only
for deities that jawiki editorially WIKILINKED, and skips every unlinked
plain-text name. This script does the deferred deity RESEARCH the review doc
called for (`docs/jawiki_infobox_import_review_2026-07.md`: "parse deity names,
match to kami items … Multi-deity + 主祭神 distinction via qualifier"), and adds:

  1. **Unlinked-name matching.** Plain-text 祭神 names are matched to Wikidata
     kami items by EXACT ja label/alias, gated on the item being a deity
     (`wdt:P31/wdt:P279* wd:Q178885`) and being the UNIQUE such item — no fuzzy
     matching, no guessing. A mis-split token simply matches nothing and is
     dropped, so the SPARQL exactness is the safety net.
  2. **主祭神 (principal deity) qualifier.** The {{神社}} infobox carries a
     distinct `主祭神` parameter. Deities named there get their P825 statement
     qualified with P3831 (object of statement has role) = the principal-deity
     role item. Deities that appear only in the general `祭神` list get a bare
     P825 — principal-ness is never inferred from list order.

Emma 2026-07-10 chose the P3831-role model and "research unlinked names too", and
supplied the role item Q140493995 (主祭神 / "Primary deity of a Shinto shrine").

Output: saijin_deity_research.txt — atomic cited lines
    <shrine>|P825|<deity>|S143|Q177837|S4656|"<jawiki url>"                (general)
    <shrine>|P825|<deity>|P3831|<role>|S143|Q177837|S4656|"<jawiki url>"  (principal)
    (S143=Q177837 imported-from-Japanese-Wikipedia + S4656 the page URL — the
     established corpus reference bundle; see JA_WIKIPEDIA note below.)

Usage:
    python generate_saijin_deity_research.py             # full run
    python generate_saijin_deity_research.py --limit 200 # sample
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from infobox_fields import field_pattern

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
TEMPLATE = "Template:神社"
OUTPUT = os.path.join(HERE, "saijin_deity_research.txt")

# P3831 role value marking a principal (主祭神) deity. Q140493995 = 主祭神 /
# "Primary deity" ("Primary deity of a Shinto shrine", subclass of Q11591100
# saijin) — the purpose-built role item Emma supplied 2026-07-10.
PRINCIPAL_DEITY_ROLE = "Q140493995"
DEITY_CLASS_ROOT = "Q178885"  # deity — the P31/P279* gate for a safe name match
# Japanese Wikipedia (P143 = imported from). Verified 2026-07-11 as the DOMINANT
# reference marker on existing shrine-deity P825 statements — 3,339 carry
# S143=Q177837 vs only 1,441 with S4656 (the import URL). Our generator emitted
# only the URL, missing the more common imported-from marker; add it to match the
# established corpus citation bundle (S143 + S4656).
JA_WIKIPEDIA = "Q177837"

_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
_LINK_PAIR_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
_SAIJIN_RE = re.compile(field_pattern("祭神"))
_SHUSAIJIN_RE = re.compile(field_pattern("主祭神"))

# Tokens split out of a deity field that are never a deity name on their own —
# section/annotation words. A token containing any of these is dropped before the
# SPARQL gate (which would drop them anyway; this just saves query volume).
_ANNOTATION = ("配神", "相殿", "配祀", "合祀", "摂社", "末社", "主祭神", "祭神",
               "など", "ほか", "他", "不明", "など数", "境内")
_NAME_OK = re.compile(r"^[一-鿿぀-ゟ゠-ヿー々ヶ]{2,}$")


def _is_deity_link(target):
    return bool(target) and not target.startswith(
        ("File:", "ファイル:", "Category:", "カテゴリ:"))


def link_targets(field_value):
    """Wikilink targets in a field value (File:/Category: excluded)."""
    return [t.strip() for t in _LINK_RE.findall(field_value) if _is_deity_link(t.strip())]


def link_pairs(field_value):
    """[(target, display)] for each deity wikilink; display = piped text or target.

    The display form is the name AS THE SOURCE WROTE IT — captured into the P1932
    'object named as' qualifier, matching the established shrine-P825 model:
    [[天照大神|天照皇大御神]] -> ("天照大神", "天照皇大御神"); [[素戔嗚尊]] -> ("素戔嗚尊", "素戔嗚尊").
    """
    out = []
    for tgt, disp in _LINK_PAIR_RE.findall(field_value):
        tgt = tgt.strip()
        if not _is_deity_link(tgt):
            continue
        out.append((tgt, (disp or "").strip() or tgt))
    return out


def plain_names(field_value):
    """Unlinked plain-text deity-name candidates in a field value.

    Wikilinks removed, parenthetical readings stripped, split on Japanese and
    ASCII separators; only clean kanji/kana tokens survive. Loose by design —
    the SPARQL exact-label gate downstream is what guarantees correctness.
    """
    v = _LINK_RE.sub("", field_value)
    v = re.sub(r"[（(][^）)]*[）)]", "", v)          # drop readings/notes
    v = re.sub(r"<[^>]+>", "／", v)               # <br> etc. -> separator
    v = re.sub(r"\{\{[^}]*\}\}", "", v)               # drop templates
    v = re.sub(r"''+", "", v)                          # wiki bold/italic
    out = []
    for tok in re.split(r"[、,，・/／;；\n\r\t　]+", v):
        tok = tok.strip().strip("-–—*:： 　'\"")
        if not tok or any(a in tok for a in _ANNOTATION):
            continue
        if _NAME_OK.match(tok):
            out.append(tok)
    return out


_OTHER_LABEL = re.compile(r"(?:配神|配祀神?|相殿神?|合祀神?|摂社|末社|境内社|左殿|右殿)\s*[:：]?")
# Form A — a 主祭神 LABEL: the deities that FOLLOW are principal. Must not be the
# （主祭神） annotation (handled as Form B), so 主祭神 is required to be followed by
# a colon or a wikilink, and not immediately preceded by an opening paren.
_LABEL_A = re.compile(r"(?<![（(])(?:主祭神|主神)\s*(?:[:：]|(?=\[\[))")
# Form B — a （主祭神） ANNOTATION: the deity IMMEDIATELY BEFORE it is principal.
_ANNOT_B = re.compile(r"[（(]\s*(?:主祭神|主神)\s*[）)]")


def principal_refs(field_value):
    """(link_titles, plain_names) that jawiki EXPLICITLY marks as 主祭神.

    Two jawiki conventions, both handled; principal-ness is NEVER inferred from
    list order (a field with no 主祭神 marking yields empty sets):
      A. label:      主祭神：X、Y …   → X, Y (up to the next 配神/相殿… label) principal
      B. annotation: X（主祭神）        → X (the deity right before the marker) principal
    """
    links, plain = set(), set()
    # Form B first — the deity immediately preceding each （主祭神） marker.
    for m in _ANNOT_B.finditer(field_value):
        prefix = field_value[:m.start()]
        ls = link_targets(prefix)
        if ls:
            links.add(ls[-1])
        else:
            ps = plain_names(prefix)
            if ps:
                plain.add(ps[-1])
    # Form A — deities following a 主祭神 label, up to the next auxiliary label.
    for m in _LABEL_A.finditer(field_value):
        rest = field_value[m.end():]
        nxt = _OTHER_LABEL.search(rest)
        seg = rest[:nxt.start()] if nxt else rest
        links.update(link_targets(seg))
        plain.update(plain_names(seg))
    return links, plain


def qs_line(shrine_qid, deity_qid, principal, named, url):
    """One QuickStatements line: P825 + optional P3831 role + P1932 name + jawiki ref.

    Matches the established shrine-P825 model — the deity item, the source's exact
    name string (P1932 'object named as'), and, where jawiki marks it, the
    principal-deity role (P3831).
    """
    role = f"|P3831|{PRINCIPAL_DEITY_ROLE}" if principal else ""
    named_q = f'|P1932|"{named.replace(chr(34), "")}"' if named else ""
    return (f'{shrine_qid}|P825|{deity_qid}{role}{named_q}'
            f'|S143|{JA_WIKIPEDIA}|S4656|"{url}"')


# ─────────────────────────── network ───────────────────────────

def _get(params):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request(JA_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def shrine_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": TEMPLATE,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def resolve_links(titles):
    """{jawiki title -> wikidata QID} for deity link targets (redirects followed)."""
    out = {}
    titles = sorted(titles)
    for i in range(0, len(titles), 50):
        d = _get({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                  "titles": "|".join(titles[i:i + 50]), "redirects": 1})
        qy = d.get("query", {})
        remap = {}
        for r in qy.get("normalized", []) + qy.get("redirects", []):
            remap[r["from"]] = r["to"]
        final = {}
        for t in titles[i:i + 50]:
            ft, seen = t, set()
            while ft in remap and ft not in seen:
                seen.add(ft)
                ft = remap[ft]
            final[t] = ft
        by_title = {p["title"]: p.get("pageprops", {}).get("wikibase_item")
                    for p in qy.get("pages", {}).values() if "missing" not in p}
        for t, ft in final.items():
            if by_title.get(ft):
                out[t] = by_title[ft]
        time.sleep(0.3)
    return out


def _wdqs(query):
    # POST the query in the body — VALUES batches make the URL too long for GET
    # (HTTP 431). 429 bails immediately per repo policy.
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)["results"]["bindings"]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise SystemExit("429 from WDQS — bailing (repo policy: no retries).")
        raise


def match_names(names):
    """{ja deity name -> QID} for names that map to EXACTLY ONE deity item.

    Batched VALUES queries (429-safe throttle). A name resolving to >1 deity item
    is ambiguous and dropped; a name resolving to none is dropped.
    """
    names = sorted(set(names))
    hits = {}       # name -> set(qid)
    for i in range(0, len(names), 120):
        chunk = names[i:i + 120]
        values = " ".join('"%s"@ja' % n.replace('\\', '\\\\').replace('"', '\\"')
                          for n in chunk)
        query = """SELECT ?name ?item WHERE {
  VALUES ?name { %s }
  ?item rdfs:label|skos:altLabel ?name .
  ?item wdt:P31/wdt:P279* wd:%s .
}""" % (values, DEITY_CLASS_ROOT)
        for b in _wdqs(query):
            hits.setdefault(b["name"]["value"], set()).add(
                b["item"]["value"].rsplit("/", 1)[-1])
        time.sleep(1.0)
    return {n: next(iter(q)) for n, q in hits.items() if len(q) == 1}


def existing_pairs():
    """((shrine,deity) with any P825, (shrine,deity) already qualified principal)."""
    rows = _wdqs("SELECT ?s ?d WHERE { ?s wdt:P31 wd:Q845945 ; wdt:P825 ?d . }")
    have = {(b["s"]["value"].rsplit("/", 1)[-1], b["d"]["value"].rsplit("/", 1)[-1])
            for b in rows}
    rows2 = _wdqs("""SELECT ?s ?d WHERE {
      ?s wdt:P31 wd:Q845945 ; p:P825 ?st . ?st ps:P825 ?d ; pq:P3831 wd:%s . }"""
                  % PRINCIPAL_DEITY_ROLE)
    principal = {(b["s"]["value"].rsplit("/", 1)[-1], b["d"]["value"].rsplit("/", 1)[-1])
                 for b in rows2}
    return have, principal


def build_lines(shrine_deities, resolved, matched, have, have_principal):
    """Pure line assembly. shrine_deities: {(title,qid): {key: {principal, named}}}.

    key is a jawiki link title or a plain name; resolved/matched map those to QIDs.
    Deduped by (shrine,deity) QID; principal wins; the principal spelling wins as
    the P1932 name. Existing pairs are left alone (new statements only) so P1932
    is never guessed onto a pre-existing statement.
    """
    lines = []
    for (title, qid), refs in sorted(shrine_deities.items()):
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        by_qid = {}
        for key, info in refs.items():
            d = resolved.get(key) or matched.get(key)
            if not d:
                continue
            e = by_qid.setdefault(d, {"principal": False, "named": info["named"]})
            e["principal"] = e["principal"] or info["principal"]
            if info["principal"]:
                e["named"] = info["named"]
        for d, e in sorted(by_qid.items()):
            if e["principal"]:
                if (qid, d) in have_principal:
                    continue
            elif (qid, d) in have:
                continue
            lines.append(qs_line(qid, d, e["principal"], e["named"], url))
    return sorted(set(lines))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have, have_principal = existing_pairs()
    print(f"{len(have)} existing (shrine,deity) P825 pairs; "
          f"{len(have_principal)} already principal-qualified")
    titles = shrine_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki shrine articles")

    # pass 1: parse 祭神 + 主祭神, collect link targets and plain names per shrine
    shrine_deities = {}          # (title,qid) -> {deity_ref: principal_bool}
    all_links, all_plain = set(), set()
    no_field = no_qid = 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            text = text or ""
            m_all = _SAIJIN_RE.search(text)
            m_prin = _SHUSAIJIN_RE.search(text)
            gen_val = m_all.group(1) if m_all else ""
            prin_val = m_prin.group(1) if m_prin else ""
            if not gen_val.strip() and not prin_val.strip():
                no_field += 1
                continue
            if not qid:
                no_qid += 1
                continue
            inline_links, inline_plain = principal_refs(gen_val)
            prin_links = set(link_targets(prin_val)) | inline_links
            prin_plain = set(plain_names(prin_val)) | inline_plain
            refs = {}
            for tgt, disp in link_pairs(gen_val) + link_pairs(prin_val):
                is_p = tgt in prin_links
                cur = refs.get(tgt)
                if cur is None:
                    refs[tgt] = {"principal": is_p, "named": disp}
                else:
                    cur["principal"] = cur["principal"] or is_p
                    if is_p:
                        cur["named"] = disp
                all_links.add(tgt)
            for nm in plain_names(gen_val) + list(prin_plain):
                is_p = nm in prin_plain
                cur = refs.get(nm)
                if cur is None:
                    refs[nm] = {"principal": is_p, "named": nm}
                else:
                    cur["principal"] = cur["principal"] or is_p
                all_plain.add(nm)
            if refs:
                shrine_deities[(title, qid)] = refs
        time.sleep(0.3)
    print(f"{len(shrine_deities)} shrines with deity refs "
          f"(no-field={no_field}, no-QID={no_qid}); "
          f"{len(all_links)} link targets, {len(all_plain)} plain names")

    # pass 2: resolve links (pageprops) and match plain names (SPARQL exact label)
    resolved = resolve_links(all_links)
    print(f"{len(resolved)}/{len(all_links)} link targets resolve to items")
    matched = match_names(all_plain)
    print(f"{len(matched)}/{len(all_plain)} plain names match a unique deity item")

    lines = build_lines(shrine_deities, resolved, matched, have, have_principal)
    principal_n = sum(1 for ln in lines if "|P3831|" in ln)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P825 lines ({principal_n} principal-qualified) -> {OUTPUT}")


if __name__ == "__main__":
    main()
