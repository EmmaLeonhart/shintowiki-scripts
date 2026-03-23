#!/usr/bin/env python3
"""
generate_pages.py
==================
Generates a static GitHub Pages site for the shintowiki-scripts project.

Pages:
  - index.html    — project overview and automation status
  - p11250.html   — P11250 QuickStatements with copy-paste boxes
  - p11250.txt    — raw QuickStatements text file

Fetches live data from shinto.miraheze.org and Wikidata APIs.
"""

import datetime
import json
import os
import re
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WIKI_URL = "https://shinto.miraheze.org"
WIKI_API = f"{WIKI_URL}/w/api.php"
USER_AGENT = "ShintowikiPages/1.0 (User:EmmaBot; shinto.miraheze.org)"
SITE_DIR = os.path.join(os.path.dirname(__file__), "_site")
REPO_URL = "https://github.com/EmmaLeonhart/shintowiki-scripts"
PAGES_URL = "https://emmaleonhart.github.io/shintowiki-scripts"

QS_LINE_RE = re.compile(r'^(Q\d+)\|P11250\|"shinto:(.+)"$')

_retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
http = requests.Session()
http.mount("https://", HTTPAdapter(max_retries=_retry))
http.mount("http://", HTTPAdapter(max_retries=_retry))


# ─── Data fetching ───────────────────────────────────────────

