"""Execute QuickStatements v1 lines directly via the Wikidata API.

Fallback for when the QuickStatements API is unavailable. Randomly
selects up to 100 lines from the atomic QS files and executes them
via the Wikidata API with random 1-5 minute intervals between edits.

Environment variables:
    MW_BOTNAME  - Wikidata bot-password username (e.g. "EmmaBot@BotName")
    BOT_TOKEN   - Wikidata bot-password token
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import datetime
import io
import json
import os
import random
import re
import sys
import time
import requests

import conflict_gate
import sutra_gate

WD_API = "https://www.wikidata.org/w/api.php"
UA = USER_AGENT

# 300/day at 30-90s delays (Emma, 2026-07-04). The QuickStatements toolforge
# path is permanently dead — its API demands a one-time manual web-UI batch
# and Emma has said she will not do one — so this direct-API path is now the
# PRIMARY (only) Wikidata editor, not a fallback. 300/day drains the ~25k
# pending lines in ~3 months instead of years; delays stay well inside bot
# norms. Still gated to once per day by cleanup-loop.yml.
#
# CAP is a runtime date-gate, NOT a commit-then-revert (Emma 2026-07-06: reverting
# a config value is how things break — express the exception as a rule instead).
# On the catch-up days below the cap is raised; every other day it is 300. At
# ~30-90s/edit the 6h job timeout admits ~360 edits, so 500 is a real bump.
_DEFAULT_MAX_EDITS = 300
_CAP_EXCEPTIONS = {
    datetime.date(2026, 7, 6): 500,
    datetime.date(2026, 7, 7): 500,
}


def edit_day(now=None):
    """The cap's 'day' rolls over at 02:00 JST (Emma 2026-07-07), not UTC
    midnight: JST is UTC+9, minus the 2h shift = UTC+7."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return (now + datetime.timedelta(hours=7)).date()


MAX_EDITS = _CAP_EXCEPTIONS.get(edit_day(), _DEFAULT_MAX_EDITS)
MIN_DELAY = 30
MAX_DELAY = 90

