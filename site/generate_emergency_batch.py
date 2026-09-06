"""The EMERGENCY BATCH page — every generated QuickStatement, in one place, in run order.

Emma, 2026-09-06: *"The emergency batch is supposed to try to apply labels to all orphaned
description shrines first, and then goes through every single other edit"*, and
*"Is there a page that's just every single quickstatement we made on one page for easy
execution?"*

The answer to that second question was NO, which is why this exists. What was there:

    _site/daily.html            200 lines shown, of a 10,929-line concatenation
    daily_operations.txt        10,929 lines — a SUBSET, not the whole
    the real total              125,681 lines across 73 ATOMIC_FILES

So the existing page was a 200-line window onto 8% of the work. This is the whole thing.

RUN ORDER, WHICH IS THE POINT AND NOT COSMETIC
----------------------------------------------
Block 1 is the orphan-description labels; everything else follows. That ordering is Emma's
and it is load-bearing:

  * An item with a description and no label in that language is an orphan. Wikidata's
    uniqueness constraint is on the (label, description) PAIR, so the description stakes the
    half that matters least, and when a label finally arrives the completed pair can collide
    — and it is the LABEL edit that gets rejected. A description with no label costs a label.
  * The established remedy (`audit_orphan_descriptions.py`) DELETES the description. That is
    right only where no label exists. Measured 2026-09-06: 9,976 of 10,250 orphans already
    have a generated label sitting in `shinto-label-generator/`. So for 97% of them the
    deletion throws away a description we could complete instead.
  * Hence: add the label FIRST, keep the description. Fix rather than clear.

⚠ NOTHING IN THIS BATCH DELETES A DESCRIPTION. Checked when this was written:
`orphan_description_removals.txt` is not on disk and is not registered in ATOMIC_FILES. If it
is ever staged, it MUST NOT be added to this page without being sequenced strictly after
block 1 — a removal that runs before its matching label add destroys exactly what the
ordering exists to preserve.

OUTPUT SHAPE
------------
The page links to raw `.txt` batches rather than embedding 135k lines in HTML. A single
textarea of everything would be ~10 MB, would make the page unusable on a phone, and
QuickStatements does not want a paste that size anyway. Each batch is chunked so a chunk can
be pasted, run, and ticked off independently — a run that dies halfway loses only its chunk.

`ALL.txt` IS A SAMPLE, NOT THE CORPUS
-------------------------------------
It held all 131,567 lines until 2026-09-06, and that was the wrong shape for the one thing it
exists for. Emma: *"all.txt is simply too large, largest batches I found pasted in were 10,000
lines each. So we gotta have it be 10,000 randomly selected lines."* A file nobody can paste
is not a convenience.

So it is a random draw of `SAMPLE` lines, and three things follow:

  * The corpus is not lost. The per-file chunks written beside it still hold every line, and
    they are what to work through exhaustively.
  * The draw is unseeded, so each regeneration deals a different hand and repeated runs cover
    the corpus rather than re-offering the same 10,000. `--seed` fixes it when a reproducible
    file is wanted.
  * Lines are SELECTED at random and emitted in the ORIGINAL run order, so the orphan labels
    still lead whatever came up. Only ~8% of the file is orphan labels now, though, where the
    unsampled version led with all 9,976 — if that ordering matters more than the sampling,
    the fix is to take the orphan block whole and sample only the remainder.

This script is READ-ONLY and offline apart from reusing the orphan query result. It never
edits Wikidata and never writes into the atomic files. It renders a page; delivery is still
the operator's paste or the daily drip.

Usage:
    python site/generate_emergency_batch.py
    python site/generate_emergency_batch.py --chunk 5000
"""
import argparse
import collections
import datetime
import glob
import html
import io
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

QS_DIR = os.path.join(REPO_ROOT, "modern-quickstatements")
LABEL_DIR = os.path.join(REPO_ROOT, "shinto-label-generator", "quickstatements")
SITE_DIR = os.path.join(REPO_ROOT, "_site")
BATCH_DIR = os.path.join(SITE_DIR, "emergency-batch")
PAGES_URL = "https://emmaleonhart.github.io/shintowiki-scripts"

