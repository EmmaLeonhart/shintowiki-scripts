#!/usr/bin/env python3
"""The site's home page IS the QuickStatements batch: every line, randomly shuffled.

Emma, 2026-09-28: no more automated Wikidata edits or item creations. Everything goes
through QuickStatements, run by hand. The home page is a randomly sorted list of all the
QuickStatements, modelled on the genealogy repo's batch page, and the previous home page
moved to legacy.html.

What goes in:
  * every line of every drip file (direct_daily_edits.ATOMIC_FILES, read from its source so
    no credentials are needed, DRIP-PAUSED entries excluded), in QuickStatements v1 syntax,
    tab-separated;
  * sequential_misc.txt as ONE block in its own order (its remove/rebuild pairs must run in
    sequence);
  * every item-creation batch (create_items.GATES), minus blocks already created according
    to the batch's .state file.

Blocks that must stay together move together through the shuffle: a CREATE block with its
LAST lines, a `||` compound line (description, then label), and sequential_misc. The order
is new on every build.

Writes _site/index.html and _site/quickstatements-all.txt.
"""
import html
import io
import json
import os
import random
import re
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MQ = os.path.join(ROOT, "modern-quickstatements")
SITE = os.path.join(ROOT, "_site")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_qs_home_page.html")
SPLIT = re.compile(r'\|(?=(?:[^"]*"[^"]*")*[^"]*$)')          # a pipe outside quotes
COMPOUND = re.compile(r'\|\|(?=(?:[^"]*"[^"]*")*[^"]*$)')      # `||` outside quotes


def atomic_files():
    """Registered drip files, read from direct_daily_edits.py's ATOMIC_FILES block."""
    src = io.open(os.path.join(MQ, "direct_daily_edits.py"), encoding="utf-8").read()
    block = re.search(r"^ATOMIC_FILES = \[(.*?)^\]", src, re.S | re.M).group(1)
    return re.findall(r'^\s*"([^"]+\.txt)",', block, re.M)


def create_batches():
    """Batch files registered in create_items.GATES."""
    src = io.open(os.path.join(MQ, "create_items.py"), encoding="utf-8").read()
    block = re.search(r"^GATES = \{(.*?)^\}", src, re.S | re.M).group(1)
    return re.findall(r'^\s*"([^"]+\.txt)":', block, re.M)


def to_v1(line):
    """One QuickStatements line in v1 syntax: tab-separated, comments dropped."""
    line = line.split("    #")[0].strip()
    if "\t" in line:
        return line
    return "\t".join(p.strip() for p in SPLIT.split(line))


def read(path):
    try:
        return [l.rstrip("\n") for l in io.open(path, encoding="utf-8")]
    except FileNotFoundError:
        return []


def never_touch():
    """QIDs no QuickStatements line may touch (never_touch_qids.txt). Emma, 2026-10-09: the
    category and disambiguation items whose labels Wikidata refused "just straight up make it so
    that the pipeline never touches those QIDs"."""
    return {l.split("#")[0].strip() for l in read(os.path.join(MQ, "never_touch_qids.txt"))} - {""}


def drip_units():
    skip = never_touch()
    units = []
    for fn in atomic_files():
        for raw in read(os.path.join(MQ, fn)):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            parts = [p for p in COMPOUND.split(raw.split("    #")[0]) if p.strip()]
            unit = [to_v1(p) for p in parts]
            if any(l.split("\t")[0].lstrip("-") in skip for l in unit):
                continue
            units.append(unit)
    return units


def sequential_cursor(lines):
    """Index of the first sequential_misc line not yet run, from sequential_misc.state.

    Same rule as direct_daily_edits.load_sequential_cursor: a recorded `next_line` wins when it
    is still in the file, otherwise the stored index stands."""
    try:
        state = json.load(io.open(os.path.join(MQ, "sequential_misc.state"), encoding="utf-8"))
        cursor = int(state.get("cursor", 0))
    except Exception:
        return 0
    marker = state.get("next_line")
    if marker and marker in lines:
        return lines.index(marker)
    return cursor


def sequential_lines():
    return [l.strip() for l in read(os.path.join(MQ, "sequential_misc.txt"))
            if l.strip() and not l.lstrip().startswith("#")]


def sequential_unit():
    """The sequential_misc lines not yet run, as ONE unit in file order.

    2026-10-09: this used to send the whole file every round, so its 32 lines (removals that
    had long since run) went into every QuickStatements round and the rounds could never reach
    0 lines. Only lines past the cursor go out now; build_browser_round.py moves the cursor
    past what a finished round sent."""
    lines = sequential_lines()
    lines = lines[sequential_cursor(lines):]
    return [[to_v1(l) for l in lines]] if lines else []


def block_label(block):
    for lang in ("en", "ja"):
        for l in block:
            m = re.match(r'^LAST\|L' + lang + r'\|"(.*)"$', l)
            if m:
                return m.group(1)
    return None


def create_units():
    units = []
    for fn in create_batches():
        path = os.path.join(MQ, fn)
        try:
            done = json.load(io.open(os.path.splitext(path)[0] + ".state", encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            done = {}
        blocks, block = [], None
        for raw in read(path):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if s == "CREATE":
                if block:
                    blocks.append(block)
                block = [s]
            elif block is not None:
                block.append(s)
        if block:
            blocks.append(block)
        units += [b for b in blocks if block_label(b) not in done]     # already created: out
    return [[to_v1(l) if l != "CREATE" else l for l in b] for b in units]


def build_units(seed=None):
    """The shuffled units (each a list of lines that must stay together), before flattening."""
    units = drip_units() + sequential_unit() + create_units()
    random.Random(seed).shuffle(units)
    return units


def build(seed=None):
    units = build_units(seed)
    lines = [l for u in units for l in u]
    creates = sum(1 for l in lines if l == "CREATE")
    return lines, creates


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    lines, creates = build()
    text = "\n".join(lines) + "\n"
    os.makedirs(SITE, exist_ok=True)
    io.open(os.path.join(SITE, "quickstatements-all.txt"), "w", encoding="utf-8", newline="\n").write(text)
    tpl = io.open(TEMPLATE, encoding="utf-8").read()
    page = tpl % ("Shinto Wikidata QuickStatements", "Shinto Wikidata QuickStatements",
                  "{:,} lines, {:,} item creations".format(len(lines), creates),
                  datetime.date.today().isoformat(), html.escape(text))
    io.open(os.path.join(SITE, "index.html"), "w", encoding="utf-8", newline="\n").write(page)
    print("index.html: {:,} lines ({:,} creations), shuffled; quickstatements-all.txt written".format(
        len(lines), creates))


if __name__ == "__main__":
    main()