# MUST be a superset of submit_daily_batch.ATOMIC_FILES (drift-guard test
# enforces it): with the QS path retired (2026-07-04), THIS list is the only
# road to Wikidata — 7 files (both temple label files, kana/identical-name
# labels, cjk backfill, both migrate removals) existed only in the submit
# list and would have been silently orphaned.
ATOMIC_FILES = [
    "modern_shrine_ranking_qualifiers.txt",
    "p4656_jawiki_references.txt",
    "p958_qualifiers.txt",
    "remove_shikinai_hiteisha.txt",
    "remove_shikinaisha.txt",
    "engishiki_add_references.txt",
    "p11250_miraheze_links.txt",
    "p6262_fandom_links.txt",
    "en_labels.txt",
    "kana_en_labels.txt",
    "identical_name_en_labels.txt",
    "temple_en_labels.txt",
    "temple_identical_name_en_labels.txt",
    "cjk_ja_backfill.txt",
    "en_labels_sonnet.txt",
    "category_label_fixes.txt",
    "doujou_address_fixes.txt",
    "shinto_honorifics.txt",                  # Emma 2026-07-16: "a pipeline that actively creates quick statements that go into the queue that get constantly generated and inferred based off of the labels and aliases in Japanese". P1035 honorific suffix on kami + ONE P1813 short name (ja label minus the honorific) with the romaji as a P2440 qualifier + P21=Q24238356 (unknown) / P569=novalue ONLY where absent. The suffix set is data-driven from P31=Q137169543, so a new honorific item self-registers with no code change. Romaji is taken from the item's OWN en label, NEVER transliterated (Emma: "You absolutely should not, in fact, be trying to translate... it reads wrong"). Compounds/groups/label-conflicts go to shinto_honorifics_judgement.txt for Emma instead, never to the drip. ADD-only, self-healing (generate_shinto_honorifics.py).
    "task3_cites_existing.txt",                # TASK 3 half A: P2860 from Emma's 37 papers to cited papers that ALREADY exist on Wikidata. 244 lines, pure add, no creation — order-independent, so genuinely atomic. Every target was existence-checked by DOI (P356) / arXiv (P818) first; 178 of 593 candidates were already there, and skipping that check is what made 5 duplicate papers on 2026-07-15. NOTE this file is a STATIC snapshot, not CI-regenerated like its neighbours, so it is not self-healing in their sense — it stays safe because execute_line() already refuses a claim that exists ("Skipped (already exists)"), so re-running it is a no-op rather than a duplicate. It simply goes inert once the statements land, whether from the drip or from Emma's own QS run of the same batch. Emma took the links and DECLINED the 415 creations (2026-07-16: "Don't create them — links only", "I'm still not mass creating"); regenerate both halves with wikidata-review/scripts/build_task3_cited_papers.py if that ever changes.
    "kami_parent_qualifiers.txt",             # Emma 2026-07-16, from the ontology census: on <parent> P40 <child>, the P25/P22 qualifier names the child's OTHER parent — and the child's own item already records it, so this is a JOIN over existing data, not an inference. "I believe we can do this pretty programmatically, and this is super easy to run, and it is valuable." Refuses blank-node (somevalue) parents and children naming >1 father/mother. ADD-only, self-healing (generate_kami_parent_qualifiers.py).
    "shinto_short_names.txt",               # STAGE 2 of the honorific pipeline (generate_shinto_short_names.py). Reads the P1035 that shinto_honorifics.txt (stage 1) has ALREADY landed, and only then adds the short name P1813 (ja label minus the honorific the item actually carries) + P2440 romaji qualifier + P21=Q24238356 / P569=novalue where absent. Emma 2026-07-16: "it's a stateful thing where the short name isn't even added until the honorific is known" — the pipeline is path-dependent and long-term, "it might take months for an edit to fully finish because it goes in based off of one thing, and then that thing's added. Another query catches it and then starts adding the required whatever's to it." So this file is SMALL at first and grows as stage 1 drips in. ADD-only, self-healing.
    "sutra_label_rename.txt",               # Emma 2026-07-25 (QS source): "LABEL CHANGING: MUST BE DONE ALL AT ONCE ON JULY 30 if item exists". The 3-line S2->Sutra rename (alias mul "S2", label mul "Sutra", P4970 "S2"), split out of sutra_profile.txt because a 1/day drip would leave Q140570154 visibly half-renamed for two days. Capped at 3 so all three land in the first run after sutra_gate opens; same gate as sutra_profile.txt.
    "sutra_profile.txt",                    # Emma 2026-07-16: "you should actually run this autonomously... a daily one edit... at a random point in our edit scheme". The Sutra item (Q140570154) + her researcher item (Q140568870) from wikidata-review/sutra-and-profile-quickstatements.txt. Capped to 1 line/day below and gated by sutra_gate.py (2-week settle from 2026-07-30 + her "#if this one is unmolested" existence check on Q140570154). Her ⚠ UNSURE social-media block (LinkedIn/X/GitHub/Substack) is deliberately EXCLUDED — she held it for a strategic descriptor discussion that has not happened.
    "address_citation_backfill.txt",
    "label_proposals_drip.txt",
    "kana_qualifier_add.txt",
    "kana_redundant_remove.txt",
    "migrate_ritsuryo_funding_remove.txt",
    "migrate_ritsuryo_funding_underspecified_remove.txt",
    "recreation_relations.txt",               # Deferred family relations (P22/P25/P40/P3373) between recreated deleted-items; from recreate-deleted-wikidata/match_new_qids.py
    "durability_backlinks.txt",               # Durability reciprocal backlinks for orphaned 2026-created items (audit of 2026-01-01.txt)
    "ronsha_ojp_name_removals.txt",           # Emma 2026-07-09: a Ronsha is a *candidate*, not an Engishiki shrine, so an Old Japanese (ojp-*) P1448 on one is a name copied off the entry it merely claims to be. Remove-only => drip-safe. Guarded to PURE Ronsha (not also Q134917286/Q135038714).
    "shikinaisha_kokugakuin_refs.txt",        # Emma 2026-07-09: "all P31 Shikinaisha items should get the Kokugakuin university citation thing just like others." Every one of the 2,863 P31=Q134917286 statements was unreferenced while its siblings carried S248=Q135159299 + S13677. Add-only => drip-safe; self-healing (query returns only unreferenced statements).
    "uncited_address_removals.txt",           # Emma 2026-07-09: an uncited Japanese P6375 is import noise when the same shrine also has a cited Japanese address. Remove-only => drip-safe. Refuses any item where an uncited value equals a cited one (QS removes by value, not GUID).
    "reisai.txt",                             # Shrine Reisai (例祭) dates imported from jawiki (P837 day-of-year + P3831=Reisai qualifier + jawiki citation); regenerated in CI by generate_reisai_quickstatements.py
    "bunrei.txt",                             # Shrine bunrei lineage: branch->head-shrine P612 + P1013=Q195793 (Bunrei) qualifier, cited to jinja-kikou.net; derived locally by generate_bunrei_quickstatements.py (name-classification into jinja-kikou's network->head mapping)
    "bunrei_animism.txt",                     # More bunrei: the networks animism.world/総本社まとめ adds beyond jinja-kikou (Kifune/Toshogu/Osugi/Awashima/Sarutahiko/Kotoshironushi), same P612+P1013 model, cited to animism.world
    "bunrei_toranomaki.txt",                  # More bunrei: jisha-toranomaki.com 系列社 table adds Ebisu->西宮神社; same model, cited to jisha-toranomaki
    "bunrei_ikkojin.txt",                     # More bunrei: ikkojin.jp 系統ランキング adds Shirahige->白鬚神社 + Otori->大鳥大社; same model, cited to ikkojin
    "bunrei_shinwa_otaku.txt",                # More bunrei: shinwa-otaku.com's ~57-network list adds the niche tail (Mitsumine/Hisaizu/Shiogama/Watatsumi/Niu/Kamo/Mitoshi/Aoso/...); cited to shinwa-otaku
    "bunrei_nicovideo.txt",                   # More bunrei: dic.nicovideo.jp 神社の系列 adds Suitengu->久留米水天宮 + Tsushima->津島神社; cited to nicovideo dic
    "bunrei_onkamui.txt",                     # More bunrei: onkamui Rakuten blog 総本宮・総本社と分霊社 — NAMED branch enumerations (catches branches whose names differ from their network suffix); parse_onkamui_bunrei.py, unique ja-label matches only, same-name/same-deity tail sections excluded; cited to the blog post
    "bunrei_qualifier_repair.txt",           # Self-healing: qualifier-add lines for bare shrine P612 statements missing P1013=Q195793 (the single-statement bunrei model, Emma 2026-07-07); regenerated in CI by generate_bunrei_qualifier_repair.py
    "reisai_qualifier_repair.txt",           # Self-healing: qualifier-add lines for bare shrine P837 statements missing any P3831 role (docs/wikidata_shrine_festival_model.md); regenerated in CI by generate_reisai_qualifier_repair.py
    "label_typo_fixes.txt",                   # Corrected EN labels from the label_typo_review cloud-RAG answers (collector: shinto_miraheze/collect_label_typo_answers.py)
    "multilingual_label_fixes.txt",           # Emma 2026-08-04: "replacing all of the wrong names ... not just the english one. It's wrong in French and Indonesian too." The fr/id/de/tr labels were built FROM the English ones, so every bad reading label_typo_fixes.txt corrects was copied outward — 寒川神社 carried "sanctuaire de Samugawa" and "Kuil Samugawa" beside the en label. Rewrites any non-ja label containing the old name, keeping that label's own phrasing, and fixes French elision only when the name's vowel class flips. Regenerated by shinto_miraheze/generate_multilingual_label_fixes.py; ADD-only for the alias lines.
    "description_label_pairs.txt",            # Description-without-label cleanup (Emma 2026-07-07): compound desc-then-label pair units (sub-lines joined by ||, executed in order); capped ~100/day below; regenerated in CI by generate_description_fixes.py
    "description_adds.txt",                   # Description MAKER (Emma 2026-07-07): standardized descriptions for items that already have a label in the language but no description; simple adds, uncapped; regenerated in CI by generate_description_adds.py
    "p3225_corporate_numbers.txt",           # Japan Corporate Numbers from the jawiki temple infobox (generate_p3225_quickstatements.py; field ~1%-filled, essentially exhausted at 2 lines 2026-07-08)
    "ronsha_ranking_qualifiers.txt",         # P1352 likelihood qualifiers (1=likely, 0=rest) on ronsha P460 candidates, from cloud-RAG answers (collector: shinto_miraheze/collect_ronsha_rankings.py)
    "saijin_p825.txt",                       # Enshrined deities (祭神) from the jawiki shrine infobox as P825, wikilinked-only precision path (generate_saijin_quickstatements.py); jawiki-cited
    "saijin_deity_research.txt",             # 祭神 as P825 + P1932 "object named as" (source spelling) + P3831=Q140493995 principal-deity role where jawiki marks 主祭神; unlinked names matched to kami items by exact ja-label+deity-class SPARQL (generate_saijin_deity_research.py); ADD-only, jawiki-cited
    "honzon_p825.txt",                       # Principal images (本尊) from the jawiki temple infobox as P825, wikilinked-only precision path (generate_honzon_quickstatements.py); jawiki-cited
    "souken_p571.txt",                       # Founding dates (創建/創建年) from jawiki infoboxes as P571 year-precision; conservative single-clean-year parser (generate_souken_quickstatements.py); jawiki-cited
    "souken_den_p571.txt",                   # Traditional (伝/社伝/寺伝) founding dates as P571 + P1480=Q18122778 "presumably"; disjoint accept-set from souken_p571 (generate_souken_den_quickstatements.py); jawiki-cited
    "miscellaneous_edits.txt",               # Emma 2026-07-10: the miscellaneous-edits queue — small, safe, non-urgent fixes that wait behind conflict_gate. Currently a Commons-category-name English label on Q138565446, plus the Kikuna Shrine statements ブルーノ・プラス stripped, re-added to OUR item Q134926804 (not the husk). ADD-only; diffed against live state so it shrinks as values land. See docs/bruno_plus_analysis_2026-07.md.
    "province_exclusions.txt",                # Engishiki-list exclusions (Emma 2026-07-10: "wire them into the atomic statements thing so that they gradually get done over time"). ADD-ONLY: <list>|P3113|<shrine>|P3831|<class>|P1013|<criterion>, 113 new exclusions + 258 role backfills, point-in-polygon over the CODH province boundaries. assert_add_only() refuses a "-" line from any code path (generate_province_exclusions.py). Province work NEVER removes — Emma 2026-07-10 rejected the "removal half" outright ("we are literally removing nothing from the provinces … this is entirely adding"); the old generate_province_exclusion_removals.py was deleted the same day.
    "sango_p1448.txt",                       # 山号 (sangō) from the jawiki temple infobox as P1448 monolingual ja + P3831=Q11058522 role (Emma 2026-07-10: "official name (P1448) with a qualifier object of statement has role (P3831) sangō (Q11058522). Simple thing."). Filled on 92% of temple articles; parser strips citations, takes a piped wikilink's DISPLAY text, drops parenthetical readings, and refuses anything naming two sangō (generate_sango_quickstatements.py); jawiki-cited
    "hisousha_p119_p547.txt",                # 被葬者 (interred person) from the jawiki kofun infobox, BOTH directions: <person>|P119|<kofun> and <kofun>|P547|<person> (Emma 2026-07-10). 69 of 73 carry P1480=Q18122778 "presumably" because the attribution is 推定/治定/伝/一説 — 治定 is an Imperial Household Agency designation, not an excavation result. [[宮内庁]] is the attributor and is never taken as the occupant; rival candidates are refused; targets must be P31=Q5 (generate_hisousha_quickstatements.py); jawiki-cited
    "shintai_p825.txt",                      # 神体 (shintai) from the jawiki shrine infobox as P825 + P3831=Q327532 role (Emma 2026-07-10: "find a property and it will have the object of statement has role shintai"; P825 chosen for consistency with the 本尊 import). （[[神体山]]） is a CLASS annotation, never the shintai; a piped link whose display differs from its target is refused (柊野#名所・旧跡|神山 targets a district) (generate_shintai_quickstatements.py); jawiki-cited
    "list_membership_rebuild.txt",           # Script 1 of 2 (Emma's wiki-queue item (d)): the Engishiki LIST item is the source of truth — its has-part statements are deduplicated, the shrine items' are not (jawiki piped-link import damage). For every item the list NAMES as a part, set the series ordinal + follows/followed-by DERIVED from the list's own ordering, plus two references (stated in = Kokugakuin University Shrine database + entry id; Wikimedia import URL = the jawiki list article). ADD-only, diffed against live state so it shrinks as it lands (generate_list_membership_rebuild.py).
    "list_membership_removals.txt",          # Script 2 of 2 (Emma, Open questions 2026-07: "these are pure removals — no add, no ordering risk — so this one can just be registered and dripped safely today"): strip the false Engishiki-list membership from the ~2,151 Ronsha the lists do NOT name (piped-link import damage; "Ronshas should not even have list membership"). PURE REMOVE-only, no paired add => drip-safe (2,236 lines over 2,151 items). NEVER touches the 126 the list names: generate_list_membership_removals.py counts any has-part (ordinal or not) as naming and has assert_never_touches_a_named_part; idempotent against live state.
    "kofun_imports.txt",                     # Kofun shapes (P31 shape-classes, the live convention) + construction periods (P571 century precision) from the jawiki kofun infobox (generate_kofun_quickstatements.py); jawiki-cited
    "description_enrichment_en.txt",         # Unique English descriptions for collision groups, from cloud-RAG answers (collector: shinto_miraheze/collect_description_enrichment.py; stage 1 of docs/description_enrichment_pipeline.md)
    "genbu_ids.txt",                         # P13930 Genbu.net ID resolved from genbu.net citations already in our articles -> page's QID via P11250 (generate_genbu_ids.py). ADD-only external id; re-runs are no-ops (execute_line skips existing).
    "shinmei_ids.txt",                       # P14391 Shinmei database ID (Kokugakuin god-name DB) for deities, matched by exact ja label to the scraped kami name+numeric id (generate_shinmei_ids.py). ADD-only external id; single-exact-match only.
    "jinjacho_p973.txt",                     # P973 (described at URL) to each shrine's prefectural 神社庁 database page, from the subtree-merged jinjacho/shrines_and_websites.csv (no dedicated WD property exists). ADD-only; generate_jinjacho_p973.py.
    "beppyo_p612.txt",                       # P612 mother house for 別表神社 (Beppyo) shrines, extracted by an Opus pass over the jawiki article — queue item A0b. The mother house is common in prose (勧請元/分霊元/総本社) and absent from every infobox, which is why it is an LLM job rather than a parser. Membership is reached by P13723=Q10898274, NOT P31 (which returns zero). Follows the single-statement model in docs/wikidata_shrine_festival_model.md: ONE P612 + P1013=Q195793 in the SAME statement, never bare. Q135508874 (autochthonous) is emitted for a positively-described in-situ founding; an article that does not settle the question yields NO statement, because a guessed mother house on a major shrine is the expensive direction. Builder shinto_miraheze/build_beppyo_p612_queue.py, collector shinto_miraheze/collect_beppyo_p612.py (--verify SPARQL-confirms each target is a shrine). ADD-only.
    "name_in_kana.txt",                      # P1814 name in kana (MODERN HIRAGANA) extracted by an LLM from the jawiki lead — queue item A0. Builder shinto_miraheze/build_name_in_kana_queue.py writes a work-file per target (shrine, jawiki sitelink, no top-level P1814); collector shinto_miraheze/collect_name_in_kana.py applies the one gate — hiragana only, katakana REJECTED — and appends the line here with S143=Q177837 + S4656=the jawiki URL. P1814's datatype is `string`, so the value takes bare quotes, no ja: prefix. The 601 Engishiki items carrying an ojp-hani P1448 are HELD out of the queue entirely: the kana-qualifier add/remove pair writes the same property on them, and Emma asked to see that ordering before the subset runs. ADD-only.
    "court_rank_people.txt",                 # P14005 Japanese court rank on PEOPLE, from the ja.wp [[Category:日本の位階受位者]] tree (generate_court_rank_quickstatements.py). Wired in 2026-07-28 once WDQS had indexed the 26 sub-rank items Emma created: all 42 per-rank categories now resolve (the wire-in condition), 12,326 people -> 12,605 statements. Every rank a person held is emitted, not just the highest; 无位 is skipped; recursion does not double-tag a coarser parent rank. ADD-only, and existing person->rank pairs are preloaded from WDQS and skipped, so re-runs shrink the file. Deliberately UNCAPPED: 12.6k lines in a ~106k pool is ~10% of the 300/day draw, the same share as its size peers (p6262_fandom_links, bunrei) — FILE_DAILY_CAPS is for files that would otherwise swamp the pool.
]

