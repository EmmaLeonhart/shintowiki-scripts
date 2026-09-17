# Kokugakuin ranking sequence anomalies — verdicts (2026-07-11)

Method + scope: `kokugakuin_anomaly_review_scope_2026-07.md`. The 6 ranking-sequence anomalies
in `p958_manual_review.txt` (candidate P1352 ranks that don't start contiguously at 1) were each
investigated per Emma's tooled method: read the Kokugakuin entry page's 現社名など（１..N）
ordering — the ranking ground truth — and diff it against the Wikidata candidate ranks. Report
only; no Wikidata edits.

The pages turned out to be **static HTML** (no JS/browser needed): a plain fetch of
`https://jmapps.ne.jp/kokugakuin/det.html?data_id=<P13677>` contains the full 現社名など list.

## The single structural explanation — all 6 are INTENTIONAL

Every one has candidate ranks starting at **2** (`[2]` or `[2,3]`) instead of `[1]`. In every
case the reason is the same:

> **現社名など（１） is the shrine's CURRENT SITE (現社地) — i.e. the parent/entry item itself.**
> Wikidata does not store a self-referential `has part` candidate for the parent, so the *other*
> 論社 (former sites 旧社地, or a distinct identified shrine) correctly begin at rank 2. The
> renumber algorithm's "expected [1]" is a false alarm — it doesn't know rank 1 is the parent.

| Parent | Entry | Kokugakuin 現社名など ordering | WD candidates (rank) | Verdict |
|---|---|---|---|---|
| [Q11442961](https://www.wikidata.org/wiki/Q11442961) 天王宮大歳神社 | 181512 | (1) 天王宮〔=self〕 (2) 蒲神明宮 | 蒲神明宮 (2) | INTENTIONAL |
| [Q11659237](https://www.wikidata.org/wiki/Q11659237) 雄神神社 | 182391 | (1) 雄神神社〔=self〕 (2) 元雄神神社 | 元雄神神社 (2) | INTENTIONAL |
| [Q135039294](https://www.wikidata.org/wiki/Q135039294) 畠田神社 | 181183 | (1) 現社地〔=self〕 (2)(3) 旧社地 | 旧社地 (2), 旧社地 (3) | INTENTIONAL |
| [Q135040569](https://www.wikidata.org/wiki/Q135040569) 三重神社 | 182575 | (1) 現社地〔=self〕 (2) 旧社地 (3) 大屋神社 | 旧社地 (2), 大屋神社 (3) | INTENTIONAL |
| [Q135041216](https://www.wikidata.org/wiki/Q135041216) 百射山神社 | 183085 | (1) 〔=self〕 (2) 元百射山神社 | 元百射山神社 (2) | INTENTIONAL |
| [Q135041251](https://www.wikidata.org/wiki/Q135041251) 和理比賣神社 | 183117 | (1) 〔=self〕 (2)(3) 旧社地 | 旧社地 (2), 旧社地 (3) | INTENTIONAL |

None needs a renumber. The ranks on Wikidata already match the source once you account for the
parent occupying slot 1.

## Action taken

* These 6 parent QIDs are added to `SEQUENCE_ANOMALIES_CLEARED` in
  `generate_p958_qualifiers.py`, so the catcher stops re-flagging them each CI run. It is an
  explicit, per-item, source-verified allowlist — **not** a loosened heuristic (Emma's standing
  prohibition on name-matching heuristics here is respected; nothing is auto-cleared by rule).
* No QuickStatements emitted — INTENTIONAL verdicts produce no edits.

This closes the ranking-sequence half of the anomaly review. The multiple-P13677 half (~66 hard
residue) remains per-item investigation, unchanged.