# daily_operations.txt is a CONCATENATION of other atomic files. Including it would run every
# line it holds a second time. QuickStatements adds are idempotent, but a removal is not
# idempotent in a useful way and the duplicate work is pure cost, so it is excluded and the
# sources are used directly.
CONCATENATION_FILES = {"daily_operations.txt"}

# ALL.txt is a PASTE, so it is bounded by what QuickStatements will actually take. Emma,
# 2026-09-06: *"all.txt is simply too large, largest batches I found pasted in were 10,000
# lines each. So we gotta have it be 10,000 randomly selected lines"*. The corpus is not
# lost -- the per-file chunks beside it still hold every line -- and because the draw is
# unseeded, regenerating deals a different hand, so repeated runs work through the corpus.
SAMPLE = 10000


def atomic_files():
    """The ATOMIC_FILES list, read from direct_daily_edits.py rather than re-listed here.

    Re-listing would be a second source of truth that silently goes stale — the registry
    already exists and is the thing the daily pipeline actually consumes.
    """
    src = io.open(os.path.join(QS_DIR, "direct_daily_edits.py"), encoding="utf-8").read()
    m = re.search(r"ATOMIC_FILES\s*=\s*\[(.*?)\n\]", src, re.S)
    if not m:
        raise SystemExit("could not find ATOMIC_FILES in direct_daily_edits.py")
    return re.findall(r'^\s*"([^"]+\.txt)"', m.group(1), re.M)


def read_lines(path):
    if not os.path.exists(path):
        return []
    out = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n").strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def orphan_label_lines(cache_path):
    """`Qxxx<TAB>L<lang><TAB>"label"` for every orphan description we have a label for.

    Reuses the cached orphan query if present so this does not re-hit WDQS; the join itself
    is entirely local against the generated label files.
    """
    if not os.path.exists(cache_path):
        return [], {}
    orphans = [tuple(r) for r in json.load(io.open(cache_path, encoding="utf-8"))]
    want_langs = {lang for _, lang, _ in orphans}

    labels = {}
    for path in sorted(glob.glob(os.path.join(LABEL_DIR, "*.txt"))):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            qid, field, value = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not qid.startswith("Q") or not field.startswith("L"):
                continue
            lang = field[1:]
            if lang in want_langs:
                labels[(qid, lang)] = value

    lines, per_lang = [], collections.Counter()
    for qid, lang, _desc in orphans:
        val = labels.get((qid, lang))
        if val:
            # PIPE, not TAB. The generator files under shinto-label-generator/ are
            # TAB-separated, but every atomic file in modern-quickstatements/ is
            # pipe-separated — including label_proposals_drip.txt, which is itself built
            # from those same generator files by select_label_proposals.py, converting on
            # the way in. Emitting TAB here would put two separator conventions in one
            # paste and misparse one half of it.
            lines.append("{}|L{}|{}".format(qid, lang, val))
            per_lang[lang] += 1
    return sorted(set(lines)), per_lang


def write_chunks(name, lines, chunk):
    """Split into chunk-sized .txt files; return [(filename, count)]."""
    os.makedirs(BATCH_DIR, exist_ok=True)
    written = []
    if not lines:
        return written
    total = (len(lines) + chunk - 1) // chunk
    for i in range(total):
        part = lines[i * chunk:(i + 1) * chunk]
        fn = "{}.{:03d}.txt".format(name, i + 1) if total > 1 else "{}.txt".format(name)
        io.open(os.path.join(BATCH_DIR, fn), "w", encoding="utf-8", newline="\n").write(
            "\n".join(part) + "\n")
        written.append((fn, len(part)))
    return written


def esc(s):
    return html.escape(s or "", quote=True)