# Files that contribute at most N randomly chosen lines per run — used to
# intersperse a bounded slice of a large cohort through the day's selection
# instead of letting it swamp the pool (Emma 2026-07-07: ~100 description
# fixes/day, randomly interspersed, no separate queue).
FILE_DAILY_CAPS = {
    "description_label_pairs.txt": 100,
    # Emma 2026-07-16: "a daily one edit to the entry or one of the quick statements
    # ... at a random point in our edit scheme". ONE line/day, deliberately: the
    # Sutra/profile page is built up slowly rather than landing as a single
    # self-promotional burst (sutra-page-plan.md). Gated by sutra_gate on top.
    "sutra_profile.txt": 1,
    # Emma 2026-07-25, in the QS source: "LABEL CHANGING: MUST BE DONE ALL AT ONCE
    # ON JULY 30 if item exists". The alias/label/P4970 rename is NOT drip-safe —
    # at 1 line/day the item sits for two days half-renamed (label moved to
    # "Sutra" with no "S2" alias yet, or vice versa), which is exactly the
    # visible-in-progress state the rename trick exists to avoid. Split into its
    # own file with a cap of 3 so all three land in the first run after
    # sutra_gate opens (START_DATE = 2026-07-30).
    "sutra_label_rename.txt": 3,
}
# Description ADDS are capped until January 2027 so descriptions don't become
# the dominant edit type while other backlogs drain (Emma 2026-07-07); the cap
# lifts automatically on 2027-01-01 — a date rule, not a value to revert.
if edit_day() < datetime.date(2027, 1, 1):
    FILE_DAILY_CAPS["description_adds.txt"] = 50