def fetch_wiki_page(title):
    """Fetch raw wikitext of a page from shinto.miraheze.org."""
    resp = http.get(WIKI_API, params={
        "action": "parse", "page": title, "prop": "wikitext",
        "format": "json", "formatversion": "2",
    }, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("parse", {}).get("wikitext", "")


def fetch_category_count(category):
    """Get the number of pages in a category."""
    resp = http.get(WIKI_API, params={
        "action": "query", "prop": "categoryinfo",
        "titles": f"Category:{category}",
        "format": "json", "formatversion": "2",
    }, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", [])
    if pages:
        return pages[0].get("categoryinfo", {}).get("pages", 0)
    return 0


def fetch_stats():
    """Fetch key wiki statistics."""
    stats = {}
    categories = {
        "Pages linked to Wikidata": "linked_to_wikidata",
        "Pages without wikidata": "without_wikidata",
        "Japanese language category names": "japanese_category_names",
        "Categories autocreated by EmmaBot": "autocreated_categories",
        "Pages with untranslated japanese content": "untranslated_japanese",
        "Double category qids": "double_category_qids",
        "duplicated qid category redirects": "duplicated_qid_redirects",
    }
    for cat_name, key in categories.items():
        try:
            stats[key] = fetch_category_count(cat_name)
        except Exception:
            stats[key] = "?"
        time.sleep(0.2)

    # Total pages via siteinfo
    try:
        resp = http.get(WIKI_API, params={
            "action": "query", "meta": "siteinfo", "siprop": "statistics",
            "format": "json", "formatversion": "2",
        }, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        si = resp.json().get("query", {}).get("statistics", {})
        stats["total_pages"] = si.get("articles", "?")
        stats["total_edits"] = si.get("edits", "?")
    except Exception:
        stats["total_pages"] = "?"
        stats["total_edits"] = "?"

    return stats


def parse_qs_lines(wikitext):
    """Extract QuickStatements lines from wiki page text."""
    lines = []
    for line in wikitext.split("\n"):
        m = QS_LINE_RE.match(line.strip())
        if m:
            lines.append({"qid": m.group(1), "page": m.group(2), "raw": line.strip()})
    return lines


# ─── HTML generation ─────────────────────────────────────────

STYLE = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  max-width: 960px; margin: 2rem auto; padding: 0 1.5rem;
  color: #1a1a1a; line-height: 1.6;
}
h1 { border-bottom: 3px solid #c62828; padding-bottom: 0.5rem; margin-bottom: 1rem; }
h2 { color: #b71c1c; margin: 1.5rem 0 0.75rem; }
h3 { color: #333; margin: 1rem 0 0.5rem; }
a { color: #c62828; }
a:hover { color: #e53935; }
p { margin: 0.5rem 0; }
nav {
  background: #fafafa; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 1rem 1.5rem; margin-bottom: 1.5rem;
  display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center;
}
nav a { text-decoration: none; font-weight: 500; }
nav .sep { color: #ccc; }
.timestamp { color: #666; font-size: 0.85rem; }
.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem; margin: 1rem 0;
}
.stat-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 1rem; text-align: center;
}
.stat-card .number { font-size: 1.8rem; font-weight: 700; color: #c62828; }
.stat-card .label { font-size: 0.85rem; color: #666; }
.section {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 1.25rem; margin: 1rem 0;
}
.section h3 { margin-top: 0; }
.info-box {
  background: #fff3e0; border-left: 4px solid #ff9800;
  padding: 0.75rem 1rem; margin: 0.75rem 0; border-radius: 0 4px 4px 0;
}
.success-box {
  background: #e8f5e9; border-left: 4px solid #4caf50;
  padding: 0.75rem 1rem; margin: 0.75rem 0; border-radius: 0 4px 4px 0;
}
.qs-box {
  width: 100%; font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.8rem; border: 1px solid #ccc; border-radius: 4px;
  padding: 0.75rem; resize: vertical; background: #fafafa;
}
.progress-bar {
  background: #e0e0e0; border-radius: 12px; height: 24px;
  overflow: hidden; margin: 0.5rem 0;
}
.progress-fill {
  height: 100%; background: #c62828; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 600;
  transition: width 0.3s ease; min-width: 2rem;
}
.pipeline-list { list-style: none; padding: 0; }
.pipeline-list li {
  padding: 0.4rem 0.75rem; border-left: 3px solid #e0e0e0; margin: 0.25rem 0;
}
.pipeline-list li.chunk-header {
  border-left-color: #c62828; font-weight: 600; margin-top: 0.75rem;
}
footer {
  margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid #e0e0e0; color: #999; font-size: 0.8rem;
}
ul { margin: 0.5rem 0 0.5rem 1.5rem; }
li { margin: 0.25rem 0; }
"""


def nav_html(active="index"):
    links = [
        ("index", "index.html", "Overview"),
        ("p11250", "p11250.html", "P11250 QuickStatements"),
    ]
    parts = []
    for key, href, label in links:
        if key == active:
            parts.append(f'<strong>{label}</strong>')
        else:
            parts.append(f'<a href="{href}">{label}</a>')

    return f"""<nav>
  <span style="font-weight:700;">shintowiki</span>
  <span class="sep">|</span>
  {"  ".join(parts)}
  <span class="sep">|</span>
  <a href="{REPO_URL}">GitHub</a>
  <a href="{WIKI_URL}">Wiki</a>
</nav>"""


def page_html(title, body, active="index"):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
{nav_html(active)}
{body}
<footer>
  Generated {now} by <a href="{REPO_URL}">shintowiki-scripts</a> pipeline.
  Bot account: <a href="{WIKI_URL}/wiki/User:EmmaBot">User:EmmaBot</a>.
</footer>
</body>
</html>"""


# ─── Index page ──────────────────────────────────────────────

def generate_index(stats):
    total = stats.get("total_pages", "?")
    edits = stats.get("total_edits", "?")
    linked = stats.get("linked_to_wikidata", "?")
    without = stats.get("without_wikidata", "?")
    japanese = stats.get("japanese_category_names", "?")
    autocreated = stats.get("autocreated_categories", "?")
    untranslated = stats.get("untranslated_japanese", "?")
    double_qids = stats.get("double_category_qids", "?")
    dup_redirects = stats.get("duplicated_qid_redirects", "?")

    # Wikidata progress bar
    if isinstance(linked, int) and isinstance(without, int) and (linked + without) > 0:
        pct = linked / (linked + without) * 100
        bar = f"""<div class="progress-bar">
  <div class="progress-fill" style="width:{pct:.1f}%">{linked:,} linked ({pct:.0f}%)</div>
</div>
<p class="timestamp">{without:,} pages still need Wikidata links</p>"""
    else:
        bar = ""

    body = f"""
<h1>Shintowiki Scripts</h1>

<div class="section">
  <h3>About the project</h3>
  <p><a href="{WIKI_URL}">shinto.miraheze.org</a> is an independent wiki documenting Shinto shrines,
  Japanese religious history, and related topics. It was founded after content created on English Wikipedia
  could no longer be maintained there, preserving thousands of articles about shrines, deities, and
  religious practices.</p>
  <p>The wiki uses <strong>interlanguage link templates</strong> (<code>{{{{ill}}}}</code>) for every
  cross-wiki reference, and <strong>Wikidata integration</strong> (<code>{{{{wikidata link}}}}</code>)
  to connect pages to the linked data ecosystem. Every page is linked to its Wikidata item where one exists.</p>
</div>

<h2>Wiki statistics</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="number">{total:,}</div><div class="label">Content pages</div></div>
  <div class="stat-card"><div class="number">{edits:,}</div><div class="label">Total edits</div></div>
  <div class="stat-card"><div class="number">{linked:,}</div><div class="label">Linked to Wikidata</div></div>
  <div class="stat-card"><div class="number">{without:,}</div><div class="label">Missing Wikidata</div></div>
</div>

<h2>Wikidata integration progress</h2>
{bar}

<h2>Automated maintenance</h2>
<div class="section">
  <p>The <a href="{REPO_URL}">shintowiki-scripts</a> repository runs a daily <strong>GitHub Actions</strong>
  pipeline that performs automated maintenance on the wiki. All edits are made by
  <a href="{WIKI_URL}/wiki/User:EmmaBot">User:EmmaBot</a> with transparent edit summaries linking back to
  the workflow run.</p>

  <h3>Pipeline stages</h3>
  <ul class="pipeline-list">
    <li class="chunk-header">Import &amp; Categorization</li>
    <li>Reimport pages from English Wikipedia</li>
    <li>Create wanted categories as stubs</li>
    <li>Triage autocreated categories (enwiki / jawiki / secondary)</li>
    <li>Create shrine ranking article pages</li>
    <li class="chunk-header">Structural Fixes</li>
    <li>Delete unused templates</li>
    <li>Fix double redirects</li>
    <li>Resolve duplicate QID disambiguation pages</li>
    <li class="chunk-header">Wikidata</li>
    <li>Generate P11250 QuickStatements (<a href="p11250.html">view</a>)</li>
    <li>Clean completed QuickStatements</li>
    <li>Tag pages without Wikidata links</li>
    <li>Clean wikidata category redirects</li>
    <li class="chunk-header">Final</li>
    <li>Fix template noinclude blocks</li>
    <li>Categorize uncategorized pages</li>
    <li>Tag untranslated Japanese content</li>
    <li class="chunk-header">Cleanup</li>
    <li>Delete unused categories &amp; broken redirects</li>
    <li>Migrate &amp; clean up talk pages</li>
    <li>Remove crud category tags</li>
  </ul>
</div>

<h2>Ongoing work</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="number">{japanese}</div><div class="label">Japanese category names<br><small>(need translation)</small></div></div>
  <div class="stat-card"><div class="number">{autocreated}</div><div class="label">Autocreated categories<br><small>(need enrichment)</small></div></div>
  <div class="stat-card"><div class="number">{untranslated}</div><div class="label">Pages with untranslated<br>Japanese content</div></div>
  <div class="stat-card"><div class="number">{double_qids}</div><div class="label">Double category QIDs<br><small>(being resolved)</small></div></div>
</div>

<div class="section">
  <h3>Key categories</h3>
  <ul>
    <li><a href="{WIKI_URL}/wiki/Category:Pages_linked_to_Wikidata">Pages linked to Wikidata</a> ({linked})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Pages_without_wikidata">Pages without wikidata</a> ({without})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Japanese_language_category_names">Japanese language category names</a> ({japanese})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Double_category_qids">Double category QIDs</a> ({double_qids})</li>
    <li><a href="{WIKI_URL}/wiki/Category:duplicated_qid_category_redirects">Duplicated QID category redirects</a> ({dup_redirects})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Pages_with_untranslated_japanese_content">Pages with untranslated Japanese content</a> ({untranslated})</li>
  </ul>
</div>
"""
    return page_html("Shintowiki Scripts", body, active="index")


# ─── P11250 page ─────────────────────────────────────────────

def generate_p11250_page(qs_lines, stats):
    count = len(qs_lines)
    linked = stats.get("linked_to_wikidata", 0)

    if isinstance(linked, int) and linked > 0:
        pct = count / linked * 100
        pct_text = f" ({pct:.1f}% of linked pages still need P11250)"
    else:
        pct_text = ""

    # Build the raw text for copy-paste
    raw_text = "\n".join(l["raw"] for l in qs_lines)

    # Show first 200 lines in the textarea
    preview_lines = qs_lines[:200]
    preview_text = "\n".join(l["raw"] for l in preview_lines)
    more_text = f"\n... and {count - 200} more lines (download full file below)" if count > 200 else ""

    body = f"""
<h1>P11250 QuickStatements</h1>

<div class="section">
  <h3>What is this?</h3>
  <p><a href="https://www.wikidata.org/wiki/Property:P11250">P11250</a> (Miraheze article ID) links
  Wikidata items to their corresponding articles on <a href="{WIKI_URL}">shinto.miraheze.org</a>.
  Each line below adds a <code>P11250</code> claim to a Wikidata item, connecting it to the shintowiki article.</p>
  <p>These statements are generated automatically by
  <a href="{REPO_URL}">EmmaBot</a> and can be pasted directly into
  <a href="https://quickstatements.toolforge.org/">QuickStatements</a>.</p>
</div>

<div class="info-box">
  Click the text box to select all contents, then paste into
  <a href="https://quickstatements.toolforge.org/#/batch">QuickStatements batch mode</a>.
  Each box shows up to 200 lines. Download the full file for all {count:,} lines.
</div>

<h2>Status</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="number">{count:,}</div><div class="label">Pending QuickStatements{pct_text}</div></div>
</div>

<h2>QuickStatements</h2>
<p><strong>{count:,} lines</strong> &mdash;
  <a href="p11250.txt" download>Download full p11250.txt</a></p>

<textarea class="qs-box" rows="20" readonly onclick="this.select()">{preview_text}{more_text}</textarea>

<h2>How it works</h2>
<div class="section">
  <ol>
    <li><code>generate_p11250_quickstatements.py</code> walks all pages in
    <a href="{WIKI_URL}/wiki/Category:Pages_linked_to_Wikidata">Category:Pages linked to Wikidata</a></li>
    <li>For each page with <code>{{{{wikidata link|Q...}}}}</code>, it checks Wikidata for an existing P11250 claim</li>
    <li>If missing, a QuickStatements line is added: <code>Q...|P11250|"shinto:Page Name"</code></li>
    <li><code>clean_p11250_quickstatements.py</code> removes lines for items that now have the correct P11250</li>
    <li>Both scripts run daily in the GitHub Actions pipeline</li>
  </ol>
</div>

<h2>Sample entries</h2>
<div class="section">
  <table style="width:100%;font-size:0.85rem;">
    <thead><tr><th style="text-align:left">Wikidata</th><th style="text-align:left">Shintowiki page</th></tr></thead>
    <tbody>
"""
    for entry in qs_lines[:10]:
        body += f'      <tr><td><a href="https://www.wikidata.org/wiki/{entry["qid"]}">{entry["qid"]}</a></td>'
        body += f'<td><a href="{WIKI_URL}/wiki/{entry["page"].replace(" ", "_")}">{entry["page"]}</a></td></tr>\n'

    body += f"""    </tbody>
  </table>
  {"<p class='timestamp'>Showing first 10 of " + str(count) + " entries</p>" if count > 10 else ""}
</div>
"""
    return page_html("P11250 QuickStatements — Shintowiki", body, active="p11250"), raw_text


# ─── Main ────────────────────────────────────────────────────

def main():
    os.makedirs(SITE_DIR, exist_ok=True)

    print("Fetching wiki statistics...", flush=True)
    stats = fetch_stats()
    print(f"  Total pages: {stats.get('total_pages', '?')}")
    print(f"  Linked to Wikidata: {stats.get('linked_to_wikidata', '?')}")

    print("Fetching QuickStatements/P11250...", flush=True)
    qs_text = fetch_wiki_page("QuickStatements/P11250")
    qs_lines = parse_qs_lines(qs_text)
    print(f"  Found {len(qs_lines)} QuickStatements lines")

    print("Generating index.html...", flush=True)
    index_html = generate_index(stats)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    print("Generating p11250.html and p11250.txt...", flush=True)
    p11250_html, p11250_raw = generate_p11250_page(qs_lines, stats)
    with open(os.path.join(SITE_DIR, "p11250.html"), "w", encoding="utf-8") as f:
        f.write(p11250_html)
    with open(os.path.join(SITE_DIR, "p11250.txt"), "w", encoding="utf-8") as f:
        f.write(p11250_raw + "\n")

    # Write summary.json for external consumption
    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stats": stats,
        "p11250_pending": len(qs_lines),
    }
    with open(os.path.join(SITE_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nSite generated in {SITE_DIR}/")
    print(f"  index.html    — project overview")
    print(f"  p11250.html   — QuickStatements page")
    print(f"  p11250.txt    — raw QuickStatements ({len(qs_lines)} lines)")
    print(f"  summary.json  — machine-readable stats")


if __name__ == "__main__":
    main()
