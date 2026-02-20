# Wiki History & Development Timeline

This documents the history of [shinto.miraheze.org](https://shinto.miraheze.org) and how it reached its current state. Useful context for understanding why things are structured the way they are.

---

## Wikipedia origins (2020–2023)

Started using English Wikipedia around 2020. By 2023 there were serious problems: pages were being moved from mainspace to draft space, editing restrictions were imposed, and a heavy volume of translation work (setting up a translation workflow for Japanese Wikipedia content) was not being accepted. Around 4,000 drafts accumulated in draft space. A permanent block on English Wikipedia was issued in December 2023. After that, the drafts could not be kept from deletion. Two appeals have been filed and rejected; an appeal is ongoing.

There was a brief period of editing on Simple English Wikipedia while the block situation played out.

---

## Creating Shintowiki

Founded [shinto.miraheze.org](https://shinto.miraheze.org) as an independent wiki. Initial page set was imported from:
- English Wikipedia drafts
- Simple English Wikipedia drafts
- A few pages from Everybody Wiki

Started with a few hundred pages. Includes some non-Japanese content (Russian Orthodox icons, ancient Egyptian deities) from the old drafts.

---

## Inter-language link system

Initially, links pointed directly to English Wikipedia. Another editor objected to this approach. The wiki moved to the current system: **every single link in the entire wiki is an `{{ill}}` (interlanguage link) template**. No bare `[[wikilinks]]` to other wikis.

Early ILLs used Japanese Wikipedia as the primary language target. Current practice varies by page. Most ILLs now carry a `WD=Q…` Wikidata parameter.

The `{{ill}}` template accumulates complexity over time:
- Multiple language pairs as positional parameters
- Manual `lt=` display text overrides
- Many combinations of both, often with redundant or outdated values

This is a known maintenance problem. See [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) and [VISION.md](VISION.md) for the long-term plan to move export data to a separate namespace layer.

---

## Translated page template

Almost every mainspace page has a `{{translated page}}` template crediting the source Wikipedia edition. Early ChatGPT-era translation passes resulted in some ILL links pointing to wrong targets, particularly disambiguation pages. Some pages went to Japanese Wikipedia targets, some to English, some to both.

Translation pipeline over time:
1. ChatGPT (early, bulk work — lower quality, some mislinks)
2. Kodak
3. Claude (current)

---

## Wiki suspension and restoration

The wiki was suspended and then reinstated. It was restored using XML exports from Archive.org. The archived XML technically contained the full edit history, but was "weirdly partially archived." Only the most recent revision of each page was imported in the restoration (around January of the restoration year), not the full history.

A full history import is pending.

To preserve edit attribution, templates were introduced for history merges:
- `{{moved to}}` — marks the destination page of a history merge
- `{{moved from}}` — marks the source page

There were **two waves of page moves** due to separate issues, so some pages have both templates from different rounds.

---

## Category:Pages with duplicated content

[Category:Pages with duplicated content](https://shinto.miraheze.org/wiki/Category:Pages_with_duplicated_content) documents pages where the same content appears under more than one page title — pages that should be merged or disambiguated.

Previously called something like "merges" (renamed via Special:ReplaceText to the current, more descriptive name).

These are pages that need human review to decide which title is canonical and whether a history merge is appropriate.

---

## This repository

Originally created for Wikidata edits and Channelwiki work. Evolved into the main scripting repository for shintowiki operations.

**Initial project:** Getting all the Beppu shrines (and shrines of the Association of Shrines special designation) documented and linked to Wikidata.

**Translation workflow:** Established a pipeline for translating Japanese Wikipedia content and adding interwiki links, initially via ChatGPT.

---

## Shikinaisha project (June–July 2025)

Shikinaisha (式内社) are shrines listed in the Engishiki, an ancient register. Japanese Wikipedia has extensive, well-documented pages on these that had no English equivalents and were not on Wikidata.

**What was done:**
1. Ran scripts to import shrine ranks from Japanese Wikipedia categorization into Wikidata
2. Imported shikinaisha from Japanese Wikipedia lists (via the lists → Excel → scripts pipeline — messy but functional)
3. Got all shrines into Wikidata and onto the wiki

**Kokugakuin University database:** Found a second major source — the Kokugakuin University shrine database. This database had been used as the source for the Japanese Wikipedia tables. Importing from it caused a large number of duplicate shikinaisha entries (the database structures overlapped in non-obvious ways).

**WikiProject Shinto backlash:** The Wikidata WikiProject Shinto community had significant backlash to this mass import. Proposals to revert or ban were made but the data was never removed. The `wikiproject shinto current` and `wikiproject shinto archive` files in this repo are archives of those discussions.

---

## Shikinaisha pages on shintowiki

Generated programmatically from Wikidata using scripts in this repo. Earlier versions generated pages with excessive auto-generated content (essentially a dump of the Wikidata fields). Current policy: clean pages, one page per identified shikinaisha.

Categorization distinguishes:
- Identified shikinaisha (confirmed modern shrine correspondence)
- Candidate / disputed shikinaisha (no consensus on modern identification)

Most pages linked to Wikidata via the "Mizen article" property (`P18`), though not all — particularly more recent additions. Pages without Wikidata connections often have broken ILL links pointing to "Unknown" as target (flaw in early workflow).

Japanese Wikipedia content has been imported for most of them. Translation quality varies: early ChatGPT translations have the most issues.

---

## Category system state

**Key decision:** Translating category names does not work — slight paraphrases break categorization hierarchies since categories must match exactly. All category work is done via Wikidata linking instead of translation.

**Current state of categories:**
- All categories have been through the `wikidata link` script run
- Some categories still lack Wikidata items (Japan-only or internal maintenance categories)
- Some older scripts added interwikis without the Wikidata link → those pages need a re-run of the wikidata link script
- Category pages are heavily messy from many automated passes — Japanese text, accumulated redundant categories, navigation templates from Japanese Wikipedia (regex-based province/prefecture navigation)

**Intended end state:**
- Human-navigable English category names
- Clean category page wikitext (description + `{{wikidata link}}` + parent category links)
- All metadata and data in Pramana/Wikidata layer
- Navigation templates replaced with something appropriate for shintowiki's scope

---

## Talk pages

Essentially empty of real discussion. What exists is accumulated junk from Wikipedia's AFC process, old Wikipedia bots, and blank pages.

**Planned approach:**
- Import talk page content from Japanese Wikipedia and English Wikipedia for each article as a starting point
- Own discussion gets a dedicated section, with a comment noting the import date
- Navigation template on each talk page explaining all namespace layers

---

## See also

- [VISION.md](VISION.md) — architecture plan and future direction
- [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) — current page structure, templates, known issues
- [SCRIPTS.md](SCRIPTS.md) — catalog of all scripts with status
- [API.md](API.md) — how external services are accessed
