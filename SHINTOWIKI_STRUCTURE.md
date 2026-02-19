# Shintowiki page structure

This documents the actual content structure of pages on [shinto.miraheze.org](https://shinto.miraheze.org) as they currently exist, including known issues. This is the ground truth for writing new scripts — not the old scripts, many of which represent failed or partial approaches.

---

## Table of contents

1. [The `{{ill}}` template](#1-the-ill-template)
2. [The `{{wikidata link}}` template](#2-the-wikidata-link-template)
3. [QID redirect pages](#3-qid-redirect-pages)
4. [Category pages](#4-category-pages)
5. [Template pages](#5-template-pages)
6. [Talk pages](#6-talk-pages)
7. [Tracking categories](#7-tracking-categories)
8. [Known issues to fix](#8-known-issues-to-fix)

---

## 1. The `{{ill}}` template

The ILL (interlanguage link) template is used throughout mainspace pages in place of plain wikilinks when the target page doesn't exist locally. It originated as a way to produce pages that could be cleanly exported to Wikipedia while preserving link structure. This is now the primary source of maintenance complexity on the wiki.

### Full parameter format

```
{{ill|destination|lang1|title1|lang2|title2|...|WD=Q123456|lt=display text}}
```

| Parameter | Role |
|-----------|------|
| `1=` / first positional | The local wiki destination (page to link to if it exists, or the display title) |
| `lang1`, `title1`, `lang2`, `title2`, … | Pairs: language code + article title on that Wikipedia |
| `WD=Q…` | Wikidata QID for this entity |
| `lt=` | Override display text (link text shown to reader) |

### Example

```wikitext
{{ill|Ise Grand Shrine|ja|伊勢神宮|en|Ise Grand Shrine|WD=Q131287|lt=Ise Shrine}}
```

Renders as a link that:
- Links locally if `Ise Grand Shrine` exists on shintowiki
- Falls back to the `ja:` or `en:` Wikipedia link if not
- The `WD=` parameter connects it to Wikidata item Q131287
- Displays as "Ise Shrine" (from `lt=`)

### State of ILLs currently

- **Most ILLs have `WD=`** — the `wikidata link` template on each page and the ILL template's `WD=` parameter are the two places QIDs appear
- **ILLs without `WD=`** indicate something went wrong during an earlier bot pass; these need fixing
- **The `1=` destination** should point to the correct local page title (resolved from the QID redirect if one exists, otherwise from enwiki sitelink, otherwise from English label)
- `fix_ill_destinations.py` handles keeping `1=` correct using this priority chain:
  1. `Q{QID}` mainspace redirect → resolves to local page title
  2. Wikidata enwiki sitelink
  3. Wikidata English label
  4. Last `lt=` value
  5. The QID itself as a fallback

### Why this is a maintenance problem

The ILL template was designed for export to Wikipedia. That goal is no longer realistic. The result is that every link on the wiki carries extra parameters (language pairs, QIDs) that make pages hard to read in the editor and hard to maintain by humans. The long-term vision (see [VISION.md](VISION.md)) is to move this data to a separate `Export:` namespace layer and simplify the mainspace to plain `[[links]]`.

---

## 2. The `{{wikidata link}}` template

Every page that has been connected to Wikidata has a `{{wikidata link|Q…}}` template. This is the canonical record of the page's Wikidata connection.

### Format

```wikitext
{{wikidata link|Q123456}}
```

### Where it appears

| Namespace | Placement |
|-----------|-----------|
| Mainspace | Bottom of the page, outside any section |
| Category | Bottom of the category page wikitext |
| Template | Inside `<noinclude>…</noinclude>` at the end of the template |

### Tracking category

Pages with `{{wikidata link}}` are automatically collected in:
```
Category:Pages linked to Wikidata
```
This category is the canonical index used by scripts to find wikidata-connected pages.

### Multiple QIDs

If multiple QIDs were found (e.g., from multiple interwikis pointing to different items), multiple templates appear:
```wikitext
{{wikidata link|Q111111}}
{{wikidata link|Q222222}}
```
This is an edge case that usually means there's a disambiguation problem on Wikidata.

### Missing wikidata

Pages with interwikis but no Wikidata connection get tagged:
```wikitext
[[Category:categories missing wikidata]]
```

---

## 3. QID redirect pages

For every page connected to Wikidata, a redirect exists in **mainspace** at the QID:

```
Q123456  →  #REDIRECT [[Page Name]]
```

### Rules

- QID redirects exist in **mainspace only** (namespace 0)
- They do **not** exist in Template space
- Category QID redirects point to the category: `#REDIRECT [[Category:Name]]`
- An earlier bot run incorrectly created some in **Category space** (`Category:Q123456`) — these are legacy artifacts and should eventually be cleaned up or converted

### Duplicate QIDs

When two pages share the same Wikidata QID, the redirect page is replaced with a disambiguation list:

```wikitext
# [[:Category:Foo]]
# [[:Category:Bar]]
[[Category:duplicated qid category redirects]]
```

Note the `[[:Category:…]]` colon prefix — this is a link to the category, not a category tag. Without the colon it would incorrectly categorize the page.

### How `fix_ill_destinations.py` uses QID redirects

```python
# Check if a Q-page redirect exists and resolve to its target
qid_page = site.pages[qid]   # e.g. site.pages["Q131287"]
if qid_page.exists:
    text = qid_page.text()
    m = re.match(r'#REDIRECT\s*\[\[([^\]]+)\]\]', text, re.IGNORECASE)
    if m:
        local_title = m.group(1)   # use this as the ill destination
```

---

## 4. Category pages

### Current state (messy)

Category pages have accumulated wikitext from many automated passes. A typical messy category page may contain:

- Stray `[[Category:Parent]]` links scattered throughout the text (not at the bottom)
- `{{wikidata link|Q…}}` templates sometimes in the middle of the page instead of the bottom
- `{{DEFAULTSORT:…}}` entries (mostly cleaned up Feb 2026)
- Interwiki links like `[[ja:Category:…]]` either inside or outside proper position
- Auto-generated content from old scripts that is no longer accurate
- Sometimes multiple conflicting categorizations from different bot passes

### Intended clean format

```wikitext
Short human-readable description of what this category contains.

{{wikidata link|Q123456}}

[[Category:Parent category]]
[[Category:Another parent]]
```

### Categories without Wikidata

Many categories lack Wikidata items because:
1. The category only exists on Japanese Wikipedia (no English Wikipedia equivalent, so no widely-known QID)
2. They are internal maintenance/organizational categories with no real-world entity correspondence

These get tagged:
```wikitext
[[Category:categories missing wikidata]]
```

### QID redirects for categories

The `Q{QID}` mainspace redirect for a category points to the full category title:
```
Q123456  →  #REDIRECT [[Category:Shrines in Kyoto]]
```

---

## 5. Template pages

### Structure

Templates should have their operational wikitext (the template code itself) followed by a `<noinclude>` section at the end:

```wikitext
[template code here — what gets transcluded]<noinclude>
{{wikidata link|Q123456}}
[[ja:Template:Japanese equivalent]]
[[Category:Templates by topic]]
</noinclude>
```

### Known issue: categories outside `<noinclude>`

Some earlier bot passes accidentally placed `[[Category:…]]` links and `{{wikidata link|…}}` templates **outside** the `<noinclude>` section. This causes every page that transclude the template to also get added to those categories, which is wrong.

The fix is straightforward: move any stray `[[Category:…]]` and `{{wikidata link|…}}` at the end of a template into a `<noinclude>` block.

Pattern to detect this:
```python
import re

# Detect template with categories/wikidata links outside noinclude
STRAY_CAT_RE = re.compile(
    r'(?<!</noinclude>)\n(\[\[Category:[^\]]+\]\]|{{wikidata link\|[^}]+}})\s*$',
    re.MULTILINE | re.IGNORECASE
)
```

---

## 6. Talk pages

### Current state

Talk pages on shintowiki are largely junk — accumulated random content from:
- Auto-generated comments from Wikipedia's AFC process (imported via page history)
- Bot-generated notices from various Wikipedia bots
- Old discussions that have no relevance to shintowiki
- Blank pages

### Intended structure (planned — not yet implemented)

Each talk page will have:

1. **A header template** (to be created) that explains the page's structure and all associated namespaces (Main, Data, Meta, Export)
2. **Auto-archiving** enabled via `{{archive box}}` or similar
3. **Imported content** from Japanese Wikipedia and English Wikipedia talk pages, as a starting point for discussion
4. **A dummy comment** to prevent immediate archiving of a fresh page

The existing content should be completely overwritten — none of it is worth preserving.

### Implementation approach

```python
# Overwrite talk page with clean starting structure
TALK_TEMPLATE = """\
{{talk page header}}

<!-- This talk page covers the main article and all associated namespace layers -->

== Initial import ==
<!-- Talk page content imported from Japanese Wikipedia and English Wikipedia -->

"""
```

---

## 7. Tracking categories

These categories are used by scripts to find pages to process:

| Category | Contains |
|----------|----------|
| `Pages linked to Wikidata` | All pages with `{{wikidata link\|Q…}}` |
| `categories missing wikidata` | Categories with interwikis but no Wikidata QID found |
| `Templates without wikidata` | Templates with no Wikidata connection |
| `duplicated qid category redirects` | `Q{QID}` pages pointing to 2+ categories |
| `Wikidata generated shikinaisha pages` | Pages generated from Wikidata shikinaisha data |

---

## 8. Known issues to fix

### High priority

| Issue | Scope | Fix |
|-------|-------|-----|
| Template categories outside `<noinclude>` | Template namespace | Move stray `[[Category:…]]` and `{{wikidata link}}` into `<noinclude>` |
| ILLs without `WD=` parameter | Mainspace | Run `fix_ill_destinations.py` or a new script to add missing `WD=` |
| Category:Q* pages in category namespace | ~77 pages | Either delete or move to mainspace |
| Duplicate QID disambiguation pages | 621 pages | Human review to assign correct QID ownership |
| Category pages with spaghetti wikitext | All categories | Rewrite script to clean up category content |

### Lower priority

| Issue | Notes |
|-------|-------|
| Talk pages with junk content | Full overwrite planned |
| Categories missing wikidata | Many are Japan-only or internal; low value to fix |
| Multiple `{{wikidata link}}` on one page | Usually indicates Wikidata disambiguation needed |
