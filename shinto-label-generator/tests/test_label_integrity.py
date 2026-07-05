"""Cross-generator integrity invariants over every committed label/alias line.

These lock in audit dimensions that were verified clean on 2026-07-05 but had no
test — so a future CI regen (which regenerates the .txt from the generators) can't
silently reintroduce them, the way it did with the kami-exclusion and whitespace
fixes earlier. Each check is over the committed quickstatements/*.txt files.
"""

import glob
import os

_QS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "quickstatements")


def _label_lines():
    """Yield (filename, qid, prop, value_field) for every L*/A* line."""
    for path in glob.glob(os.path.join(_QS, "*.txt")):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 3 and parts[1].startswith(("L", "A")):
                    yield name, parts[0], parts[1], parts[2], line


def _is_forbidden_char(cp):
    # C0/C1 controls (+DEL), BOM/ZWNBSP, zero-width space, bidi embed/override/isolate.
    # NB: ZWNJ/ZWJ (U+200C/D) are NOT forbidden — legitimate joiners in Arabic/
    # Persian/Indic scripts.
    return (cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F
            or cp == 0xFEFF or cp == 0x200B
            or 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069)


def test_no_control_or_format_chars():
    bad = []
    for name, qid, prop, val, _ in _label_lines():
        inner = val.strip('"')
        if any(_is_forbidden_char(ord(c)) for c in inner):
            bad.append((name, qid, prop))
    assert not bad, f"{len(bad)} labels carry control/format chars; e.g. {bad[:5]}"


def test_quickstatements_quoting_well_formed():
    """Value field must be \"...\" with every internal quote doubled — otherwise the
    QuickStatements submitter mis-parses the line."""
    bad = []
    for name, qid, prop, val, _ in _label_lines():
        if not (val.startswith('"') and val.endswith('"') and len(val) >= 2):
            bad.append((name, qid, prop, "not-quoted"))
            continue
        inner = val[1:-1]
        if inner.replace('""', '').count('"'):   # a lone, undoubled quote
            bad.append((name, qid, prop, "unescaped-quote"))
    assert not bad, f"{len(bad)} malformed QS-quoted values; e.g. {bad[:5]}"


def test_no_exact_duplicate_lines_within_a_file():
    dupes = []
    for path in glob.glob(os.path.join(_QS, "*.txt")):
        seen = set()
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if line.startswith("#") or not line.strip():
                    continue
                if line in seen:
                    dupes.append((os.path.basename(path), line[:60]))
                seen.add(line)
    assert not dupes, f"{len(dupes)} exact-duplicate lines; e.g. {dupes[:5]}"
