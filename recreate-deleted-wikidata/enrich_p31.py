#!/usr/bin/env python3
"""Assign each recreation candidate a P31 (instance of) + English description from the
entity NAME — the reliable Shinto signal — not the fandom host-page categories (which
describe the page, not the deleted ill-target) and not jawiki (these names have no jawiki
articles). Emma 2026-07-06: "a property of instance of (p31) or subclass of."

Classification is driven primarily by the Japanese name suffix, which is essentially
definitional for this domain, with the English label as corroboration:
  祭 / Festival·Matsuri        → festival (Q132241)
  命·尊 / Mikoto·Ōkami         → kami (Q524158)
  社·宮·大社·神宮 / Shrine·Taisha → Shinto shrine (Q845945)
  神 / Kami·Hime·Hiko          → kami (Q524158)   [after shrine, since 神社 ends 社]
  踊 / Odori·Dance             → dance (Q11639)
  連·禰 / Muraji·Sukune, or a clan patronymic "<Clan> no <name>" → human (Q5)
  記·書·抄·経·集 / Record·Mirror → book/text (Q571)
Anything else → null (left for human review — never guessed).

All target QIDs verified against live Wikidata 2026-07-06. Pure local transform; no network.
Writes `enrichment.p31` / `p31_label` / `p31_property` / `description_en` /
`type_source` / `type_confidence` into each candidate's JSON + `items/_p31_summary.md`.
"""
import io
import os
import re
import sys
import glob
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(HERE, "items")

KNOWN_CLANS = (
    "Abe", "Fujiwara", "Nakatomi", "Ōnakatomi", "Onakatomi", "Urabe", "Minamoto",
    "Taira", "Sugawara", "Ki", "Ōe", "Oe", "Kamo", "Inbe", "Imbe", "Ono", "Ban",
    "Kamitsukeno", "Ōtomo", "Otomo", "Mononobe", "Soga", "Ki no", "Saeki",
)
_CLAN_PAT = re.compile(r"^(?:" + "|".join(re.escape(c) for c in KNOWN_CLANS) + r") no \w", re.I)


_PAREN = re.compile(r"\s*[\(（].*?[\)）]\s*$")


def _strip_paren(s):
    """Drop a trailing disambiguator, e.g. 'Akagi Shrine (Niisato Itabashi Town)' →
    'Akagi Shrine' and '赤城神社 (桐生市…)' → '赤城神社', so the type suffix is exposed."""
    prev = None
    s = s or ""
    while s != prev:
        prev = s
        s = _PAREN.sub("", s).strip()
    return s


def _last_word(en):
    words = (en or "").replace("(", " ").replace(")", " ").split()
    return words[-1] if words else ""


