#!/usr/bin/env python3
"""Extract family relations for the HUMAN recreation candidates from the host
article they were referenced in, cited to that article.

Emma 2026-07-06: "for the humans, their family relations are something I want to
keep here … we'd essentially be citing the article that they were referenced in
for their genealogical relationships." The deleted individuals came from family
trees on host pages (e.g. `[[Abe no Yasuchika]]`), whose infobox + Family section
state the relations EXPLICITLY and definitionally:

    | Parentage = Father: …, Mother: …
    | Siblings  = {{ill|Abe no Masafumi|ja|安倍政文|qid=DELETED_QID}}, …
    | Children  = {{ill|Abe no Kiyohiro|ja|安倍季弘|qid=DELETED_QID}}, …
    * Father: …  * Mother: …  * Sons: …  * Daughters: …
    gender = {{ill|Male (gender)|…}}

So a deleted person's relationship to the host SUBJECT is stated, not guessed. We
map it to Wikidata properties (host subject = the relation target; its QID read from
the host article's OWN declared {{wikidata link}} — authoritative, never fuzzy-searched:
Emma 2026-07-06 flagged that host articles already have wikidata, so a search is a red
flag). If a relative is itself a deleted item, its QID is null (link after recreation):

  candidate in host's Children/Sons/Daughters → candidate P22/P25 = host (by host sex)
  candidate in host's Siblings                → candidate P3373 (sibling) = host
  candidate in host's Father                  → candidate P40 (child) = host; P21 male
  candidate in host's Mother                  → candidate P40 (child) = host; P21 female

Every relation records its `source_page` (the citation). Relatives that are other
DELETED targets get `target_qid: null` (their item doesn't exist yet — linked after
co-recreation). Read-only fandom + Wikidata (throttled, 429-bail); writes local JSON
+ `_relations_summary.md`. Run after enrich_p31.py. Recreation stays human-gated.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import io
import os
import re
import sys
import glob
import json
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(HERE, "items")
FANDOM_API = "https://shinto.fandom.com/api.php"
UA = USER_AGENT
HUMAN_QID = "Q5"
THROTTLE = 0.25

# Wikidata property + label for each relation of the CANDIDATE to the host subject.
REL_PROP = {
    "father_of_host": ("P40", "child", None),        # candidate is host's father → child=host
    "mother_of_host": ("P40", "child", None),
    "child_of_host_male": ("P22", "father", "Q6581097"),   # host is candidate's father
    "child_of_host_female": ("P25", "mother", "Q6581072"),
    "sibling_of_host": ("P3373", "sibling", None),
}

_ILL = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)
_WLINK = re.compile(r"\[\[([^\[\]|]+)(?:\|[^\[\]]*)?\]\]")
_LANG = re.compile(r"^[a-z][a-z-]{1,11}$")


def _targets_in(field):
    """Return [(en_label, ja_label)] for every {{ill}} / [[link]] in a field string.
    Pure. For an ill, en = positional[0], ja = the value after a `ja` positional or
    `ja=` param (empty if none)."""
    out = []
    for inner in _ILL.findall(field):
        parts = [p.strip() for p in inner.split("|")]
        positional, ja = [], ""
        for i, p in enumerate(parts):
            if "=" in p:
                k, _, v = p.partition("=")
                if k.strip().lower() == "ja" and v.strip():
                    ja = v.strip()
                continue
            if i == 0 or p:
                positional.append(p)
        en = positional[0] if positional else ""
        if not ja:
            for j in range(1, len(positional) - 1):
                if positional[j] == "ja" and positional[j + 1]:
                    ja = positional[j + 1]
                    break
        if en or ja:
            out.append((en, ja))
    for en in _WLINK.findall(field):
        out.append((en.strip(), ""))
    return out


def _field(wikitext, *labels):
    """Value of an infobox `| Label = …` line OR a `* Label: …` bullet, joined across
    both forms. Pure. Stops the infobox field at the next `|` newline."""
    chunks = []
    for lab in labels:
        for m in re.finditer(r"\|\s*" + re.escape(lab) + r"\s*=\s*(.*)", wikitext):
            chunks.append(m.group(1))
        for m in re.finditer(r"^\*\s*" + re.escape(lab) + r"\s*[:：]\s*(.*)$",
                             wikitext, re.MULTILINE):
            chunks.append(m.group(1))
    return " ,, ".join(chunks)


def host_sex(wikitext):
    """'male' / 'female' / None from the host infobox gender field. Pure."""
    m = re.search(r"gender\s*=\s*\{\{\s*ill\s*\|\s*(Male|Female)", wikitext, re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"\|\s*(?:sex|gender)\s*=\s*(male|female|男性|女性|男|女)", wikitext, re.I)
    if m:
        v = m.group(1).lower()
        return "male" if v in ("male", "男性", "男") else "female"
    return None


def host_ja(wikitext):
    """Host subject's Japanese name from bold '''En''' (Ja) or {{nihongo}}. Pure."""
    m = re.search(r"'''[^']+'''\s*[（(]\s*([　-鿿]+)\s*[）)]", wikitext)
    if m:
        return m.group(1)
    m = re.search(r"\{\{\s*nihongo\s*\|[^|{}]*\|\s*([　-鿿]+)", wikitext, re.I)
    return m.group(1) if m else ""


def _ill_node(inner):
    """Parse one {{ill|…}} inner → (en, ja, qid). qid = real Q from `qid=` (not
    DELETED_QID), else ''. Pure."""
    parts = [p.strip() for p in inner.split("|")]
    positional, ja, qid = [], "", ""
    for i, p in enumerate(parts):
        if "=" in p:
            k, _, v = p.partition("=")
            k, v = k.strip().lower(), v.strip()
            if k == "ja" and v:
                ja = v
            elif k == "qid" and re.match(r"Q\d+$", v):
                qid = v
            continue
        if i == 0 or p:
            positional.append(p)
    en = positional[0] if positional else ""
    if not ja:
        for j in range(1, len(positional) - 1):
            if positional[j] == "ja" and positional[j + 1]:
                ja = positional[j + 1]
                break
    return en, ja, qid


def familytree_chain(wikitext):
    """Ordered node list [(en, ja, qid)] from {{familytree}} rows. For a linear
    vertical 系図 (one node per row, `!` connectors — the Awaga priest lineage
    form) consecutive entries are parent→child. Pure."""
    nodes = []
    for line in wikitext.splitlines():
        if "{{familytree" not in line.lower():
            continue
        for m in re.finditer(r"=\s*'*\{\{\s*ill\s*\|([^{}]*)\}\}", line):
            en, ja, qid = _ill_node(m.group(1))
            if en or ja:
                nodes.append((en, ja, qid))
    return nodes


def familytree_relation(cand_en, cand_ja, wikitext):
    """(parent_node, child_node) for the candidate in a linear familytree lineage,
    each (en, ja, qid) or None. Vertical descent line ⇒ node above = parent (P22),
    node below = child (P40). Pure."""
    chain = familytree_chain(wikitext)
    idx = None
    for i, (en, ja, _q) in enumerate(chain):
        if (cand_ja and ja and cand_ja == ja) or (cand_en and en and cand_en == en):
            idx = i
            break
    if idx is None:
        return None, None
    parent = chain[idx - 1] if idx > 0 else None
    child = chain[idx + 1] if idx + 1 < len(chain) else None
    return parent, child


def host_wikidata_qid(wikitext):
    """The host article's OWN declared Wikidata item — from its {{wikidata link|Q…}}
    template (or a `|wikidata=Q…` infobox param). Authoritative: the article states
    its item, so we never fuzzy-search for it (Emma 2026-07-06: host articles already
    have wikidata; a search is a red flag). None if the page declares none. Pure."""
    m = (re.search(r"\{\{\s*wikidata[ _]link\s*\|\s*(Q\d+)", wikitext, re.I)
         or re.search(r"\|\s*wikidata\s*=\s*(Q\d+)", wikitext, re.I))
    return m.group(1) if m else None


def _indirect(field, start):
    """True if the reference beginning at `start` is preceded by 'Daughter of' /
    'Son of' — i.e. names a grand-parent, not a direct parent. Pure."""
    pre = re.sub(r"[\s'’]+", " ", field[max(0, start - 24):start]).strip().lower()
    return pre.endswith("daughter of") or pre.endswith("son of") or pre.endswith(" of")


def _direct_in(field, cand_en, cand_ja):
    """True if the candidate appears in `field` as a DIRECT reference — NOT as
    'Daughter of {{ill|X}}' / 'Son of X' (which makes X a grand-parent, not a
    parent — e.g. Adachi Yoshikage's 'Mother: Daughter of Mutō Yorisuke'). Pure."""
    for m in _ILL.finditer(field):
        en, ja, _q = _ill_node(m.group(1))
        if ((cand_ja and ja and ja == cand_ja) or (cand_en and en and en == cand_en)) \
                and not _indirect(field, m.start()):
            return True
    for m in _WLINK.finditer(field):
        if cand_en and m.group(1).strip() == cand_en and not _indirect(field, m.start()):
            return True
    return False


def classify_candidate(cand_en, cand_ja, wikitext):
    """Which relation the candidate has to the host subject, by the field it sits in.
    Returns one of REL_PROP's keys (+ host sex applied for child) or None. Pure."""
    sex = host_sex(wikitext)

    def _has(*labels):
        return _direct_in(_field(wikitext, *labels), cand_en, cand_ja)

    if _has("Children", "Sons", "Daughters"):
        return "child_of_host_female" if sex == "female" else "child_of_host_male"
    if _has("Siblings", "Brothers", "Sisters"):
        return "sibling_of_host"
    if _has("Father"):
        return "father_of_host"
    if _has("Mother"):
        return "mother_of_host"
    # Parentage / parents line packs Father:/Mother: together (Adachi uses `parents`).
    par = _field(wikitext, "Parentage", "parents")
    if par:
        fa = par.split("Mother")[0]
        mo = par[len(fa):]
        if _direct_in(fa, cand_en, cand_ja):
            return "father_of_host"
        if _direct_in(mo, cand_en, cand_ja):
            return "mother_of_host"
    return None


# ── network ────────────────────────────────────────────────────────────────
def _get(api, params):
    for attempt in range(4):
        try:
            r = requests.get(api, params=params, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429:
                print("  [429] bailing per policy")
                sys.exit(2)
            if r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def fetch_wikitext(title):
    r = _get(FANDOM_API, {"action": "query", "titles": title, "prop": "revisions",
                          "rvprop": "content", "rvslots": "main",
                          "formatversion": "2", "format": "json"})
    time.sleep(THROTTLE)
    if not r:
        return ""
    pgs = r.get("query", {}).get("pages", [])
    if not pgs or pgs[0].get("missing"):
        return ""
    return pgs[0]["revisions"][0]["slots"]["main"]["content"]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    files = sorted(glob.glob(os.path.join(ITEMS_DIR, "Q*.json")))
    wt_cache, qid_cache = {}, {}
    rows = []
    with_rel = 0
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if not rec.get("recreation_candidate"):
            continue
        enr = rec.setdefault("enrichment", {})
        if enr.get("p31") != HUMAN_QID:
            continue
        fandom = rec.get("fandom") or {}
        cand_en = rec.get("recovered_label") or fandom.get("label") or ""
        cand_ja = (fandom.get("langlinks") or {}).get("ja") or ""
        relations = []
        for host in fandom.get("host_pages") or []:
            if host not in wt_cache:
                wt_cache[host] = fetch_wikitext(host)
            wt = wt_cache[host]
            if not wt:
                continue
            # (a) Labeled infobox/Family fields — the host subject is the relative.
            key = classify_candidate(cand_en, cand_ja, wt)
            if key:
                prop, rel_label, sex_qid = REL_PROP[key]
                h_ja = host_ja(wt)
                if host not in qid_cache:
                    qid_cache[host] = host_wikidata_qid(wt)  # article's declared item
                relations.append({
                    "property": prop, "relation": rel_label,
                    "target_label_en": host, "target_label_ja": h_ja,
                    "target_qid": qid_cache[host], "source_page": host,
                    "source": "infobox",
                })
                if sex_qid and not any(r.get("property") == "P21" for r in relations):
                    relations.append({"property": "P21", "relation": "sex or gender",
                                      "target_label_en":
                                      "male" if sex_qid == "Q6581097" else "female",
                                      "target_qid": sex_qid, "source_page": host,
                                      "source": "infobox"})

            # (b) {{familytree}} vertical lineage — node above/below = father/child.
            parent, child = familytree_relation(cand_en, cand_ja, wt)
            if parent:
                relations.append({
                    "property": "P22", "relation": "father",
                    "target_label_en": parent[0], "target_label_ja": parent[1],
                    "target_qid": parent[2] or None, "source_page": host,
                    "source": "familytree-lineage",
                })
            if child:
                relations.append({
                    "property": "P40", "relation": "child",
                    "target_label_en": child[0], "target_label_ja": child[1],
                    "target_qid": child[2] or None, "source_page": host,
                    "source": "familytree-lineage",
                })
        enr["relations"] = relations
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
        if relations:
            with_rel += 1
        rows.append((rec["qid"], cand_en, cand_ja, relations))
        rc = ", ".join(f"{r['relation']}→{r.get('target_label_en')}"
                       f"({r.get('target_qid') or '—'})" for r in relations) or "none"
        print(f"  {rec['qid']} {cand_en}: {rc}")

    lines = ["# Human recreation candidates — family relations (from host articles)\n",
             f"- Humans with ≥1 extracted relation: **{with_rel}**",
             "- Each relation cites the host article it was read from; a `—` target "
             "QID means the relative is itself a deleted item (link after recreation).\n",
             "## Per human\n"]
    for qid, en, ja, rels in sorted(rows, key=lambda r: (-len(r[3]), r[0])):
        if not rels:
            lines.append(f"- **{en}** ({ja}) `{qid}`: — no labeled relation found")
            continue
        parts = [f"{r['relation']} = {r.get('target_label_en')} "
                 f"[{r.get('target_qid') or 'deleted/unresolved'}] (cite [[{r['source_page']}]])"
                 for r in rels]
        lines.append(f"- **{en}** ({ja}) `{qid}`: " + "; ".join(parts))
    with open(os.path.join(ITEMS_DIR, "_relations_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nExtracted relations for {with_rel} humans.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
