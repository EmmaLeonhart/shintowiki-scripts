#!/usr/bin/env python3
"""
fix_sexagenary_mt_entropy.py
============================
Cleans machine-translation entropy from git_synced/ Sexagenary cycle pages.

The 60 ``<Yang|Yin> <Element> <Animal>.wiki`` files under ``git_synced/`` carry
a leading instruction comment asking that the pages be standardized and have
their minor machine-translation entropy stripped. Concretely the pages share
these systemic defects:

  * Every page emits ``[[Category:qq]]`` from an unsubstituted ``qq=`` param.
  * Most ``{{ill|...}}`` calls have the same named params (``comment=``,
    ``lt=``, ``1=``..``13=``) repeated 4-7 times back to back.
  * Every ``{{wikidata link|<QID>|...}}`` ends with interwiki labels from
    a different Sexagenary page mashed onto the correct ones.
  * Sundry empty ``qq=`` parameters in inline templates, and a few
    ``\\s{2,}`` double-spaces in lede sentences.

This script applies the following idempotent transforms in place:

  1. Strip empty ``qq=`` params from every template.
  2. Inside any ``{{template|...}}``, dedupe named params (keep first
     occurrence by key).
  3. Inside ``{{wikidata link|QID|...}}``, dedupe positional interwiki
     pairs by language code (keep the first ``|lang|label`` pair).
  4. Remove standalone ``[[Category:qq]]`` lines.
  5. Collapse runs of intra-line double-spaces to one.

It does NOT touch:

  * The leading instruction comment.
  * ``==Events==`` / ``==Years==`` / ``==Months==`` / ``==Days==`` content
    (the "intentional content" the comment asks us to preserve).
  * Structural prose variations between pages — that's a bigger rewrite.

This is a local-files-only script. The ``sync_git_synced_pages`` cron job
detects the SHA change and pushes the cleaned text to the wiki on its next
run. No wiki credentials needed.

Usage:  python3 shinto_miraheze/fix_sexagenary_mt_entropy.py [--apply]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "git_synced"

STEMS = ["Yang", "Yin"]
ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]
ANIMALS_YANG = ["Rat", "Tiger", "Dragon", "Horse", "Monkey", "Dog"]
ANIMALS_YIN = ["Ox", "Rabbit", "Snake", "Goat", "Rooster", "Pig"]


def sexagenary_files() -> list[Path]:
    files: list[Path] = []
    for stem in STEMS:
        animals = ANIMALS_YANG if stem == "Yang" else ANIMALS_YIN
        for elem in ELEMENTS:
            for animal in animals:
                p = ROOT / f"{stem} {elem} {animal}.wiki"
                if p.exists():
                    files.append(p)
    return files


def split_top_level(s: str, delim: str = "|") -> list[str]:
    """Split s on delim, respecting nested ``{{ }}`` and ``[[ ]]``."""
    parts: list[str] = []
    cur: list[str] = []
    depth_brace = 0
    depth_bracket = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if c == "{" and nxt == "{":
            depth_brace += 1
            cur.append("{{")
            i += 2
            continue
        if c == "}" and nxt == "}":
            depth_brace -= 1
            cur.append("}}")
            i += 2
            continue
        if c == "[" and nxt == "[":
            depth_bracket += 1
            cur.append("[[")
            i += 2
            continue
        if c == "]" and nxt == "]":
            depth_bracket -= 1
            cur.append("]]")
            i += 2
            continue
        if c == delim and depth_brace == 0 and depth_bracket == 0:
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    parts.append("".join(cur))
    return parts


NAMED_PARAM_RE = re.compile(r"^\s*([A-Za-z0-9_\-]+)\s*=")


def is_named_param(p: str) -> tuple[bool, str, str]:
    m = NAMED_PARAM_RE.match(p)
    if not m:
        return False, "", p
    key = m.group(1)
    val = p[m.end():]
    return True, key, val


def fix_wikidata_link(parts: list[str]) -> list[str]:
    """Dedup ``{{wikidata link|QID|lang1|label1|lang2|label2|...}}`` by lang.

    ``parts`` is the list of pipe-split parts of the template body, including
    the head ("wikidata link") as parts[0] and QID as parts[1].
    """
    if len(parts) < 2:
        return parts
    head = parts[0]
    qid = parts[1]
    body = parts[2:]
    seen_lang: set[str] = set()
    out: list[str] = []
    i = 0
    while i < len(body):
        t = body[i]
        named, key, _val = is_named_param(t)
        if named:
            # named in the middle of pairs — pass through; doesn't affect parity
            out.append(t)
            i += 1
            continue
        lang = t.strip()
        if i + 1 < len(body) and not is_named_param(body[i + 1])[0]:
            label = body[i + 1]
            if not lang or lang in seen_lang:
                i += 2
                continue
            seen_lang.add(lang)
            out.extend([t, label])
            i += 2
        else:
            # dangling positional, pass through
            out.append(t)
            i += 1
    return [head, qid] + out


def fix_generic_template(parts: list[str]) -> list[str]:
    """For most templates: dedupe named params (keep first), strip empty qq=,
    leave positionals as-is."""
    head = parts[0]
    tail = parts[1:]
    seen: set[str] = set()
    out: list[str] = []
    for p in tail:
        named, key, val = is_named_param(p)
        if named:
            if key == "qq" and val.strip() == "":
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        else:
            out.append(p)
    return [head] + out


def fix_ill_template(parts: list[str]) -> list[str]:
    """For ``{{ill|<en title>|<lang1>|<page1>|...|named=val...}}``:

    * Keep the first positional (en title).
    * Walk the rest: bare positionals are interpreted as ``(lang, page)`` pairs
      and deduped by lang (keep first pair per lang); named params are deduped
      by key.
    * Empty ``qq=`` is stripped.
    """
    head = parts[0]
    tail = parts[1:]
    if not tail:
        return [head]
    en_title = tail[0]
    rest = tail[1:]

    seen_named: set[str] = set()
    seen_lang: set[str] = set()
    out_pairs: list[str] = []
    out_named: list[str] = []

    i = 0
    while i < len(rest):
        t = rest[i]
        named, key, val = is_named_param(t)
        if named:
            if key == "qq" and val.strip() == "":
                i += 1
                continue
            if key in seen_named:
                i += 1
                continue
            seen_named.add(key)
            out_named.append(t)
            i += 1
        else:
            # bare positional — treat as start of a (lang, page) pair
            lang = t.strip()
            if i + 1 < len(rest) and not is_named_param(rest[i + 1])[0]:
                page = rest[i + 1]
                if lang and lang not in seen_lang:
                    seen_lang.add(lang)
                    out_pairs.extend([t, page])
                i += 2
            else:
                # dangling, pass through
                out_pairs.append(t)
                i += 1

    return [head, en_title] + out_pairs + out_named


def transform_template(body: str) -> str:
    """Apply per-template fixes to the inside of ``{{ ... }}``."""
    parts = split_top_level(body, "|")
    head_lower = parts[0].strip().lower()
    if head_lower == "wikidata link":
        parts = fix_wikidata_link(parts)
    elif head_lower == "ill":
        parts = fix_ill_template(parts)
    else:
        parts = fix_generic_template(parts)
    return "|".join(parts)


def transform_text(text: str) -> str:
    """Walk the text, recursing into every ``{{ ... }}`` and applying fixes."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i:i + 2] == "{{":
            depth = 1
            j = i + 2
            while j < n:
                if text[j:j + 2] == "{{":
                    depth += 1
                    j += 2
                elif text[j:j + 2] == "}}":
                    depth -= 1
                    j += 2
                    if depth == 0:
                        break
                else:
                    j += 1
            if depth != 0:
                # unbalanced — bail and emit literally
                out.append(text[i:])
                return "".join(out)
            body = text[i + 2:j - 2]
            body = transform_text(body)  # recurse into nested templates first
            new_body = transform_template(body)
            out.append("{{" + new_body + "}}")
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


CATEGORY_QQ_RE = re.compile(r"^\[\[Category:qq\]\][ \t]*\n?", re.MULTILINE)
INTRA_LINE_DOUBLE_SPACE_RE = re.compile(r"(?<=\S) {2,}")
MULTI_BLANK_LINE_RE = re.compile(r"\n{3,}")


# ─── Lede prose normalization ─────────────────────────────────────────────────
# Every page's first prose line is a single-sentence lede introducing the
# combination. The 60 files have it phrased five+ different ways ("is one of
# the", "is one element of", "is the Nth combination of", "is one of the
# stems-and-branches combinations in the traditional Chinese calendar", etc.)
# — pure machine-translation entropy. The canonical fields live in the
# preceding ``{{infobox Chinese|l=…|kanji=…|romaji=…|onyomi=…}}`` so we
# regenerate the lede deterministically from those.

INFOBOX_CHINESE_RE = re.compile(r"\{\{infobox Chinese\s*\|", re.IGNORECASE)

STEMS_KANJI = "甲乙丙丁戊己庚辛壬癸"      # 1-10
BRANCHES_KANJI = "子丑寅卯辰巳午未申酉戌亥"  # 1-12


def parse_infobox_chinese(text: str) -> dict[str, str] | None:
    m = INFOBOX_CHINESE_RE.search(text)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    n = len(text)
    while i < n:
        if text[i:i + 2] == "{{":
            depth += 1
            i += 2
        elif text[i:i + 2] == "}}":
            depth -= 1
            if depth == 0:
                break
            i += 2
        else:
            i += 1
    body = text[start:i]
    params: dict[str, str] = {}
    for p in split_top_level(body, "|"):
        if "=" in p:
            k, _, v = p.partition("=")
            params[k.strip()] = v.strip()
    return params


def sexagenary_ordinal(kanji: str) -> int | None:
    """Return the 1-based ordinal (1..60) for a stem+branch kanji pair."""
    if not kanji or len(kanji) != 2:
        return None
    s = STEMS_KANJI.find(kanji[0])
    b = BRANCHES_KANJI.find(kanji[1])
    if s < 0 or b < 0:
        return None
    for x in range(60):
        if x % 10 == s and x % 12 == b:
            return x + 1
    return None


def english_ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_canonical_lede(params: dict[str, str]) -> str | None:
    l = params.get("l", "").strip()
    kanji = params.get("kanji", "").strip()
    romaji = params.get("romaji", "").strip()
    onyomi = params.get("onyomi", "").strip()
    if not l or not kanji:
        return None
    ord_n = sexagenary_ordinal(kanji)
    position = f"the {english_ordinal(ord_n)} of the sixty combinations" if ord_n else "one of the sixty combinations"
    paren_bits: list[str] = [kanji]
    if romaji:
        paren_bits.append(f"''{romaji}''")
    paren = ", ".join(paren_bits)
    if onyomi:
        paren = f"{paren}; onyomi ''{onyomi}''"
    return (
        f"'''{l}''' ({paren}) is {position} of the "
        f"{{{{ill|Sexagenary cycle|en|Sexagenary cycle|qid=Q246658"
        f"|lt=Sexagenary cycle|1=Sexagenary cycle}}}}."
    )


def replace_lede(text: str) -> str:
    """Replace the first prose paragraph (from the first line starting with
    ``'''`` until the first blank line) with a canonical lede derived from
    ``{{infobox Chinese|...}}``. No-op if the infobox is missing required
    fields or no ``'''`` lede line is found."""
    params = parse_infobox_chinese(text)
    if not params:
        return text
    canonical = build_canonical_lede(params)
    if not canonical:
        return text

    lines = text.split("\n")
    # Find first line that opens with '''
    i = 0
    while i < len(lines) and not lines[i].lstrip().startswith("'''"):
        i += 1
    if i >= len(lines):
        return text
    # Find end of paragraph (first subsequent blank line)
    j = i
    while j < len(lines) and lines[j].strip() != "":
        j += 1
    # Replace lines[i:j] with the single canonical line
    new_lines = lines[:i] + [canonical] + lines[j:]
    return "\n".join(new_lines)


# ─── Stem / branch / wuxing data tables ───────────────────────────────────────
# Indexed by position 0..N-1.

STEM_DATA = [
    # (kanji, pinyin, romaji_kunyomi, romaji_onyomi, yin_yang, element)
    ("甲", "jiǎ", "kinoe",    "kō",   "Yang", "Wood"),
    ("乙", "yǐ",  "kinoto",   "otsu", "Yin",  "Wood"),
    ("丙", "bǐng", "hinoe",   "hei",  "Yang", "Fire"),
    ("丁", "dīng", "hinoto",  "tei",  "Yin",  "Fire"),
    ("戊", "wù",  "tsuchinoe", "bo",   "Yang", "Earth"),
    ("己", "jǐ",  "tsuchinoto","ki",   "Yin",  "Earth"),
    ("庚", "gēng", "kanoe",   "kō",   "Yang", "Metal"),
    ("辛", "xīn",  "kanoto",  "shin", "Yin",  "Metal"),
    ("壬", "rén",  "mizunoe", "jin",  "Yang", "Water"),
    ("癸", "guǐ", "mizunoto", "ki",   "Yin",  "Water"),
]

BRANCH_DATA = [
    # (kanji, pinyin, romaji_kunyomi, romaji_onyomi, yin_yang, element, animal_en)
    ("子", "zǐ",   "ne",    "shi",  "Yang", "Water", "Rat"),
    ("丑", "chǒu", "ushi",  "chū",  "Yin",  "Earth", "Ox"),
    ("寅", "yín",  "tora",  "in",   "Yang", "Wood",  "Tiger"),
    ("卯", "mǎo",  "u",     "bō",   "Yin",  "Wood",  "Rabbit"),
    ("辰", "chén", "tatsu", "shin", "Yang", "Earth", "Dragon"),
    ("巳", "sì",   "mi",    "shi",  "Yin",  "Fire",  "Snake"),
    ("午", "wǔ",   "uma",   "go",   "Yang", "Fire",  "Horse"),
    ("未", "wèi",  "hitsuji","bi",  "Yin",  "Earth", "Goat"),
    ("申", "shēn", "saru",  "shin", "Yang", "Metal", "Monkey"),
    ("酉", "yǒu",  "tori",  "yū",   "Yin",  "Metal", "Rooster"),
    ("戌", "xū",   "inu",   "jutsu","Yang", "Earth", "Dog"),
    ("亥", "hài",  "i",     "gai",  "Yin",  "Water", "Pig"),
]

STEM_BY_KANJI = {s[0]: s for s in STEM_DATA}
BRANCH_BY_KANJI = {b[0]: b for b in BRANCH_DATA}

WUXING_GENERATES = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal",
                    "Metal": "Water", "Water": "Wood"}
WUXING_DESTROYS = {"Wood": "Earth", "Earth": "Water", "Water": "Fire",
                   "Fire": "Metal", "Metal": "Wood"}


def wuxing_relationship(stem_elem: str, branch_elem: str) -> str:
    if stem_elem == branch_elem:
        return "Biwa (Mutual Harmony)"
    if (WUXING_GENERATES.get(stem_elem) == branch_elem
            or WUXING_GENERATES.get(branch_elem) == stem_elem):
        return "Mutual Generation"
    if (WUXING_DESTROYS.get(stem_elem) == branch_elem
            or WUXING_DESTROYS.get(branch_elem) == stem_elem):
        return "Mutual Destruction"
    return "Biwa (Mutual Harmony)"  # fallback; shouldn't trigger


def sexagenary_name(ordinal: int) -> tuple[str, str]:
    """Return ``(english_name, kanji)`` for ordinal 1..60."""
    n = (ordinal - 1) % 60
    stem = STEM_DATA[n % 10]
    branch = BRANCH_DATA[n % 12]
    name = f"{stem[4]} {stem[5]} {branch[6]}"
    kanji = stem[0] + branch[0]
    return name, kanji


# ─── Page section extraction + rewrite ────────────────────────────────────────

# Strict regexes that pin to the start of a line — avoid matching headers
# embedded in prose.
H2_RE = re.compile(r"^==[^=].*?==[ \t]*$", re.MULTILINE)


def find_section_starts(text: str) -> list[tuple[int, str]]:
    """Return list of ``(line_start_offset, heading_text)`` for each ==H2== in
    file order."""
    return [(m.start(), m.group()) for m in H2_RE.finditer(text)]


def parse_page(text: str) -> dict:
    """Pull the structured slots we need to regenerate the page."""
    info = parse_infobox_chinese(text) or {}
    l = info.get("l", "")
    kanji = info.get("kanji", "")
    romaji = info.get("romaji", "")
    onyomi = info.get("onyomi", "")

    out: dict = {
        "infobox": info,
        "l": l,
        "kanji": kanji,
        "romaji": romaji,
        "onyomi": onyomi,
        "ordinal": sexagenary_ordinal(kanji) if kanji else None,
    }

    if out["ordinal"]:
        out["year_mod_60"] = (out["ordinal"] + 3) % 60 or 60
        prev_ord = ((out["ordinal"] - 2) % 60) + 1
        next_ord = (out["ordinal"] % 60) + 1
        out["prev_name"], out["prev_kanji"] = sexagenary_name(prev_ord)
        out["next_name"], out["next_kanji"] = sexagenary_name(next_ord)
    else:
        out["year_mod_60"] = None

    if len(kanji) == 2:
        out["stem"] = STEM_BY_KANJI.get(kanji[0])
        out["branch"] = BRANCH_BY_KANJI.get(kanji[1])
        if out["stem"] and out["branch"]:
            out["wuxing"] = wuxing_relationship(out["stem"][5], out["branch"][5])
    else:
        out["stem"] = out["branch"] = out["wuxing"] = None

    # Extract QID from {{wikidata link|QID|...}} for footer regeneration
    m = re.search(r"\{\{wikidata link\|(Q\d+)", text)
    out["qid"] = m.group(1) if m else None

    # Extract Events section content (lines between === Events === and next heading)
    out["events"] = extract_named_subsection(text, "Events")
    # Extract Day Selection content (rule on what day-of-cycle this is)
    out["day_selection"] = extract_named_subsection(text, "Day Selection")

    # Extract the year table verbatim (we only want to regenerate prose, not
    # the table itself — preserving year QIDs).
    out["year_table"] = extract_year_table(text)
    # Extract any trailing {{translated page|...}} verbatim
    m = re.search(r"\{\{translated page\b[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}", text)
    out["translated_page_tpl"] = m.group(0) if m else None

    # Extract trailing {{wikidata link|...}} verbatim (already dedup'd by an
    # earlier transform pass)
    m = re.search(r"\{\{wikidata link\|[^}]*\}\}", text)
    out["wikidata_link_tpl"] = m.group(0) if m else None

    # Extract category lines
    out["categories"] = re.findall(r"^\[\[Category:[^\]]+\]\]", text, re.MULTILINE)

    return out


def extract_named_subsection(text: str, name: str) -> str | None:
    """Find a heading whose label contains ``name`` (case-insensitive), return
    the body until the next heading of equal-or-higher level. Heading level is
    detected from the matched markup."""
    pattern = re.compile(
        rf"^(?P<eqs>={{2,}}) *[^=\n]*{re.escape(name)}[^=\n]* *(?P=eqs) *$",
        re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(text)
    if not m:
        return None
    level = len(m.group("eqs"))
    body_start = m.end()
    # Find next heading of level <= level
    next_pat = re.compile(rf"^={{1,{level}}}[^=\n]+={{1,{level}}} *$", re.MULTILINE)
    nxt = next_pat.search(text, body_start)
    body_end = nxt.start() if nxt else len(text)
    body = text[body_start:body_end].strip("\n")
    return body if body else None


def extract_year_table(text: str) -> str | None:
    """Return the first ``{| class=\"wikitable\" ... |}`` block."""
    m = re.search(r"\{\|\s*class=\"wikitable\".*?\n\|\}", text, re.DOTALL)
    return m.group(0) if m else None


# ─── Canonical section renderers ──────────────────────────────────────────────

def render_lede(d: dict) -> str:
    return build_canonical_lede(d["infobox"]) or ""


def render_second_paragraph(d: dict) -> str:
    if not (d.get("ordinal") and d.get("stem") and d.get("branch") and d.get("prev_name")):
        return ""
    stem = d["stem"]
    branch = d["branch"]
    rel = d["wuxing"]
    s_kanji, _, _, _, s_yy, s_elem = stem
    b_kanji, _, _, _, b_yy, b_elem, b_animal = branch
    o = d["ordinal"]
    return (
        f"It is the {english_ordinal(o)} of the sixty stem-branch combinations, "
        f"preceded by {{{{ill|{d['prev_name']}|ja|{d['prev_kanji']}|1={d['prev_name']}}}}} "
        f"and followed by {{{{ill|{d['next_name']}|ja|{d['next_kanji']}|1={d['next_name']}}}}}. "
        f"The {{{{ill|Heavenly Stems|en|Heavenly Stems|qid=Q1190985|lt=Heavenly Stem|1=Heavenly Stems}}}} "
        f"''{s_kanji}'' is {s_yy} {s_elem}, and the "
        f"{{{{ill|Earthly Branches|en|Earthly Branches|qid=Q1072961|lt=Earthly Branch|1=Earthly Branches}}}} "
        f"''{b_kanji}'' ({b_animal}) is {b_yy} {b_elem}; "
        f"together they form a {rel} relationship in "
        f"{{{{ill|Wuxing (Chinese philosophy)|en|Wuxing (Chinese philosophy)|qid=Q218652|lt=Wuxing|1=Wuxing (Chinese philosophy)}}}}."
    )


def render_pronunciation(d: dict) -> str:
    info = d["infobox"]
    l = info.get("l", "")
    kanji = info.get("kanji", "")
    pinyin = info.get("p", "")
    jyutping = info.get("j", "") or info.get("y", "")
    romaji = info.get("romaji", "")
    onyomi = info.get("onyomi", "")
    lines = [
        "==Pronunciation==",
        f"* English: {l} ({kanji})",
    ]
    if pinyin:
        lines.append(f"** Chinese (Mandarin Pinyin): {pinyin}")
    if jyutping:
        lines.append(f"** Cantonese (Jyutping): {jyutping}")
    lines.append("** Japanese:")
    if romaji:
        lines.append(f"*** Kun'yomi: {romaji}")
    if onyomi:
        lines.append(f"*** On'yomi: {onyomi}")
    return "\n".join(lines)


def render_years_intro(d: dict) -> str:
    if not d.get("year_mod_60") or not d.get("l"):
        return ""
    r = d["year_mod_60"]
    return (
        f"A {{{{ill|Common Era|en|Common Era|qid=Q208141|lt=Common Era|1=Common Era}}}} "
        f"year that leaves a remainder of {r} when divided by 60 is a year of {d['l']} ({d['kanji']})."
    )


def normalize_year_table(year_table: str, d: dict) -> str:
    """Normalize the caption of a year table to use the English page name.
    Preserves all year rows (and their QIDs) verbatim."""
    if not year_table or not d.get("l"):
        return year_table
    # Replace any |+'''...''' caption with the canonical one
    canonical_caption = f"|+ '''Years of {d['l']} ({d['kanji']})'''"
    new = re.sub(
        r"\|\+[ \t]*'''[^']*'''",
        canonical_caption,
        year_table,
        count=1,
    )
    return new


def render_years_section(d: dict) -> str | None:
    if not d.get("year_table"):
        return None
    parts = [
        f"==Years of {d['l']}==",
        render_years_intro(d),
        normalize_year_table(d["year_table"], d),
    ]
    if d.get("events"):
        parts += ["", "=== Events ===", d["events"]]
    return "\n".join(p for p in parts if p)


def render_days_section(d: dict) -> str | None:
    if not d.get("day_selection"):
        return None
    return f"==Days of {d['l']}==\n=== Day Selection ===\n{d['day_selection']}"


def render_see_also(d: dict) -> str:
    return "==See Also==\n* {{prefix}}\n* {{intitle}}"


def render_footer(d: dict) -> str:
    parts: list[str] = []
    if d.get("translated_page_tpl"):
        parts.append(d["translated_page_tpl"])
        parts.append("")
    if d.get("wikidata_link_tpl"):
        parts.append(d["wikidata_link_tpl"])
    # Categories, deduped, qq removed
    seen: set[str] = set()
    for c in d.get("categories", []):
        if c == "[[Category:qq]]":
            continue
        if c in seen:
            continue
        seen.add(c)
        parts.append(c)
    return "\n".join(parts)


def replace_second_paragraph(text: str) -> str:
    """Replace the second prose paragraph (the "It is the Nth combination…
    Heavenly Stem … Earthly Branch …" sentence) with a canonical version
    generated from stem/branch data. No-op if the required data isn't
    available or no second paragraph is found."""
    d = parse_page(text)
    canonical = render_second_paragraph(d)
    if not canonical:
        return text

    lines = text.split("\n")
    # Skip past lede (first ''' line) and its trailing blank
    i = 0
    while i < len(lines) and not lines[i].lstrip().startswith("'''"):
        i += 1
    if i >= len(lines):
        return text
    i += 1
    # Skip blank line(s)
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines):
        return text
    # Second paragraph runs from here until next blank line or heading
    start = i
    while i < len(lines) and lines[i].strip() != "" and not lines[i].lstrip().startswith("="):
        i += 1
    end = i
    if end == start:
        return text
    # Only replace if the existing paragraph references either ``Sexagenary``,
    # ``Heavenly Stem``, or ``Earthly Branch`` — i.e. looks like the canonical
    # stem-branch description. Avoid clobbering an unrelated paragraph.
    existing = "\n".join(lines[start:end])
    keywords = ("Heavenly Stem", "Earthly Branch", "Sexagenary cycle",
                "Yin-Yang", "Yin Yang", "Yang Earth", "Yin Earth")
    if not any(k in existing for k in keywords):
        return text
    new_lines = lines[:start] + [canonical] + lines[end:]
    return "\n".join(new_lines)


YEAR_TABLE_CAPTION_RE = re.compile(r"\|\+[ \t]*'''[^']*'''")
YEAR_INTRO_RE = re.compile(
    r"^[^\n]*\bdivided by 60\b[^\n]*$",
    re.MULTILINE,
)


def normalize_year_block(text: str) -> str:
    """Normalize the year-table caption and the year-intro sentence to use
    the English page name uniformly, replacing per-page Romanized aliases
    like ''Years of Wuxu'' / ''year of Earth Dragon''."""
    d = parse_page(text)
    l = d.get("l")
    kanji = d.get("kanji")
    r = d.get("year_mod_60")
    if not l or not kanji or not r:
        return text
    canonical_caption = f"|+ '''Years of {l} ({kanji})'''"
    text = YEAR_TABLE_CAPTION_RE.sub(canonical_caption, text, count=1)
    canonical_intro = (
        f"A {{{{ill|Common Era|en|Common Era|qid=Q208141|lt=Common Era|"
        f"1=Common Era}}}} year that leaves a remainder of {r} when divided "
        f"by 60 is a year of {l} ({kanji})."
    )
    text = YEAR_INTRO_RE.sub(canonical_intro, text, count=1)
    return text


def clean_file_text(text: str) -> str:
    text = transform_text(text)
    text = CATEGORY_QQ_RE.sub("", text)
    text = INTRA_LINE_DOUBLE_SPACE_RE.sub(" ", text)
    text = replace_lede(text)
    text = replace_second_paragraph(text)
    text = normalize_year_block(text)
    text = MULTI_BLANK_LINE_RE.sub("\n\n", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Write changes. Without this flag, runs dry.")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    files = sexagenary_files()
    print(f"Scanning {len(files)} Sexagenary cycle files under {ROOT}")
    changed = 0
    total_delta = 0
    for f in files:
        orig = f.read_text(encoding="utf-8")
        new = clean_file_text(orig)
        if new == orig:
            continue
        changed += 1
        delta = len(new) - len(orig)
        total_delta += delta
        print(f"  {f.name}: {len(orig)} -> {len(new)} ({delta:+d})")
        if args.apply:
            f.write_text(new, encoding="utf-8")

    mode = "applied" if args.apply else "dry-run"
    print(f"{changed}/{len(files)} files changed ({mode}). "
          f"Net char delta: {total_delta:+d}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
