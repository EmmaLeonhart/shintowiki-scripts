#!/usr/bin/env python3
"""Render the Izumo 韓国伊太弖 report (docs/izumo_ou_karakuni_2026-07.md) as a
browsable GitHub Pages page.

Emma, Open questions 2026-07: *"write a relatively comprehensive report on what the fuck
might be happening with this thing."* The canonical report is the markdown doc; this
renders it to `_site/izumo-karakuni.html` so she can click it. Single source of truth —
the page is generated FROM the doc, so they cannot drift.

The renderer handles the constructs this report uses: ATX headings, pipe tables, fenced
code blocks, links, bold, and inline code. It is deliberately small (not a general
markdown engine) but is reused by any report page built the same way.

    python generate_izumo_karakuni_page.py
"""
import datetime
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DOC = os.path.join(REPO_ROOT, "docs", "izumo_ou_karakuni_2026-07.md")
OUT = os.path.join(REPO_ROOT, "_site", "izumo-karakuni.html")

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_CODE = re.compile(r"`([^`]+)`")


def inline(text):
    """Escape, then re-apply inline markdown (links, bold, code)."""
    # Protect code spans first so their contents aren't touched by bold/link.
    spans = []

    def stash(m):
        spans.append(html.escape(m.group(1)))
        return f"\x00{len(spans)-1}\x00"

    text = _CODE.sub(stash, text)
    text = html.escape(text)
    text = _LINK.sub(lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank">{m.group(1)}</a>', text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)
    return text


def render_table(lines):
    # lines: header | sep | rows...
    def cells(row):
        return [c.strip() for c in row.strip().strip("|").split("|")]
    header = cells(lines[0])
    aligns = cells(lines[1])
    body = [cells(r) for r in lines[2:]]
    out = ['<div class="table-wrap"><table>', "<thead><tr>"]
    for i, h in enumerate(header):
        a = "right" if i < len(aligns) and aligns[i].endswith(":") and not aligns[i].startswith(":") else "left"
        out.append(f'<th style="text-align:{a}">{inline(h)}</th>')
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(html.escape(lines[j]))
                j += 1
            out.append("<pre>" + "\n".join(buf) + "</pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            tbl = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                tbl.append(lines[j])
                j += 1
            out.append(render_table(tbl))
            i = j
            continue
        if re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append(f"<li>{inline(re.sub(r'^\\d+\\.\\s+', '', lines[i]))}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        if not line.strip():
            i += 1
            continue
        # Gather a soft-wrapped paragraph: consecutive plain lines until a blank
        # line or the start of a block construct. Join with spaces so bold/links
        # that span a line break render correctly.
        para = []
        while i < len(lines):
            cur = lines[i]
            if (not cur.strip() or cur.startswith("```")
                    or re.match(r"^#{1,6}\s+", cur)
                    or re.match(r"^\d+\.\s+", cur)
                    or cur.strip().startswith("|")):
                break
            para.append(cur.strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def render(md):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = md_to_html(md)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Izumo 意宇郡 韓国伊太弖 — one item, two register entries</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 900px;
    margin: 0 auto; padding: 1.5rem; color: #222; line-height: 1.65; }}
  h1 {{ color: #2e7d32; font-size: 1.5rem; }}
  h2 {{ color: #2e7d32; border-bottom: 2px solid #c8e6c9; padding-bottom: 0.3rem;
    margin-top: 2rem; font-size: 1.2rem; }}
  .nav a {{ color: #2e7d32; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.88rem; margin: 0.5rem 0; }}
  th, td {{ border: 1px solid #e0e0e0; padding: 0.4rem 0.6rem; vertical-align: top; }}
  th {{ background: #f1f8e9; }}
  code {{ font-family: Consolas, Monaco, monospace; background: #f5f5f5;
    padding: 0.05rem 0.3rem; border-radius: 3px; font-size: 0.9em; }}
  pre {{ background: #263238; color: #eceff1; padding: 0.85rem 1rem; border-radius: 6px;
    overflow-x: auto; font-size: 0.85rem; line-height: 1.5; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  a {{ color: #1565c0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .table-wrap {{ overflow-x: auto; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;
    color: #999; font-size: 0.8rem; }}
</style>
</head>
<body>
<p class="nav"><a href="index.html">&larr; shintowiki</a></p>
{body}
<footer>Generated {now} from <code>docs/izumo_ou_karakuni_2026-07.md</code> by
<a href="https://github.com/EmmaLeonhart/shintowiki-scripts">shintowiki-scripts</a>
(<code>generate_izumo_karakuni_page.py</code>). Report only; no Wikidata edits.</footer>
</body>
</html>"""


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    with io.open(DOC, encoding="utf-8") as fh:
        md = fh.read()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(render(md))
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
