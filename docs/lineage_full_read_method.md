# The full-read lineage pass — method

How the 444 shrines (345 `Category:別表神社` + 99 `Category:神宮125社`) got a
`P612` mother house, 2026-08-04. Written because the first version of this work
happened in ad-hoc session commands with nothing committed, so the method could
not be inspected.

**Not link analysis. Not keyword extraction.** Every article was read in full by
an Opus sub-agent. Everything else here is plumbing around that one step.

## The pipeline

| Step | Script | What it does |
|---|---|---|
| 1. Membership | `lineage/fetch_articles.py` | `list=categorymembers`, `cmnamespace=0`, **direct members only** — sub-categories are never descended (a MediaWiki category is not a taxonomy). |
| 2. Article text | same | Full plain text per article → `_agent_input/<set>/<title>.txt`, with an `ARTICLE TITLE` / `WIKIDATA` header. Not the lead, not the infobox. |
| 3. The read | Agent tool, 38 sub-agents | 11–12 files each, told to read every article in full and **not to grep**. Returns `<file> \| CLASS \| <source> \| <exact Japanese sentence>`. |
| 4. Recording | `lineage/wave.py` | `plan` lists what is still unclassified; `record` appends agent output to `agent_results.tsv`. Makes the pass restartable — a lost session costs one wave. |
| 5. Subject item | `lineage/build_subject_map.py` | Each shrine's **own** item → `subject_qids.json`. |
| 6. Target item | `lineage/build_p612_quickstatements.py` | Reduces the recorded source prose to title candidates, resolves via jawiki `pageprops`, emits QuickStatements. |
| 7. Coverage | `lineage/source_coverage.py` | Does the named source have an item at all. |
| 8. Report | `lineage/build_report.py` | `lineage/report.html` — the audit page. |

## The four classes

* **TRANSFER** — a specific named source the kami was brought from.
* **NETWORK** — tied to a named network, head shrine, or deity with no transfer stated.
* **AUTOCHTHONOUS** — the kami originated here. A positive finding, and the roots
  of the graph: 神託 at the site, a mountain/rock/island/river that *is* the kami,
  a deity enshrining its own spirit, a founding on a grave, 護国神社 招魂, a 総本社
  with no parent.
* **UNKNOWN** — no origin given anywhere in the article.

Every non-UNKNOWN verdict carries an exact Japanese sentence from the article.
The quote is the evidence; a verdict with no sentence behind it is not accepted.

**Why a read rather than a match:** the earlier pass judged from keyword-extracted
sentences and returned 129 of 344 UNCLEAR. Read in full, 438 of 444 give an
origin. The lineage is nearly always stated without the words 分霊 or 勧請.

## An article is not a data item

The original subject map asked ja.wikipedia for `pageprops.wikibase_item` **with
redirects followed**. A redirect then reports the QID of the article it lands on.

Of the 444 titles, **25 are redirects**, so 25 shrines were pointed at another
shrine's item and 19 items were claimed by two or three shrines at once. On
Wikipedia a redirect is navigation and the two titles are not separate topics; on
Wikidata the shrine behind the redirect is still its own subject.

`build_subject_map.py` resolves in this order, stopping at the first hit:

1. the jawiki page is a real **article** → its `wikibase_item`;
2. an item whose jawiki **sitelink** is exactly this title (legal on Wikidata for
   redirects — this is how 馬場都々古別神社 = `Q114593121` was found);
3. an item with exactly this **ja label** (`wbsearchentities`) — an item with no
   sitelink at all, which no sitelink lookup can see: 神服織機殿神社
   `Q135186223`, 八槻都々古別神社 `Q112152942`, 大間国生神社 `Q135098908`;
4. **none** — recorded as such. 21 shrines are in this state and get no
   statement, because emitting one would write onto whichever shrine the redirect
   lands on.

Section redirects are the clearest case that they are different subjects:
大河内神社 and 打懸神社 are `志等美神社#大河内神社` and `志等美神社#打懸神社`.

## Gates on what may be written

* Statements follow the single-statement model in
  [`wikidata_shrine_festival_model.md`](wikidata_shrine_festival_model.md):
  ONE `P612` with `P1013=Q195793` in the same statement, plus `S854` citing the
  jawiki article. Never a bare `P612`.
* The **subject** must have its own item (step 3 above).
* The **target** must resolve, must not be a disambiguation page (京都の諏訪神社
  resolves to the generic 諏訪神社 list — as a value that is worse than none), and
  must not equal the subject.
* One line per subject; the generator owns its subjects' lines and `--supersede`
  replaces any earlier line that disagrees, so an item can never receive two
  contradictory values.
* Targets are resolved through **ja.wikipedia**, not Wikidata. The only calls to
  Wikidata are the narrow "does an item exist" lookups in step 5.

## Emma's rulings, 2026-08-04

* **NETWORK emits the inferred network head**, including where the article names
  only a deity (函館八幡宮 "八幡神" → 宇佐神宮). `DEITY_HEAD` in the generator is
  the one place a value is not read off the article.
* **A non-shrine source still gets P612** — a palace, a place, a tomb
  (皇大神宮←笠縫邑, 白峯神宮←白峯陵, 石上神宮←宮中).
* **The Ise 125 are in.** The concern was that a 摂社/末社/別宮 is a constituent
  (`P361`) rather than a branch; the agents were told explicitly that
  subordination is not lineage, so `P612` carries origin and `P361` carries
  membership.
