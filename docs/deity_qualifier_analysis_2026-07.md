# Enshrined-deity (P825) qualifiers — what's good, what we're overlooking

Emma, Open questions 2026-07: *"Analyze [Q137721156]… particularly the deities. I want to
do an analysis on the qualifiers that are used because I'm noticing a lot of qualifiers are
pretty good, or we might be overlooking them."* This is that analysis. Numbers are live from
`query-main.wikidata.org`, 2026-07-10. Report only — nothing edited.

## The item that prompted it — Q137721156 (日月神社, Isehara)

Four enshrined deities (`P825`), each modelled the same way:

| deity | source spelling (`P1932`) | reference |
|---|---|---|
| Amaterasu (Q455602) | 天照皇大御神 | 神奈川県神社誌, p.357, NDL 12261125/1/200 |
| Tsukuyomi (Q595520) | 月読命 | 〃 |
| Izanagi (Q813858) | 伊邪那岐命 | 〃 |
| Izanami (Q682306) | 伊邪那美命 | 〃 |

That is a **gold-standard provenance model**:

* `P825` deity + **`P1932` "object named as" (原文表記)** = the exact characters the source printed
  (`天照皇大御神`, not just "Amaterasu"). This preserves the source's spelling without forcing it
  into the item's label.
* a real **book reference** — `P248` = 神奈川県神社誌 (Kanagawa Prefecture Shrine Records,
  Q137052933) + `P304` page 357 + **`P9836` NDL Persistent ID** (a stable link into the National
  Diet Library's digitised scan, page image 200).

An academic could re-check every one of these four claims against a specific page of a named book.

## What the dataset actually looks like

**21,405 `P825` statements on 18,240 Japanese items** (`P17` = Japan). Coverage of the good
qualifiers:

| feature | statements | share |
|---|---:|---:|
| any reference | 10,640 | ~50% |
| `P1932` source spelling | **80** | 0.4% |
| `P3831` role (any) | 15 | 0.07% |
| `P3831` = principal deity (Q140493995, 主祭神) | 0 (not yet landed) | — |

Top `stated in` (`P248`) sources on the referenced deity statements:

| source | statements |
|---|---:|
| **神奈川県神社誌** (Q137052933) | **77** |
| information board (Q76419950) | 13 |
| Database of Cultural Properties in Fukuoka City (Q124047396) | 8 |
| 興除村史 (Q124355281) | 7 |
| …then a long tail of local histories / 村誌 / temple books | 1–5 each |
| Japanese Wikipedia (Q177837) | 4 |

## What this says

1. **Q137721156 is not typical — it is the good example.** Of the 80 `P1932`-qualified deity
   statements in the whole Japanese set, **77 come from this same 神奈川県神社誌 source**. Someone
   entered the Kanagawa shrine-record deities by hand with full book+page+NDL provenance, and
   Q137721156 is one of those. The 0.4% figure means the *practice* is excellent and the *coverage*
   is tiny.

2. **The auto-generated deity statements don't use `P248` book sourcing.** Only 4 P825 statements
   cite jawiki via `P248`; the project's `saijin_p825` / `saijin_deity_research` generators cite
   jawiki through `P4656` (Wikimedia import URL) instead, which is why jawiki barely appears in the
   `P248` table. So the two populations are: a small, book-sourced, `P1932`-tagged manual set, and a
   large, jawiki-import set. The book-sourced set is strictly richer.

## The overlooked qualifiers — ranked by opportunity

1. **`P3831` = Q140493995 (principal deity / 主祭神).** Essentially absent (0 landed). It is the
   single most valuable missing qualifier: it separates the 主祭神 from 配祀/合祀 auxiliaries.
   Q137721156 itself does not mark which of its four deities is principal — for 日月神社 (“sun-moon
   shrine”) that is almost certainly the Amaterasu + Tsukuyomi pair, but the data doesn't say so.
   **Good news:** `generate_saijin_deity_research.py` already emits exactly this qualifier where
   jawiki marks a 主祭神 (role item Q140493995, per `docs/wikidata_shrine_festival_model.md`); it
   just hasn't dripped yet. So the model is right; it needs the drip to run, not new code.

2. **`P1932` source spelling (原文表記).** Present on 0.4% but is the correct way to keep 天照皇大御神
   vs the label's 天照大神. The `saijin_deity_research` generator already adds it; the manual
   神奈川県神社誌 set already has it. Nothing to build — coverage grows as the drip lands.

3. **Book sourcing via `P248` + `P304` + `P9836` (NDL).** The bigger untapped opportunity. Every
   prefecture published a 神社誌 (府県社誌), many digitised in the NDL Digital Collections with
   stable persistent IDs. The 神奈川県神社誌 entries prove the model works and is far more
   authoritative than a jawiki import. Harvesting other prefectures' 神社誌 for deity + `P1932` +
   NDL-cited references would be a large, high-quality expansion — but it is a scraping/OCR project
   against page scans, not a mechanical import, so it is a proposal for Emma, not autonomous work.

## Recommendation

* **Nothing to fix in code for (1) and (2)** — the generators already emit `P3831`=主祭神 and
  `P1932`; let the drip carry them. Re-measure coverage once it has run for a while.
* **Q137721156 specifically:** its only gap is the 主祭神 marking. Adding `P3831`=Q140493995 to its
  principal deity/deities is a judgement call (which of the four?) — flagged for Emma, not
  auto-generated.
* **(3) prefectural 神社誌 harvest** is a real project worth scoping if the deity-provenance quality
  of the Kanagawa set is what Emma wants everywhere. Left as a proposal.