def classify(en, ja):
    """Return (p31_qid, p31_label, description, confidence, source)."""
    en = _strip_paren(en or "")
    ja = _strip_paren(ja or "")
    jl = ja[-1] if ja else ""
    last = _last_word(en)

    # Izumo high-priest houses (Senge 千家 / Kitajima 北島) — people.
    if ja.startswith(("千家", "北島")):
        return "Q5", "human", "Japanese historical figure", "medium", "izumo-priest-clan"

    # Festival — 祭 / まつり / Festival / Matsuri.
    if jl == "祭" or ja.endswith(("まつり", "祭り")) or last in ("Festival", "Matsuri"):
        return "Q132241", "festival", "festival in Japan", "high", "name-suffix"
    # Kami by mikoto marker (命·尊 are always kami).
    if jl in ("命", "尊") or last in ("Mikoto", "Ōkami", "Okami", "Ōmikami", "Omikami"):
        return "Q524158", "kami", "kami (Shinto deity)", "high", "name-suffix"
    # Sect-Shinto shrine church (教会) — Izumo-taisha branch churches etc. Emma
    # 2026-07-06: these are P31 Q135437254 "Shrine Church" (verified live: place of
    # worship for Sect Shinto groups). Checked before shrine so 教会 doesn't fall to
    # a 社/宮 rule (it ends 会, but guard the English "Church" too).
    if ja.endswith("教会") or last == "Church":
        return "Q135437254", "shrine church", "Sect Shinto shrine church", "high", "name-suffix"
    # Shinto shrine — check BEFORE bare 神, because 神社/大社/神宮 end in 社/宮.
    if (jl in ("社", "宮") or ja.endswith(("大社", "神宮", "神社"))
            or last in ("Shrine", "Jinja", "Jingū", "Jingu", "Taisha", "Gongen", "Myōjin")
            or last.endswith(("gū", "-gu"))):
        return "Q845945", "Shinto shrine", "Shinto shrine in Japan", "high", "name-suffix"
    # Kami — bare 神 / Kami / Hime / Hiko.
    if jl == "神" or last in ("Kami", "Hime", "Hiko"):
        return "Q524158", "kami", "kami (Shinto deity)", "high", "name-suffix"
    # Buddhist temple — 寺 / -ji / -dera (checked after shrine so 神社 wins).
    if jl == "寺" or last.endswith(("-ji", "-dera")):
        return "Q5393308", "Buddhist temple", "Buddhist temple in Japan", "high", "name-suffix"
    # Kofun GROUP / cluster (群) — checked before single kofun; a cluster of mounds
    # is a distinct type. QID verified live: Japanese kofun groups use Q11411019.
    if ja.endswith("古墳群") or "Kofun Group" in en or "Kofun Cluster" in en:
        return "Q11411019", "kofun group", "group of kofun (ancient Japanese burial mounds)", "high", "name-suffix"
    # Kofun (ancient burial mound).
    if jl == "墳" or last == "Kofun":
        return "Q1141225", "kofun", "kofun (ancient Japanese burial mound)", "high", "name-suffix"
    # Dance.
    if jl == "踊" or last in ("Odori", "Dance"):
        return "Q11639", "dance", "Japanese traditional dance", "medium", "name-suffix"
    # Human — kabane titles or a clan patronymic.
    if jl in ("連", "禰") or last in ("Muraji", "Sukune", "Omi", "Ason") or _CLAN_PAT.match(en):
        return "Q5", "human", "Japanese historical figure", "medium", "name-pattern"
    # Text / document.
    if jl in ("記", "書", "抄", "経", "集") or last in ("Record", "Mirror", "Mirrors", "Collection"):
        return "Q571", "book", "Japanese historical text", "medium", "name-suffix"
    return None, None, None, "none", None


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    files = sorted(glob.glob(os.path.join(ITEMS_DIR, "Q*.json")))
    rows, typed = [], 0
    from collections import Counter
    by_type = Counter()
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if not rec.get("recreation_candidate"):
            continue
        fandom = rec.get("fandom") or {}
        en = rec.get("recovered_label") or fandom.get("label")
        ja = fandom.get("langlinks", {}).get("ja")
        qid, lab, desc, conf, src = classify(en, ja)
        enr = rec.setdefault("enrichment", {})
        enr["p31"] = qid
        enr["p31_label"] = lab
        enr["p31_property"] = "P31" if qid else None
        enr["description_en"] = desc
        enr["type_confidence"] = conf
        enr["type_source"] = src
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2, sort_keys=True)
        typed += bool(qid)
        by_type[lab or "(none — review)"] += 1
        rows.append((rec["qid"], en or "", ja or "", lab or "", conf))

    lines = ["# Recreation-candidate P31 (instance of) — from entity name\n",
             f"- Candidates: **{len(rows)}**",
             f"- Assigned a P31: **{typed}**  ·  left for review: **{len(rows) - typed}**\n",
             "Classifier: Japanese name suffix (definitional) + English label; see "
             "`enrich_p31.py` docstring. Uncertain → null, never guessed.\n",
             "## Type distribution\n"]
    for t, n in by_type.most_common():
        lines.append(f"- {t}: {n}")
    lines += ["\n## Per-candidate\n", "| QID | en | ja | P31 | conf |", "|---|---|---|---|---|"]
    for qid, en, ja, lab, conf in sorted(rows, key=lambda r: (r[3] or "~", r[0])):
        lines.append(f"| {qid} | {en} | {ja} | {lab} | {conf} |")
    with open(os.path.join(ITEMS_DIR, "_p31_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Classified {len(rows)} candidates; {typed} got a P31, "
          f"{len(rows) - typed} left for review.")
    print("Types:", dict(by_type))
    return 0


if __name__ == "__main__":
    sys.exit(main())
