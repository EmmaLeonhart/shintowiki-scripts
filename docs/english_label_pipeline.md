# English-label pipeline — current state vs target (A0 audit)

This documents the existing English-label generation for Shinto shrines on
Wikidata and the target 4-stage priority pipeline from the queue.md agenda.
It is the spec the Stage A queue items (A1–A5) implement.

**Hard constraint (unchanged):** every label reaches Wikidata only through the
daily QuickStatements drip (`modern-quickstatements/submit_daily_batch.py`),
no edit summaries, no bespoke direct-API editor. All stages below emit
`Qxxx|Len|"…"` (label) and `Qxxx|Aen|"…"` (alias) lines into atomic `.txt`
files in the `ATOMIC_FILES` list.

## What exists today

There are **two** independent English-label sources feeding the submitter:

### Source 1 — wiki-title lookup ("Stage 0", keep as-is)
- `shinto_miraheze/generate_en_labels_quickstatements.py` renders
  `[[QuickStatements/En labels]]` from the orchestrators' shared duplicate-QID
  dict: for every (shintowiki page title, qid) whose Wikidata item lacks an en
  label, it emits `Qxxx|Len|"<title>"`. The article title **is** the label.
  Mainspace + `Category:` only.
- `modern-quickstatements/fetch_en_labels_from_wiki.py` pulls that wiki page,
  drops items that now have an en label or are redirects, writes
  `en_labels.txt`.
- Scope: only shrines that already have a shintowiki article. Pure lookup, no
  translation. This is the highest-confidence source and stays as a de-facto
  Stage 0 ahead of everything below.

### Source 2 — SPARQL worklist → LLM (the path that needs splitting)
- `modern-quickstatements/generate_shrines_missing_en_label.py` runs a SPARQL
  query for **every** `P31=Q845945` shrine with a `ja` label but no `en` label,
  capturing the kana (`P1814`) when present, and writes
  `shrines_missing_en_label.json` (`generate-shrines-missing-en-label.yml`,
  daily ~05:17 UTC).
- `modern-quickstatements/select_shrines_to_translate.py` picks 5/day at random
  (presence-dedup against `en_labels_sonnet.txt`); the remote claude.ai Sonnet
  routine translates them from ja label + kana and appends to
  `en_labels_sonnet.txt`.

**The core defect:** Source 2 sends *all* shrines missing en — **including those
that have kana** — to the LLM. Per the agenda, kana shrines must be resolved
*deterministically* (Stage 1), and the LLM (Stage 4) should only ever see the
residual that Stages 1–3 could not handle. Today Stages 1, 2 and 3 do not exist,
so the LLM is doing work that deterministic rules should do, and the 5/day LLM
throttle is spent on shrines that need no LLM at all.

## Target 4-stage pipeline (priority order; each stage only sees what earlier stages left)

| Stage | Condition (after Stage 0 lookup) | Method | Status |
|---|---|---|---|
| **0** | Shrine has a shintowiki article | Title = label (lookup) | EXISTS (Source 1), keep |
| **1** | `ja` + kana, no `en` | Deterministic kana→English rules (jinja→Shrine, taisha→Grand Shrine [alias], daijinja→Daijinja, -sha→-sha Shrine, -gu→-gu Shrine, daijingu→Daijingu). NOT pykakasi/Indonesian. | **DONE — `kana_english.py` + `generate_kana_en_labels.py`** |
| **2** | `ja`, no kana, no `en` | Reuse en label from another shrine with identical `ja` label (dominant wins + less-common alias; tie→random; alias only when exactly one other) | **DONE — `reuse_labels.py` + `generate_identical_name_en_labels.py`** |
| **3** | no `en`/kana/identical-name match, has a non-CJK-script label | Transliterate, drop 2nd word, replace with "Shrine" | **PARKED — only 2 such shrines exist & all irregular; escalated (see Open questions)** |
| **4** | everything still without `en` | LLM remote Sonnet routine (5/day) | EXISTS (Source 2), but must be **narrowed to the residual — A4/A5** |

## Stage 1 as built (A1, 2026-06-21)
- `modern-quickstatements/kana_english.py` — `label_for(ja, kana)` picks the
  shrine-type suffix from the **kanji** label (unambiguous) and romanizes the
  stem from kana to macron-free Hepburn. Pure 神宮 deferred (see module header).
- `modern-quickstatements/generate_kana_en_labels.py` — consumes the kana-bearing
  subset of `shrines_missing_en_label.json`, emits `Len`/`Aen` to
  `kana_en_labels.txt` (now in `submit_daily_batch.ATOMIC_FILES`).
- Regenerated daily by `generate-shrines-missing-en-label.yml` right after the
  worklist refresh. On the 2026-06-21 worklist: **424 / 442** kana shrines
  handled deterministically; 18 deferred (2 pure-神宮, 8 non-shrine suffixes,
  ~8 irregular/unromanizable readings). Tests: `tests/test_kana_english.py`,
  `tests/test_generate_kana_en_labels.py`.

## Stage 2 as built (A2, 2026-06-21)
- `modern-quickstatements/reuse_labels.py` — `choose_label(candidates, qid)`:
  pure rule logic. Dominant reading wins; alias only when exactly one other
  distinct reading; ties broken by a per-QID-deterministic random pick (stable
  across daily runs, no label churn).
- `modern-quickstatements/generate_identical_name_en_labels.py` — for the
  no-kana subset of the worklist, POSTs batched `VALUES ?ja {…}` queries (a
  self-join times out; GET 431s on large bodies — POST ~1s/150 labels) to fetch
  same-ja-name shrines' en labels, normalizes out trailing parenthetical
  disambiguators ("Maruyama Shrine (Oita)"→"Maruyama Shrine"), and emits
  `Len`/`Aen` to `identical_name_en_labels.txt` (in `ATOMIC_FILES`).
- Live run on the 2026-06-21 worklist: **1881/4618** no-kana targets got a
  reused label (+440 aliases), 0 malformed, **0 QID overlap with Stage 1**.
  Tests: `tests/test_reuse_labels.py`, `tests/test_generate_identical_name_en_labels.py`.
- Stages 1+2 together now deterministically handle **2305 / 5060** en-less
  shrines, all offloaded from the 5/day LLM.

## Implementation notes for A3–A5
- **A4/A5** change `select_shrines_to_translate.py` (or the worklist generator)
  so the LLM only draws shrines NOT handled by Stages 1–3 — i.e. exclude
  kana-bearing items (now A1's job) and identical-name-resolvable items (A2).
  Cleanest split: have the worklist generator tag each item with the highest
  stage that can handle it, and each stage's selector filters on that tag.
- Existing Indonesian-derived downstream labels are untouched by all of this
  (that is the Stage B concern, and it is additive).

## Open question surfaced by the audit
- Should Stage 1's deterministic output drip at the same 5/day pace as the LLM,
  or faster (it's cheaper and higher-confidence)? Default assumption pending
  Emma: keep the overall Wikidata-facing drip pace governed by the submitter, so
  Stage 1 can generate a large pool that drains at the submitter's existing rate.
  Recorded here rather than acted on.