def block_html(title, note, chunks, count):
    p = ['<h2>{}</h2>'.format(esc(title))]
    if note:
        p.append('<p class="note">{}</p>'.format(note))
    p.append('<p><b>{:,}</b> lines in <b>{}</b> file(s).</p>'.format(count, len(chunks)))
    p.append('<ul class="files">')
    for fn, n in chunks:
        p.append('<li><a href="emergency-batch/{0}">{0}</a> '
                 '<span class="muted">{1:,} lines</span></li>'.format(esc(fn), n))
    p.append('</ul>')
    return "\n".join(p)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(SITE_DIR, "emergency-batch.html"))
    ap.add_argument("--chunk", type=int, default=5000,
                    help="lines per .txt file (default 5000)")
    ap.add_argument("--sample", type=int, default=SAMPLE,
                    help="lines to draw into ALL.txt (default {}; 0 = the whole "
                         "corpus)".format(SAMPLE))
    ap.add_argument("--seed", type=int, default=None,
                    help="seed the sample for a reproducible ALL.txt")
    ap.add_argument("--cache", default=os.path.join(REPO_ROOT, "_orphan_cache.json"),
                    help="orphan query cache from generate_orphan_label_fixes.py")
    args = ap.parse_args(argv)

    # ---- block 1: the orphan-description labels, first by Emma's ordering ----
    orphan_lines, per_lang = orphan_label_lines(args.cache)
    print("block 1 — orphan labels: {:,} lines".format(len(orphan_lines)))

    # ---- block 2+: every other atomic file ----
    seen = set(orphan_lines)
    per_file = []
    for name in atomic_files():
        if name in CONCATENATION_FILES:
            continue
        lines = [l for l in read_lines(os.path.join(QS_DIR, name)) if l not in seen]
        if lines:
            per_file.append((name, lines))
    per_file.sort(key=lambda kv: -len(kv[1]))
    rest_total = sum(len(v) for _, v in per_file)
    print("blocks 2+ — {:,} lines across {} files".format(rest_total, len(per_file)))

    os.makedirs(BATCH_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(BATCH_DIR, "*.txt")):
        os.remove(old)

    parts = []
    parts.append("""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Emergency batch — every QuickStatement, in run order</title>
<style>
 :root{--fg:#222;--muted:#666;--line:#e0e0e0;--accent:#b23c17;}
 body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--fg);
      margin:0 auto;padding:1rem;max-width:900px;line-height:1.5;}
 h1{border-bottom:3px solid var(--accent);padding-bottom:.4rem;}
 h2{margin-top:2rem;border-bottom:1px solid var(--line);padding-bottom:.25rem;font-size:1.1rem;}
 .lede{background:#fdf3ef;border-left:4px solid var(--accent);padding:.8rem 1rem;border-radius:3px;}
 .note{background:#f7f7f7;border-left:3px solid #bbb;padding:.5rem .8rem;font-size:.92rem;}
 .muted{color:var(--muted);}
 ul.files{columns:2;font-size:.92rem;}
 ul.files li{break-inside:avoid;}
 .chip{display:inline-block;background:#eef4ee;border:1px solid #cfe0cf;border-radius:12px;
       padding:.1rem .55rem;font-size:.85rem;margin:.1rem;white-space:nowrap;}
 code{background:#f0f0f0;padding:.05em .3em;border-radius:3px;}
</style>
""")
    parts.append("<h1>Emergency batch</h1>")
    parts.append(
        '<p class="lede"><b>Every generated QuickStatement, in run order.</b> '
        'Block 1 is the orphan-description labels and must run first; everything else '
        'follows. Paste one file at a time into QuickStatements — each is independent, so a '
        'run that dies loses only its own chunk.</p>')

    parts.append('<p><b>{:,}</b> lines total: <b>{:,}</b> orphan labels, then <b>{:,}</b> '
                 'across {} files. Generated {}.</p>'.format(
                     len(orphan_lines) + rest_total, len(orphan_lines), rest_total,
                     len(per_file),
                     esc(datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%d %H:%M UTC"))))

    if orphan_lines:
        chunks = write_chunks("00-orphan-labels", orphan_lines, args.chunk)
        note = (
            'These items each carry a <b>description with no label</b> in that language. '
            'On Wikidata the uniqueness constraint is on the <b>(label, description) pair</b>, '
            'so a description with no label stakes the half that matters least and can get the '
            'eventual label edit rejected — <b>a description with no label costs a label</b>. '
            'The standing remedy deletes the description; here we <b>add the label and keep '
            'it</b>, which is possible for 97% of them. That is why this block is first. '
            'Per language: ' + " ".join(
                '<span class="chip">{} {:,}</span>'.format(esc(l), n)
                for l, n in per_lang.most_common()))
        parts.append(block_html("Block 1 — orphan-description labels", note,
                                chunks, len(orphan_lines)))

    parts.append('<h2>Blocks 2+ — everything else</h2>')
    parts.append('<p class="note">Ordered largest first. <code>daily_operations.txt</code> is '
                 'excluded on purpose: it is a concatenation of these same files, so including '
                 'it would run every line twice.</p>')
    for name, lines in per_file:
        stem = name[:-4]
        chunks = write_chunks(stem, lines, args.chunk)
        parts.append('<h2>{} <span class="muted">{:,} lines</span></h2>'.format(
            esc(name), len(lines)))
        parts.append('<ul class="files">')
        for fn, n in chunks:
            parts.append('<li><a href="emergency-batch/{0}">{0}</a> '
                         '<span class="muted">{1:,}</span></li>'.format(esc(fn), n))
        parts.append('</ul>')

    parts.append('<p class="muted" style="margin-top:2rem">Built by '
                 '<code>site/generate_emergency_batch.py</code>. '
                 '<a href="orphan-label-fixes.html">Orphan label detail</a> · '
                 '<a href="index.html">dashboards</a></p>')

    # ---- ALL.txt — a RUNNABLE SAMPLE, not the whole corpus ----
    # It was the whole corpus (131,567 lines) until 2026-09-06, and that made it unpastable:
    # Emma measured the largest batches actually accepted at ~10,000 lines each. So it is now
    # a random draw of SAMPLE lines. The chunks written above are untouched and still hold
    # every line for anyone going a piece at a time.
    #
    # SELECTED at random, not REORDERED: the draw picks which lines, then they are emitted in
    # the original run order, so orphan labels still lead whatever came up. Shuffling would
    # cost that for nothing.
    corpus = list(orphan_lines)
    for _name, lines in per_file:
        corpus.extend(lines)
    corpus_total = len(corpus)
    if args.sample and args.sample < corpus_total:
        rng = random.Random(args.seed)
        picked = sorted(rng.sample(range(corpus_total), args.sample))
        all_lines = [corpus[i] for i in picked]
        orphans_drawn = sum(1 for i in picked if i < len(orphan_lines))
        print("ALL.txt — sampled {:,} of {:,} lines ({:,} orphan labels)".format(
            len(all_lines), corpus_total, orphans_drawn))
    else:
        all_lines = corpus
        orphans_drawn = len(orphan_lines)
    io.open(os.path.join(BATCH_DIR, "ALL.txt"), "w", encoding="utf-8",
            newline="\n").write("\n".join(all_lines) + "\n")
    all_bytes = sum(len(l.encode("utf-8")) + 1 for l in all_lines)
    print("wrote ALL.txt — {:,} lines, {:,} bytes".format(len(all_lines), all_bytes))

    parts.insert(
        3,
        '<p class="lede"><b>One paste:</b> '
        '<a href="emergency-batch/ALL.txt"><b>ALL.txt</b></a> — <b>{:,}</b> lines drawn at '
        'random from the {:,} in the corpus ({:,} of them orphan labels), in run order. '
        '{:.2f} MB. Sized to what QuickStatements actually accepts in one paste; regenerate '
        'for a different draw. The per-file chunks below still hold every line.</p>'.format(
            len(all_lines), corpus_total, orphans_drawn, all_bytes / 1048576.0))

    doc = "\n".join(parts)
    io.open(args.out, "w", encoding="utf-8", newline="\n").write(doc)
    n_files = len(glob.glob(os.path.join(BATCH_DIR, "*.txt")))
    print("wrote {} and {} batch files ({:,} lines total)".format(
        args.out, n_files, len(orphan_lines) + rest_total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
