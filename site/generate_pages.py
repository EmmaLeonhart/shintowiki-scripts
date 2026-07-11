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
import io
import json
import os
import re
import sys
import time

# Windows consoles default to cp1252 and choke on Japanese titles / arrows in
# progress output; force UTF-8 so the generator runs identically on dev + CI.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WIKI_URL = "https://shinto.miraheze.org"
WIKI_API = f"{WIKI_URL}/w/api.php"
USER_AGENT = ("ShintowikiPages/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot; "
              "immanuelleleonhart@gmail.com) shintowiki-scripts")
# This script lives in site/; the published output dir is _site/ at the repo
# root (the Pages deploy workflow copies/commits repo-root _site/).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR = os.path.join(REPO_ROOT, "_site")
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


def fetch_wikidata_edits_today(user="Immanuelle", cap=5000):
    """Count the editing account's Wikidata contributions so far today (UTC).

    Emma 2026-07-07: dashboard tile tracking how many daily edits happened.
    Live truth straight from Wikidata's usercontribs — covers both the daily
    drip and manual QuickStatements runs (same account). Capped to avoid
    unbounded pagination; shows 'cap+' when hit.
    """
    from datetime import datetime, timezone
    day_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    total, cont = 0, {}
    while total < cap:
        resp = http.get("https://www.wikidata.org/w/api.php", params={
            "action": "query", "list": "usercontribs", "ucuser": user,
            "ucend": day_start, "uclimit": "500", "ucprop": "timestamp",
            "format": "json", **cont,
        }, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        total += len(data.get("query", {}).get("usercontribs", []))
        if "continue" in data:
            cont = {"uccontinue": data["continue"]["uccontinue"]}
        else:
            return total
    return f"{cap}+"


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


def fetch_category_members(category, cmtype="page", cap=5000):
    """Return [{'title':...,'ns':...}] for members of a category, following
    continuation. `cmtype` is "page", "subcat", or "page|subcat|file". Bounded
    by `cap` so a runaway category can't produce unbounded HTML."""
    members = []
    params = {
        "action": "query", "list": "categorymembers",
        "cmtitle": f"Category:{category}", "cmtype": cmtype,
        "cmlimit": "500", "format": "json", "formatversion": "2",
    }
    while True:
        resp = http.get(WIKI_API, params=params,
                        headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        members.extend(data.get("query", {}).get("categorymembers", []))
        cont = data.get("continue")
        if not cont or len(members) >= cap:
            break
        params.update(cont)
        time.sleep(0.3)
    return members[:cap]


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
h1 { border-bottom: 3px solid #4caf50; padding-bottom: 0.5rem; margin-bottom: 1rem; }
h2 { color: #2e7d32; margin: 1.5rem 0 0.75rem; }
h3 { color: #333; margin: 1rem 0 0.5rem; }
a { color: #2e7d32; }
a:hover { color: #4caf50; }
p { margin: 0.5rem 0; }
nav {
  background: #f1f8e9; border: 1px solid #c5e1a5; border-radius: 8px;
  padding: 1rem 1.5rem; margin-bottom: 1.5rem;
  display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center;
}
nav a { text-decoration: none; font-weight: 500; }
nav .sep { color: #aed581; }
.timestamp { color: #666; font-size: 0.85rem; }
.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem; margin: 1rem 0;
}
.stat-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 1rem; text-align: center;
}
.stat-card .number { font-size: 1.8rem; font-weight: 700; color: #2e7d32; }
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
.feature-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem; margin: 1rem 0;
}
.feature-card {
  background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 8px;
  padding: 1.25rem; text-decoration: none; color: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.feature-card:hover { border-color: #4caf50; box-shadow: 0 2px 8px rgba(76,175,80,0.15); }
.feature-card h3 { color: #2e7d32; margin: 0 0 0.5rem; }
.feature-card p { margin: 0; font-size: 0.9rem; color: #555; }
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
  height: 100%; background: #4caf50; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 600;
  transition: width 0.3s ease; min-width: 2rem;
}
.pipeline-list { list-style: none; padding: 0; }
.pipeline-list li {
  padding: 0.4rem 0.75rem; border-left: 3px solid #e0e0e0; margin: 0.25rem 0;
}
.pipeline-list li.chunk-header {
  border-left-color: #4caf50; font-weight: 600; margin-top: 0.75rem;
}
footer {
  margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid #e0e0e0; color: #999; font-size: 0.8rem;
}
ul { margin: 0.5rem 0 0.5rem 1.5rem; }
li { margin: 0.25rem 0; }
.backlog-list {
  columns: 2; column-gap: 2rem; list-style: none; margin-left: 0;
  font-size: 0.9rem;
}
.backlog-list li { break-inside: avoid; padding: 0.1rem 0; }
@media (max-width: 640px) { .backlog-list { columns: 1; } }
"""


def nav_html(active="index"):
    links = [
        ("index", "index.html", "Overview"),
        ("backlog", "backlog.html", "Backlog"),
        ("self-audit", "self-audit.html", "Self-audit"),
        ("shikinaisha-orphans", "shikinaisha-orphans.html", "Shikinaisha ⧉"),
        ("kokugakuin-missing-ids", "kokugakuin-missing-ids.html", "Kokugakuin ids ⧉"),
        ("kokugakuin-multi-p13677", "kokugakuin-multi-p13677.html", "Kokugakuin multi-id ⧉"),
        ("shrine-ranking", "shrine-ranking.html", "Shrine Ranking"),
        ("p11250", "p11250.html", "P11250"),
        ("runs", "runs.html", "Run History"),
    ]
    parts = []
    for key, href, label in links:
        if key == active:
            parts.append(f'<strong>{label}</strong>')
        else:
            parts.append(f'<a href="{href}">{label}</a>')

    return f"""<nav>
  <a href="index.html" style="font-weight:700;font-size:1.1rem;color:#2e7d32;text-decoration:none;">shintowiki</a>
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

def _fmt(v):
    """Thousands-separated when numeric, else the fallback string ("?").

    Stat fetches degrade to "?" when Miraheze serves its anti-DDoS challenge; a
    bare {v:,} then raises "Cannot specify ',' with 's'" and aborts the build."""
    return f"{v:,}" if isinstance(v, int) else str(v)


def generate_index(stats, qs_count=0, backlog_counts=None, wd_edits_today="?"):
    count = qs_count
    total = stats.get("total_pages", "?")
    edits = stats.get("total_edits", "?")
    linked = stats.get("linked_to_wikidata", "?")
    without = stats.get("without_wikidata", "?")
    japanese = stats.get("japanese_category_names", "?")
    autocreated = stats.get("autocreated_categories", "?")
    untranslated = stats.get("untranslated_japanese", "?")
    double_qids = stats.get("double_category_qids", "?")
    dup_redirects = stats.get("duplicated_qid_redirects", "?")
    backlog_counts = backlog_counts or {}

    # Bottom-of-page backlog list: one line per todo.md item, linking to its
    # live detail page, with the live-detected count when available.
    backlog_rows = []
    for item in BACKLOG_ITEMS:
        c = backlog_counts.get(item["id"])
        unit = "scripts" if item["kind"] in ("repo_static", "repo_workflow") else "pages"
        count_txt = f" &mdash; <strong>{c}</strong> {unit}" if c not in (None, "?") else ""
        backlog_rows.append(
            f'    <li><a href="backlog-{item["slug"]}.html">{item["id"]}. '
            f'{item["title"]}</a>{count_txt}</li>'
        )
    backlog_items_html = "\n".join(backlog_rows)

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

<h2>Wikidata QuickStatements</h2>
<div class="feature-grid">
  <a class="feature-card" href="shrine-ranking.html">
    <h3>Shrine Ranking (P13723)</h3>
    <p>Add P459 determination method qualifiers to shrine ranking statements, P958 section qualifiers to Kokugakuin Museum entries, and migrate legacy properties.</p>
  </a>
  <a class="feature-card" href="p11250.html">
    <h3>Miraheze Article ID (P11250)</h3>
    <p>Link Wikidata items to their shintowiki articles. {count:,} pending statements.</p>
  </a>
  <a class="feature-card" href="runs.html">
    <h3>Run History</h3>
    <p>Track daily QuickStatements submission outcomes &mdash; submitted, partial, skipped, or failed.</p>
  </a>
</div>

<h2>Wiki statistics</h2>
<div class="stats-grid">
  <div class="stat-card"><div class="number">{_fmt(total)}</div><div class="label">Content pages</div></div>
  <div class="stat-card"><div class="number">{_fmt(edits)}</div><div class="label">Total edits</div></div>
  <div class="stat-card"><div class="number">{without}</div><div class="label">Pages still needing a Wikidata QID</div></div>
  <div class="stat-card"><div class="number">{count:,}</div><div class="label">Pending P11250 statements</div></div>
  <div class="stat-card"><div class="number">{wd_edits_today}</div><div class="label">Wikidata edits today (UTC)</div></div>
</div>

<h2>Wikidata integration progress</h2>
<div class="info-box">
  <p><strong>{without} pages are currently in
  <a href="{WIKI_URL}/wiki/Category:Pages_without_wikidata">Category:Pages without wikidata</a>.</strong>
  It is a single flat maintenance category fed by two mechanisms &mdash; not a list of
  permanently-unconnectable pages.</p>
  <ul>
    <li><strong>Most are a migration backlog.</strong> They still carry the old literal
    category tag and have no <code>{{{{wikidata link}}}}</code> template yet. Each cleanup
    cycle <code>remove_crud_categories</code> strips the legacy tag, the
    <code>wikidata_link</code> step adds the template, and <code>wikidata_lookup</code>
    resolves a QID from the page's interlanguage links wherever a matching Wikidata item
    exists. Many of these (major topics included) will connect once processed; the count
    drains over successive cycles.</li>
    <li><strong>A smaller set already carry the template but can't resolve.</strong> Their
    interlanguage links point at titles that don't exist on the target-language Wikipedia
    (or have no Wikidata item), so there is nothing to resolve to.</li>
  </ul>
  <p>The <code>wikidata_lookup</code> step reads each page's interlanguage links (e.g.
  <code>[[ja:&hellip;]]</code>), queries Wikidata's sitelinks API, and &mdash; when the
  links agree on one item &mdash; writes the QID into <code>{{{{wikidata link}}}}</code>. If
  the links disagree it flags the page for review rather than guessing.</p>
</div>

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
    <li><a href="{WIKI_URL}/wiki/Category:Pages_without_wikidata">Pages without wikidata</a> ({without})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Japanese_language_category_names">Japanese language category names</a> ({japanese})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Double_category_qids">Double category QIDs</a> ({double_qids})</li>
    <li><a href="{WIKI_URL}/wiki/Category:duplicated_qid_category_redirects">Duplicated QID category redirects</a> ({dup_redirects})</li>
    <li><a href="{WIKI_URL}/wiki/Category:Pages_with_untranslated_japanese_content">Pages with untranslated Japanese content</a> ({untranslated})</li>
  </ul>
</div>

<h2 id="backlog">Open backlog &mdash; unresolved issues</h2>
<div class="section">
  <p>The {len(BACKLOG_ITEMS)} outstanding work items tracked in
  <a href="{REPO_URL}/blob/main/todo.md">todo.md</a>. Each links to a live
  <a href="backlog.html">backlog</a> page that detects and lists the actual wiki pages
  (or repo scripts) involved. Counts are fetched live at build time.</p>
  <ul class="backlog-list">
{backlog_items_html}
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


# ─── Backlog dashboard ───────────────────────────────────────
# One page per todo.md backlog item. Each detail page DETECTS the pages (or
# repo scripts) belonging to the item and lists them live with links.
# Detection verified against shinto.miraheze.org 2026-05-30.

WIKI_LINK_TEMPLATE = f"{WIKI_URL}/wiki/{{}}"
REPO_BLOB = f"{REPO_URL}/blob/main/{{}}"


def _wiki_href(title):
    return WIKI_LINK_TEMPLATE.format(title.replace(" ", "_"))


# kind: "repo_static" | "repo_workflow" | "category" | "category_multi" | "search"
BACKLOG_ITEMS = [
    # id:1 "retire-terminating-scripts" DONE 2026-07-05 — all 4 confirmed inert
    # (unwired from wiki-cleanup.yml; normalize/remove_legacy ported to orchestrator
    # ops; reimport/migrate drained) and deleted. See DEVLOG 2026-07-05.
    # id:2 "audit-legacy-scripts" DONE 2026-07-05 — keep/fix/retire verdicts live in
    # docs/program_audit_2026-06.md §3/§8; the one open empirical gap (confirm the
    # July-gated terminating scripts were inert) was closed by id:1 (all 4 confirmed
    # + deleted). Re-verified no other actively-wired wiki-cleanup.yml script is a
    # silently-inert deleted-file reference. See DEVLOG 2026-07-05.
    {
        "id": 3, "slug": "ill-missing-wikidata",
        "title": "ILLs without WD= / \"Unknown\" targets",
        "blurb": "Interlanguage-link templates whose Wikidata target is unset or "
                 "literally \"Unknown\". The <code>unresolved_ill_qid</code> "
                 "orchestrator op tags these pages as it sweeps mainspace, so "
                 "the list grows over successive cleanup cycles. Fill via "
                 "fix_ill_destinations.py per context — don't blind-overwrite.",
        "kind": "category", "cmtype": "page",
        "category": "Pages with unresolved QID in ill template",
    },
    {
        "id": 4, "slug": "duplicate-qid-tail",
        "title": "Duplicate QID disambiguation pages (tail)",
        "blurb": "Q-named category pages sharing a QID across 2+ categories. The "
                 "~621 historical figure long drained; resolve_double_category_"
                 "qids.py auto-handles same-target cases. What remains is the "
                 "genuinely-different-target review tail.",
        "kind": "category", "category": "Double category qids", "cmtype": "page",
    },
    {
        "id": 5, "slug": "japanese-category-names",
        "title": "Japanese-language category names → English",
        "blurb": "THE real remaining backlog: category pages whose titles are in "
                 "Japanese script, to be translated/transliterated to canonical "
                 "English titles. A mix of dated maintenance cats and content "
                 "cats. See the scripting-plans doc.",
        "kind": "category", "category": "Japanese language category names",
        "cmtype": "subcat",
    },
    {
        "id": 6, "slug": "multiple-wikidata-links",
        "title": "Multiple {{wikidata link}} on one page",
        "blurb": "Pages carrying two or more {{wikidata link}} templates — "
                 "usually a Wikidata disambiguation issue needing per-case "
                 "review. The <code>multiple_wikidata_links</code> orchestrator "
                 "op tags these pages as it sweeps mainspace + categories, so "
                 "the list grows over successive cleanup cycles.",
        "kind": "category", "cmtype": "page",
        "category": "Pages with multiple wikidata links",
    },
    {
        "id": 7, "slug": "duplicated-content-need-translation",
        "title": "Duplicated content + remaining need-translation pages",
        "blurb": "Whole-body duplication to merge, plus pages still tagged for "
                 "translation. Mostly worked by the cloud-queue routine; manual "
                 "review only for the hard cases (canonical-title choice, "
                 "history merge, the large kokuzō articles).",
        "kind": "category_multi",
        "categories": [
            ("Pages with duplicated content", "page"),
            ("Need translation", "page"),
        ],
    },
    {
        "id": 8, "slug": "recreate-deleted-wikidata",
        "title": "Recreate deleted Wikidata items",
        "blurb": "ILL-target Wikidata items that another editor deleted. To be "
                 "recreated via the QuickStatements pipeline (respecting the "
                 "freeze to 2026-06-06) with a minimum claim set that won't be "
                 "re-deleted.",
        "kind": "category", "category": "Pages with deleted QID in ill template",
        "cmtype": "page",
    },
]


def _backlog_workflow_scripts(workflow_path):
    """Extract unique *.py script filenames referenced by a workflow file."""
    path = os.path.join(REPO_ROOT, workflow_path)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    names = sorted(set(re.findall(r"([A-Za-z0-9_]+\.py)", text)))
    # Resolve each to its repo path (best-effort: search shinto_miraheze/).
    resolved = []
    for name in names:
        rel = None
        for base in ("shinto_miraheze", "modern-quickstatements", "site"):
            cand = os.path.join(REPO_ROOT, base, name)
            if os.path.exists(cand):
                rel = f"{base}/{name}"
                break
        resolved.append((name, rel))
    return resolved


def _resolve_backlog_data(item):
    """Fetch the live list for one backlog item. Returns (entries, note) where
    entries is a list of (label, href) and note is an optional caveat string."""
    kind = item["kind"]
    if kind == "repo_static":
        return [(p.split("/")[-1], REPO_BLOB.format(p)) for p in item["scripts"]], None
    if kind == "repo_workflow":
        rows = _backlog_workflow_scripts(item["workflow"])
        entries = [(name, REPO_BLOB.format(rel) if rel else
                    f"{REPO_URL}/search?q={name}") for name, rel in rows]
        return entries, f"{len(entries)} scripts referenced by {item['workflow']}"
    if kind == "category":
        members = fetch_category_members(item["category"], item.get("cmtype", "page"))
        return [(m["title"], _wiki_href(m["title"])) for m in members], None
    if kind == "category_multi":
        entries, notes = [], []
        for cat, cmtype in item["categories"]:
            members = fetch_category_members(cat, cmtype)
            notes.append(f"{len(members)} in [[Category:{cat}]]")
            entries.append((cat, [(m["title"], _wiki_href(m["title"])) for m in members]))
        return entries, "; ".join(notes)
    return [], None


def _backlog_list_html(entries):
    if not entries:
        return '<p class="timestamp">No pages currently detected for this item.</p>'
    items = "\n".join(
        f'    <li><a href="{href}">{label}</a></li>' for label, href in entries
    )
    return f'<ul class="backlog-list">\n{items}\n</ul>'


def generate_backlog_index(resolved_counts):
    cards = []
    for item in BACKLOG_ITEMS:
        count = resolved_counts.get(item["id"], "?")
        if item["kind"] in ("repo_static", "repo_workflow"):
            status = f"<strong>{count}</strong> scripts"
        else:
            status = f"<strong>{count}</strong> detected"
        cards.append(f"""  <a class="feature-card" href="backlog-{item['slug']}.html">
    <h3>{item['id']}. {item['title']}</h3>
    <p>{item['blurb']}</p>
    <p class="timestamp">{status}</p>
  </a>""")
    body = f"""
<h1>Backlog</h1>
<div class="section">
  <p>Live status of the {len(BACKLOG_ITEMS)} open backlog items from
  <a href="{REPO_URL}/blob/main/todo.md">todo.md</a>. Each page below
  <strong>detects</strong> the wiki pages (or repo scripts) belonging to that
  item and lists them with links to the actual pages involved. Counts and lists
  are fetched live from <a href="{WIKI_URL}">shinto.miraheze.org</a> at build
  time.</p>
</div>
<div class="feature-grid">
{chr(10).join(cards)}
</div>
"""
    return page_html("Backlog — Shintowiki Scripts", body, active="backlog")


def generate_backlog_detail(item, entries, note):
    if item["kind"] == "category_multi":
        # entries is a list of (category, [(label, href), ...])
        total = sum(len(sub) for _, sub in entries)
        sections = []
        for cat, sub in entries:
            sections.append(
                f'<h2><a href="{_wiki_href("Category:" + cat)}">'
                f'Category:{cat}</a> &mdash; {len(sub)}</h2>\n'
                f'{_backlog_list_html(sub)}'
            )
        list_html = "\n".join(sections)
    else:
        total = len(entries)
        list_html = f"<h2>Detected pages &mdash; {total}</h2>\n{_backlog_list_html(entries)}"

    note_html = f'<div class="info-box">{note}</div>' if note else ""
    body = f"""
<h1>{item['id']}. {item['title']}</h1>
<p><a href="backlog.html">&larr; Back to backlog</a></p>
<div class="section">
  <p>{item['blurb']}</p>
</div>
{note_html}
{list_html}
"""
    return page_html(f"{item['title']} — Backlog", body, active="backlog"), total


# ─── Main ────────────────────────────────────────────────────

_WD_LINK_QID_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)", re.IGNORECASE)
_WD_ENTITY_API = "https://www.wikidata.org/w/api.php"


def _resolution_pages_with_qids():
    """Return [(title, qid)] for pages in the interlanguage-resolution category
    that the agent auto-filled with a QID — the set Emma needs to spot-check."""
    out = []
    params = {
        "action": "query", "generator": "categorymembers",
        "gcmtitle": "Category:Pages git synced to resolve interlanguage and interwiki links",
        "gcmtype": "page", "gcmlimit": "50",
        "prop": "revisions", "rvslots": "main", "rvprop": "content",
        "format": "json", "formatversion": "2",
    }
    cont = {}
    while True:
        p = dict(params); p.update(cont)
        r = http.get(WIKI_API, params=p, headers={"User-Agent": USER_AGENT}, timeout=60)
        r.raise_for_status()
        data = r.json()
        for pg in data.get("query", {}).get("pages", []):
            try:
                txt = pg["revisions"][0]["slots"]["main"]["content"]
            except (KeyError, IndexError):
                continue
            m = _WD_LINK_QID_RE.search(txt)
            if m:
                out.append((pg["title"], m.group(1)))
        if "continue" not in data:
            break
        cont = data["continue"]; time.sleep(0.3)
    return sorted(out)


def _wd_labels(qids):
    """Batch-fetch {qid: (label, description)} from Wikidata."""
    labels = {}
    qids = list(dict.fromkeys(qids))
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        try:
            r = http.get(_WD_ENTITY_API, params={
                "action": "wbgetentities", "ids": "|".join(batch),
                "props": "labels|descriptions", "languages": "en|ja",
                "format": "json",
            }, headers={"User-Agent": USER_AGENT}, timeout=30)
            r.raise_for_status()
            ents = r.json().get("entities", {})
            for q in batch:
                e = ents.get(q, {})
                lab = (e.get("labels", {}).get("en") or e.get("labels", {}).get("ja") or {}).get("value", "")
                desc = e.get("descriptions", {}).get("en", {}).get("value", "")
                labels[q] = (lab, desc)
        except Exception:
            for q in batch:
                labels.setdefault(q, ("", ""))
        time.sleep(0.3)
    return labels


def generate_self_audit():
    """Render self-audit.html — a reviewable view of the agent's autonomous
    actions Emma flagged she wanted to check (the auto-filled Wikidata QIDs and
    the agent-added CI workflow)."""
    try:
        pairs = _resolution_pages_with_qids()
    except Exception as exc:
        pairs = []
        err = str(exc)
    else:
        err = None
    labels = _wd_labels([q for _, q in pairs]) if pairs else {}

    rows = ""
    for title, qid in pairs:
        lab, desc = labels.get(qid, ("", ""))
        rows += (
            f'      <tr>'
            f'<td><a href="{_wiki_href(title)}">{title}</a></td>'
            f'<td><a href="https://www.wikidata.org/wiki/{qid}">{qid}</a></td>'
            f'<td>{lab}</td><td style="color:#666;font-size:0.85rem">{desc}</td>'
            f'<td><a href="https://www.wikidata.org/wiki/{qid}#sitelinks-wikipedia">check sitelinks</a></td>'
            f'</tr>\n'
        )
    table = (
        f'<table style="width:100%;font-size:0.9rem;border-collapse:collapse">\n'
        f'  <thead><tr style="text-align:left;border-bottom:2px solid #4caf50">'
        f'<th>Shintowiki page</th><th>Filled QID</th><th>Wikidata label</th>'
        f'<th>Description</th><th>Verify</th></tr></thead>\n  <tbody>\n{rows}  </tbody>\n</table>'
        if pairs else
        (f'<p class="timestamp">Detection failed at build time: {err}</p>' if err
         else '<p class="timestamp">No auto-filled QIDs currently detected (they may have drained as pages left the category).</p>')
    )

    body = f"""
<h1>Self-audit — agent actions to review</h1>
<div class="section">
  <p>During the 2026-06-07/08 interlanguage-resolution work the bot took two kinds
  of action on its own that it flagged for Emma to check. This page shows them
  concretely so you can see exactly what to look at.</p>
</div>

<h2>1. Auto-filled Wikidata QIDs ({len(pairs)})</h2>
<div class="info-box">
  <p><strong>What this is / what to check:</strong> for each page below, the bot
  decided <em>which Wikidata item that shintowiki page corresponds to</em> and
  wrote that QID into the page's <code>{{{{wikidata link}}}}</code> (a
  shinto.miraheze.org edit — <strong>not</strong> a Wikidata edit). It did this
  without per-page sign-off, on a high-confidence match (the item's label exactly
  matched the page's interlanguage target, or a verified search hit).</p>
  <p><strong>To verify one:</strong> click the page and the QID side by side —
  do they describe the <em>same</em> shrine/deity/place? The "Wikidata label" and
  "Description" columns are there so you can eyeball most without clicking. If any
  is wrong, tell the bot the page name and it'll clear that QID.</p>
</div>
{table}

<h2>2. Agent-added CI workflow — keep or delete?</h2>
<div class="section">
  <p><strong>What it is:</strong> <code>.github/workflows/ci.yml</code> — the bot
  added it autonomously. It runs the <code>pytest</code> suite (currently 52 tests,
  covering the git-synced sync logic incl. the clobber fix) on every push that
  touches Python, plus PRs. <strong>Upside:</strong> catches regressions (e.g. to
  the clobber fix) automatically. <strong>Cost:</strong> it adds GitHub Actions
  runs.</p>
  <p><strong>Your call:</strong> keep it (recommended — it's cheap and guards the
  sync logic), or tell the bot to delete it. Nothing depends on it.</p>
</div>
"""
    return page_html("Self-audit — Shintowiki Scripts", body, active="self-audit")


def main():
    os.makedirs(SITE_DIR, exist_ok=True)

    print("Fetching wiki statistics...", flush=True)
    stats = fetch_stats()
    print(f"  Total pages: {stats.get('total_pages', '?')}")
    print(f"  Linked to Wikidata: {stats.get('linked_to_wikidata', '?')}")

    print("Fetching QuickStatements/P11250...", flush=True)
    # Miraheze periodically serves a "Checking your connection" anti-DDoS
    # challenge (HTTP 403) to programmatic clients regardless of User-Agent
    # (build failures 2026-07-11). That must not abort the whole build — the
    # rest of the site (backlog, the Wikidata-driven data tables, static pages)
    # doesn't need this fetch. Degrade to an empty P11250 list, like fetch_stats
    # and the edits-today tile already do for the same reason.
    try:
        qs_text = fetch_wiki_page("QuickStatements/P11250")
    except Exception as exc:
        print(f"  WARNING: P11250 fetch failed ({exc}); continuing with 0 lines")
        qs_text = ""
    qs_lines = parse_qs_lines(qs_text)
    print(f"  Found {len(qs_lines)} QuickStatements lines")

    # Backlog dashboard: one detail page per todo.md item + an index. Built
    # BEFORE the index so the homepage's bottom-of-page backlog list can show
    # the live-detected counts.
    print("Generating backlog dashboard...", flush=True)
    backlog_counts = {}
    for item in BACKLOG_ITEMS:
        print(f"  [{item['id']}] {item['title']}", flush=True)
        try:
            entries, note = _resolve_backlog_data(item)
            detail_html, total = generate_backlog_detail(item, entries, note)
        except Exception as exc:
            print(f"      WARNING: detection failed: {exc}")
            detail_html, total = generate_backlog_detail(
                item, [], f"detection error at build time: {exc}")
        backlog_counts[item["id"]] = total
        with open(os.path.join(SITE_DIR, f"backlog-{item['slug']}.html"),
                  "w", encoding="utf-8") as f:
            f.write(detail_html)
        print(f"      {total} entries")

    print("Generating index.html...", flush=True)
    try:
        wd_edits_today = fetch_wikidata_edits_today()
    except Exception as exc:
        print(f"  edits-today tile unavailable: {exc}")
        wd_edits_today = "?"
    index_html = generate_index(stats, qs_count=len(qs_lines),
                                backlog_counts=backlog_counts,
                                wd_edits_today=wd_edits_today)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    print("Generating p11250.html and p11250.txt...", flush=True)
    p11250_html, p11250_raw = generate_p11250_page(qs_lines, stats)
    with open(os.path.join(SITE_DIR, "p11250.html"), "w", encoding="utf-8") as f:
        f.write(p11250_html)
    with open(os.path.join(SITE_DIR, "p11250.txt"), "w", encoding="utf-8") as f:
        f.write(p11250_raw + "\n")

    with open(os.path.join(SITE_DIR, "backlog.html"), "w", encoding="utf-8") as f:
        f.write(generate_backlog_index(backlog_counts))

    print("Generating self-audit.html...", flush=True)
    with open(os.path.join(SITE_DIR, "self-audit.html"), "w", encoding="utf-8") as f:
        f.write(generate_self_audit())

    # Write summary.json for external consumption
    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stats": stats,
        "p11250_pending": len(qs_lines),
        "backlog_counts": backlog_counts,
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