# ─────────────────────── sequential-misc file ───────────────────────
# Emma 2026-07-10 (Open questions): "a single sequential miscellaneous file that
# is executed one by one in a random place during the 300 daily edits. It
# essentially just goes one a day." Unlike the atomic files (randomly sampled,
# order-independent), this file runs exactly ONE line per day, top-to-bottom, at
# a random position among the day's edits, NEVER interleaved. That is what makes
# remove-then-add / add-then-remove PAIRS safe under the otherwise-random drip:
# line N is confirmed landed before line N+1 is ever attempted, so the second
# half can't fire first and blank a shrine. It is deliberately NOT in
# ATOMIC_FILES; it has its own cursor. Empty/absent file => no-op.
#
# The cursor indexes the file's executable (non-blank, non-comment) lines. For
# the index to stay stable across runs the file is APPEND-ONLY below the cursor:
# never insert or reorder an executable line above lines already run. Comments
# may be added anywhere (they are filtered out before indexing).
SEQUENTIAL_FILE = "sequential_misc.txt"
SEQUENTIAL_STATE = "sequential_misc.state"


def _seq_path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def load_sequential_lines(path=None):
    """Executable (non-blank, non-comment) lines of the sequential-misc file, in order."""
    path = path or _seq_path(SEQUENTIAL_FILE)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            s = raw.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def load_sequential_cursor(path=None):
    """Index of the next sequential line to run. Missing/corrupt => 0 (fail safe:
    re-runs from the top rather than skipping ahead past unrun lines)."""
    path = path or _seq_path(SEQUENTIAL_STATE)
    try:
        with open(path, encoding="utf-8") as fh:
            return int(json.load(fh).get("cursor", 0))
    except Exception:
        return 0


