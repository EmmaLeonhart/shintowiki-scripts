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


def clean_file_text(text: str) -> str:
    text = transform_text(text)
    text = CATEGORY_QQ_RE.sub("", text)
    text = INTRA_LINE_DOUBLE_SPACE_RE.sub(" ", text)
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