def save_sequential_cursor(cursor, path=None):
    path = path or _seq_path(SEQUENTIAL_STATE)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"cursor": cursor}, fh)


def next_sequential_line(lines, cursor):
    """The one line to run today, or (None, None) if the sequence is drained."""
    if 0 <= cursor < len(lines):
        return cursor, lines[cursor]
    return None, None


def sequential_should_advance(success, msg):
    """Advance the cursor past a line only when its intended end state is reached:
    a successful edit (incl. "already exists"), or a removal whose target claim is
    already gone. HOLD on any genuine error / rate-limit / parse-fail / gate skip,
    so a paired successor never runs before its predecessor has actually landed —
    the out-of-order blanking Emma built this file to prevent."""
    if success:
        return True
    return msg == "Claim not found for removal"


def read_all_lines():
    """Read all non-empty lines from all atomic QS files (per-file caps apply)."""
    lines = []
    for filepath in ATOMIC_FILES:
        if not os.path.exists(filepath):
            continue
        if filepath in ("sutra_profile.txt", "sutra_label_rename.txt"):
            # Two extra gates: the 2-week settle, and Emma's "#if this one is
            # unmolested" existence check on the Sutra item. Fails closed.
            ok, why = sutra_gate.is_open()
            if not ok:
                print(f"  {filepath} SKIPPED — {why}")
                continue
            print(f"  {filepath} {why}")
        with open(filepath, "r", encoding="utf-8") as f:
            file_lines = [l.strip() for l in f if l.strip()]
        cap = FILE_DAILY_CAPS.get(filepath)
        if cap is not None and len(file_lines) > cap:
            file_lines = random.sample(file_lines, cap)
        lines.extend(file_lines)
    return lines


def parse_qs_value(raw):
    """Parse a QS v1 value token into a Wikidata API-compatible value."""
    if raw.startswith("Q"):
        return {"type": "entity", "value": {"entity-type": "item", "numeric-id": int(raw[1:]), "id": raw}}
    # QS v1 monolingual text: ja:"島根県..." (P6375 etc.)
    m = re.match(r'^([a-z][a-z0-9-]{1,11}):"(.*)"$', raw)
    if m:
        return {"type": "monolingualtext",
                "value": {"text": m.group(2), "language": m.group(1)}}
    if raw.startswith('"') and raw.endswith('"'):
        return {"type": "string", "value": raw[1:-1]}
    if raw in ("novalue", "somevalue"):
        return {"type": raw}
    # QS v1 time: +1580-00-00T00:00:00Z/9  (trailing /N is the precision).
    # Without this, a time value fell through to {"type": "unknown"} and was POSTed
    # as a bare JSON *string*, which wbcreateclaim cannot decode for a time
    # datatype. souken_p571.txt (4,119 lines) and kofun_imports.txt (870) are both
    # registered in ATOMIC_FILES and are both entirely time-valued, so neither could
    # ever have landed through this editor — the only path either of them has.
    # QuickStatements itself always writes the proleptic Gregorian calendar model,
    # so reproducing QS semantics means Q1985727 here too.
    m = re.match(r"^([+-]\d{1,16}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)/(\d{1,2})$", raw)
    if m:
        return {"type": "time", "value": {
            "time": m.group(1),
            "timezone": 0,
            "before": 0,
            "after": 0,
            "precision": int(m.group(2)),
            "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
        }}
    return {"type": "unknown", "value": raw}


def split_qs_parts(line):
    """Split a QS v1 line by | respecting quoted strings."""
    parts = []
    current = []
    in_quotes = False
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
        elif char == '|' and not in_quotes:
            parts.append(''.join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current))
    return parts


def parse_qs_line(line):
    """Parse a QS v1 line into structured components."""
    line = line.strip()
    if not line:
        return None
    if line.startswith("#"):
        return None

    # QuickStatements v1 is canonically TAB-separated; this codebase mostly emits the
    # pipe-separated compact form, and some generators (recreate-deleted-wikidata,
    # durability_backlinks) emit tabs. A line uses one separator or the other, never both,
    # so a line with tabs and no pipe is a tab-form line — normalise it. Without this,
    # tab-form lines parsed to None and were silently skipped, so those batches never ran.
    if "\t" in line and "|" not in line:
        line = line.replace("\t", "|")

    is_removal = line.startswith("-")
    if is_removal:
        line = line[1:]

    parts = split_qs_parts(line)
    if len(parts) < 3:
        return None

    entity = parts[0]
    prop = parts[1]
    value = parse_qs_value(parts[2])

    # QS v1 label/description/alias shorthands: Lxx (label), Dxx (description),
    # Axx (alias) where xx is a language code. These map to wbsetlabel/
    # wbsetdescription/wbsetaliases on the Wikidata API, not wbcreateclaim.
    if len(prop) >= 2 and prop[0] in ("L", "D", "A") and prop[1:].isalpha():
        return {
            "entity": entity,
            "term_kind": prop[0],          # "L", "D", "A"
            "term_lang": prop[1:].lower(),  # e.g. "en"
            "term_value": value.get("value", "") if value["type"] == "string" else "",
            "is_removal": is_removal,
        }

    qualifiers = []
    references = []

    i = 3
    while i + 1 < len(parts):
        p = parts[i]
        v = parse_qs_value(parts[i + 1])
        if p.startswith("S"):
            references.append((f"P{p[1:]}", v))
        else:
            qualifiers.append((p, v))
        i += 2

    return {
        "entity": entity,
        "property": prop,
        "value": value,
        "qualifiers": qualifiers,
        "references": references,
        "is_removal": is_removal,
    }


def load_conflict_watch():
    """The three attention signals, from conflict_watch.state.

    Refreshed by `watch_conflicting_editor.py` in CI. If the file is missing or
    unreadable we do NOT fall through to editing: we assume the watched user edited
    today, which keeps the drip shut until the watcher runs again. Failing closed is
    the whole point of a caution gate.
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "conflict_watch.state")
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except Exception as exc:
        print("conflict_watch.state unreadable ({}) - failing closed".format(exc))
        return {"last_edit": today, "talk_activity": None,
                "noticeboard_mention": None, "project_chat_hold": False}

    def as_date(key):
        raw = state.get(key)
        return datetime.date.fromisoformat(raw) if raw else None

    return {"last_edit": as_date("last_watched_edit") or today,
            "talk_activity": as_date("talk_activity"),
            "noticeboard_mention": as_date("noticeboard_mention"),
            "project_chat_hold": bool(state.get("project_chat_hold"))}


# Items ブルーノ・プラス REPURPOSED — queue.md A5, Emma: "document, don't touch;
# no contact until we understand the editor." Source: docs/bruno_plus_analysis_2026-07.md.
#
# This lives at the SUBMITTER, not in each generator, because generators reach
# these items honestly: the husk now IS the 大美和神社 / 近殿神社 item on Wikidata,
# so any pipeline resolving a jawiki article to a QID by sitelink lands on it.
# Found 2026-08-04: ten staged lines across five atomic files targeted husks,
# including `Q123044569|Len|"Ōmiwa Shrine"` — an edit that would have endorsed
# the repurposing. Patching five generators would leave the sixth to be written;
# one refusal on the only road to Wikidata cannot be bypassed.
REPURPOSED = {
    "Q123044569",   # was Kamo Shrine (Odawara) -> repurposed into 大美和神社
    "Q134886554",   # was Chikadono Shrine (Saitama) -> repurposed into 近殿神社
    "Q134736575",   # 見光寺
    "Q140476265",   # created then blanked; junk husk
}


def item_is_editable(qid, today=None):
    """GATE 2 — per-item freshness. Never edit what someone else just touched.

    Emma: "I want to have the freshness constraint of no editing until something
    hasn't been edited by other users for a week." Unlike the global pause this is
    permanent and about nobody in particular: it removes the whole class of edit
    conflict with any human contributor.

    A lookup failure means we do not know, so we decline — same fail-closed rule.
    """
    # Refused before the revision lookup: these are never editable, whatever
    # their history says, and asking costs a request for an answer we ignore.
    if qid in REPURPOSED:
        return False, "ブルーノ・プラス-repurposed husk — document, don't touch (queue A5)"

    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    try:
        revisions = conflict_gate.fetch_item_revisions(qid)
    except Exception as exc:
        return False, "revision lookup failed ({})".format(exc)
    if conflict_gate.is_item_fresh_enough(revisions, today):
        return True, None
    who = conflict_gate.blocking_editor(revisions, today)
    return False, "{} edited it on {}".format(who[0], who[1]) if who else "recently edited"


def value_to_api_json(parsed_value):
    """Convert a parsed value to the JSON string expected by wbcreateclaim/wbsetqualifier."""
    if parsed_value["type"] in ("entity", "monolingualtext", "time"):
        return json.dumps(parsed_value["value"])
    if parsed_value["type"] == "string":
        return json.dumps(parsed_value["value"])
    if parsed_value["type"] == "unknown":
        # Previously this fell through and POSTed json.dumps(raw) — a bare string
        # for whatever datatype the property has. Refuse it: an unrecognised value
        # token means the encoder is missing a case, not that the API should guess.
        raise ValueError(
            "unencodable QS value {!r} — parse_qs_value has no case for it".format(
                parsed_value.get("value")))
    return json.dumps(parsed_value.get("value", ""))


def wd_login():
    """Log in to Wikidata and return (session, csrf_token)."""
    user = os.environ.get("MW_BOTNAME")
    password = os.environ.get("BOT_TOKEN")
    if not user or not password:
        missing = []
        if not user:
            missing.append("MW_BOTNAME")
        if not password:
            missing.append("BOT_TOKEN")
        print(f"SKIPPED: {', '.join(missing)} not set")
        return None, None

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    r = session.get(WD_API, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json",
    }, timeout=60)
    r.raise_for_status()
    login_token = r.json()["query"]["tokens"]["logintoken"]

    r = session.post(WD_API, data={
        "action": "login", "lgname": user, "lgpassword": password,
        "lgtoken": login_token, "format": "json",
    }, timeout=60)
    r.raise_for_status()
    result = r.json()
    if result.get("login", {}).get("result") != "Success":
        print(f"Login failed: {json.dumps(result, indent=2)}")
        return None, None
    print(f"Logged in as {result['login']['lgusername']}")

    r = session.get(WD_API, params={
        "action": "query", "meta": "tokens", "format": "json",
    }, timeout=60)
    r.raise_for_status()
    csrf = r.json()["query"]["tokens"]["csrftoken"]
    return session, csrf


def find_claim(session, entity, prop, parsed_value):
    """Find an existing claim on entity matching property and value. Returns claim GUID or None."""
    r = session.get(WD_API, params={
        "action": "wbgetentities", "ids": entity, "props": "claims", "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        return None
    r.raise_for_status()

    claims = r.json().get("entities", {}).get(entity, {}).get("claims", {}).get(prop, [])
    for claim in claims:
        mainsnak = claim.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value":
            continue
        dv = mainsnak.get("datavalue", {})

        if parsed_value["type"] == "entity":
            if dv.get("value", {}).get("id") == parsed_value["value"].get("id"):
                return claim["id"]
        elif parsed_value["type"] == "monolingualtext":
            v = dv.get("value", {})
            if (isinstance(v, dict)
                    and v.get("text") == parsed_value["value"]["text"]
                    and v.get("language") == parsed_value["value"]["language"]):
                return claim["id"]
        elif parsed_value["type"] == "string":
            if dv.get("value") == parsed_value["value"]:
                return claim["id"]
    return None


def execute_removal(session, csrf, parsed):
    """Remove a claim matching the given property and value."""
    guid = find_claim(session, parsed["entity"], parsed["property"], parsed["value"])
    if not guid:
        return False, "Claim not found for removal"
    r = session.post(WD_API, data={
        "action": "wbremoveclaims", "claim": guid,
        "token": csrf, "bot": 1, "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"API error: {result['error'].get('info', str(result['error']))}"
    return True, "Removed"


def execute_create_claim(session, csrf, entity, prop, parsed_value):
    """Create a new claim. Returns (success, message, claim_guid)."""
    snaktype = "value"
    if parsed_value["type"] in ("novalue", "somevalue"):
        snaktype = parsed_value["type"]

    data = {
        "action": "wbcreateclaim", "entity": entity,
        "property": prop, "snaktype": snaktype,
        "token": csrf, "bot": 1, "format": "json",
    }
    if snaktype == "value":
        data["value"] = value_to_api_json(parsed_value)

    r = session.post(WD_API, data=data, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests", None
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"API error: {result['error'].get('info', str(result['error']))}", None
    guid = result.get("claim", {}).get("id")
    return True, "Created", guid


def execute_set_qualifier(session, csrf, guid, prop, parsed_value):
    """Add a qualifier to an existing claim."""
    snaktype = "value"
    if parsed_value["type"] in ("novalue", "somevalue"):
        snaktype = parsed_value["type"]

    data = {
        "action": "wbsetqualifier", "claim": guid,
        "property": prop, "snaktype": snaktype,
        "token": csrf, "bot": 1, "format": "json",
    }
    if snaktype == "value":
        data["value"] = value_to_api_json(parsed_value)

    r = session.post(WD_API, data=data, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"Qualifier error: {result['error'].get('info', str(result['error']))}"
    return True, "Qualifier added"


def execute_set_reference(session, csrf, guid, ref_pairs):
    """Add a reference group to an existing claim."""
    ref_snaks = {}
    for r_prop, r_val in ref_pairs:
        snak = {"snaktype": "value", "property": r_prop}
        if r_val["type"] == "entity":
            snak["datavalue"] = {"type": "wikibase-entityid", "value": r_val["value"]}
        else:
            snak["datavalue"] = {"type": "string", "value": r_val["value"]}
        ref_snaks.setdefault(r_prop, []).append(snak)

    r = session.post(WD_API, data={
        "action": "wbsetreference", "statement": guid,
        "snaks": json.dumps(ref_snaks),
        "token": csrf, "bot": 1, "format": "json",
    }, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"Reference error: {result['error'].get('info', str(result['error']))}"
    return True, "Reference added"


def execute_set_term(session, csrf, entity, kind, lang, value):
    """Set/clear a label, description, or alias via wbsetlabel/wbsetdescription/wbsetaliases."""
    if kind == "L":
        action = "wbsetlabel"
    elif kind == "D":
        action = "wbsetdescription"
    elif kind == "A":
        action = "wbsetaliases"
    else:
        return False, f"Unknown term kind: {kind}"

    data = {
        "action": action,
        "id": entity,
        "language": lang,
        "token": csrf,
        "bot": 1,
        "format": "json",
    }
    if action == "wbsetaliases":
        data["add"] = value
    else:
        data["value"] = value

    r = session.post(WD_API, data=data, timeout=60)
    if r.status_code == 429:
        return False, "429 Too Many Requests"
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        return False, f"API error: {result['error'].get('info', str(result['error']))}"
    return True, f"{action} {lang}={value!r}"


def execute_line(session, csrf, parsed):
    """Execute a single parsed QS v1 line via Wikidata API."""
    if parsed.get("term_kind"):
        # Lxx / Dxx / Axx — label / description / alias.
        if parsed["is_removal"]:
            return False, "Term removal not supported"
        return execute_set_term(
            session, csrf,
            parsed["entity"], parsed["term_kind"],
            parsed["term_lang"], parsed["term_value"],
        )

    if parsed["is_removal"]:
        return execute_removal(session, csrf, parsed)

    entity = parsed["entity"]
    prop = parsed["property"]
    value = parsed["value"]
    has_qualifiers = bool(parsed["qualifiers"])
    has_references = bool(parsed["references"])

    if not has_qualifiers and not has_references:
        # Check if claim already exists to avoid duplicates
        existing = find_claim(session, entity, prop, value)
        if existing:
            return True, "Skipped (already exists)"
        ok, msg, _ = execute_create_claim(session, csrf, entity, prop, value)
        return ok, msg

    # Find existing claim, or create one
    guid = find_claim(session, entity, prop, value)
    if not guid:
        ok, msg, guid = execute_create_claim(session, csrf, entity, prop, value)
        if not ok:
            return False, msg
        time.sleep(1)

    # Add qualifiers
    for q_prop, q_val in parsed["qualifiers"]:
        ok, msg = execute_set_qualifier(session, csrf, guid, q_prop, q_val)
        if not ok:
            return False, msg
        time.sleep(0.5)

    # Add references
    if has_references:
        ok, msg = execute_set_reference(session, csrf, guid, parsed["references"])
        if not ok:
            return False, msg

    return True, "Done"


def main():
    print("=== Direct Wikidata API Edits (QS fallback) ===\n")

    # GATE 1 — global pause. See conflict_gate.py and
    # docs/bruno_plus_analysis_2026-07.md. Emma 2026-07-10, on ブルーノ・プラス:
    # "This is maximum caution with this person … I think that this person is an LTA."
    # A paused run is a SKIP, not a failure: nothing was attempted, so nothing broke.
    today = datetime.datetime.now(datetime.timezone.utc).date()
    watch = load_conflict_watch()
    reason = conflict_gate.pause_reason(
        today, watch["last_edit"], watch["talk_activity"],
        watch["noticeboard_mention"], watch["project_chat_hold"])
    if reason:
        print("SKIPPED: {}".format(reason))
        return 0

    all_lines = read_all_lines()
    if not all_lines:
        print("No QS lines found in any atomic file. Nothing to do.")
        return 0  # genuinely-drained backlog is success, not failure

    # Randomly select up to MAX_EDITS lines
    selected = random.sample(all_lines, min(MAX_EDITS, len(all_lines)))
    print(f"Selected {len(selected)} random lines from {len(all_lines)} available\n")

    # Weave in today's single sequential-misc line (one/day, strict order) at a
    # random position. Empty/absent file or drained cursor => nothing added.
    seq_lines = load_sequential_lines()
    seq_cursor = load_sequential_cursor()
    seq_idx, seq_line = next_sequential_line(seq_lines, seq_cursor)
    seq_pos = None
    seq_ran = False
    seq_advance = False
    if seq_line is not None:
        seq_pos = random.randint(0, len(selected))
        selected.insert(seq_pos, seq_line)
        print(f"Sequential-misc: line #{seq_idx} woven in at position "
              f"{seq_pos + 1}/{len(selected)}: {seq_line}\n")

    session, csrf = wd_login()
    if not session:
        print("FATAL: login failed — no edits attempted. Failing the run.")
        return 1  # a broken/invalidated bot token must redden, not exit green

    succeeded = 0
    failed = 0
    skipped = 0

    rate_limited = False
    for i, line in enumerate(selected, 1):
        # Is THIS the woven-in sequential-misc line? Its cursor advances only when
        # its own edit reaches its end state (tracked via seq_ran/seq_advance).
        is_seq = seq_pos is not None and (i - 1) == seq_pos
        if is_seq:
            seq_ran = True
            seq_advance = False  # default HOLD; set True only on a real end state
        # Compound unit: sub-lines joined by "||" execute sequentially and stop
        # at the first failure — used for description-then-label pairs where
        # the label add is only valid once the description landed (Emma
        # 2026-07-07; docs/wikidata_shrine_festival_model.md sibling rule).
        sublines = [s for s in line.split("||") if s.strip()]
        for j, sub in enumerate(sublines):
            parsed = parse_qs_line(sub)
            if not parsed:
                print(f"[{i}/{len(selected)}] SKIP: Could not parse: {sub}")
                failed += 1
                break

            action = "REMOVE" if parsed["is_removal"] else "EDIT"
            tag = f" (pair {j+1}/{len(sublines)})" if len(sublines) > 1 else ""
            print(f"[{i}/{len(selected)}] {action}{tag}: {sub}")

            # GATE 2 — per-item freshness. Counted as neither success nor failure:
            # declining to edit is the correct outcome, and must not redden the run.
            ok, why = item_is_editable(parsed["entity"], today)
            if not ok:
                print(f"  SKIP: {parsed['entity']} — {why}")
                skipped += 1
                break

            try:
                success, msg = execute_line(session, csrf, parsed)
                # The CSRF token is issued once at login and expires mid-run. Run
                # 29877450149 (2026-07-21) logged in at 23:33, hit its first
                # "Invalid CSRF token" at 02:57 — 3h24m in — and then every
                # remaining edit failed: 99 of that run's 106 failures were this
                # one cause. Re-login once and retry the line before counting it
                # as a failure.
                if not success and "Invalid CSRF token" in msg:
                    print("  CSRF token expired — re-logging in and retrying")
                    new_session, new_csrf = wd_login()
                    if new_session:
                        session, csrf = new_session, new_csrf
                        success, msg = execute_line(session, csrf, parsed)
                    else:
                        msg = "re-login failed after CSRF expiry"
                if success:
                    print(f"  OK: {msg}")
                    succeeded += 1
                else:
                    print(f"  FAIL: {msg}")
                    failed += 1
                    if "429" in msg:
                        print("  Rate-limited — stopping further edits")
                        rate_limited = True
                if is_seq:
                    seq_advance = sequential_should_advance(success, msg)
                if not success:
                    break  # don't run the rest of the pair after a failure
            except Exception as e:
                print(f"  ERROR: {e}")
                failed += 1
                break
            if j < len(sublines) - 1:
                time.sleep(2)  # brief gap between the halves of a pair
        if rate_limited:
            break

        # Random delay 60-300 seconds between edits
        if i < len(selected):
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            print(f"  Waiting {delay}s before next edit...", flush=True)
            time.sleep(delay)

    print(f"\n=== Results: {succeeded} succeeded, {failed} failed ===")

    # Advance the sequential-misc cursor iff today's sequential line reached its end
    # state. Held otherwise (error / rate-limit / gate skip / never reached because a
    # 429 stopped the run first), so the same line retries next run and its ordered
    # successor never runs ahead of it.
    if seq_pos is not None:
        if seq_ran and seq_advance:
            save_sequential_cursor(seq_cursor + 1)
            print(f"Sequential-misc: cursor advanced {seq_cursor} -> {seq_cursor + 1}")
        else:
            print(f"Sequential-misc: cursor held at {seq_cursor} "
                  f"(line #{seq_idx} retries next run)")

    # Total failure: attempted edits but NONE landed (the 2026-07-06 outage — an
    # invalidated bot token failing every save — hid behind a green run for days).
    # Redden the run so it surfaces instead of silently pretending to edit.
    if succeeded == 0 and failed > 0:
        print(f"FATAL: 0/{failed} edits succeeded — failing the run so the outage surfaces.")
        return 1
    return 0


if __name__ == "__main__":
    # In the main guard, not at import: tests import this module under pytest.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.exit(main())
