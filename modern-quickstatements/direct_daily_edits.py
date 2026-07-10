"""Execute QuickStatements v1 lines directly via the Wikidata API.

Fallback for when the QuickStatements API is unavailable. Randomly
selects up to 100 lines from the atomic QS files and executes them
via the Wikidata API with random 1-5 minute intervals between edits.

Environment variables:
    MW_BOTNAME  - Wikidata bot-password username (e.g. "EmmaBot@BotName")
    BOT_TOKEN   - Wikidata bot-password token
"""

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

WD_API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

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
    "address_citation_backfill.txt",
    "label_proposals_drip.txt",
    "kana_qualifier_add.txt",
    "kana_redundant_remove.txt",
    "migrate_ritsuryo_funding_remove.txt",
    "migrate_ritsuryo_funding_underspecified_remove.txt",
    "recreation_relations.txt",               # Deferred family relations (P22/P25/P40/P3373) between recreated deleted-items; from recreate-deleted-wikidata/match_new_qids.py
    "durability_backlinks.txt",               # Durability reciprocal backlinks for orphaned 2026-created items (audit of 2026-01-01.txt)
    "remove_junk_aliases.txt",                # Alias audit (queue #8): remove 189 comma-disambiguator junk aliases the pipeline dragged onto shrine/temple items (via query-main SPARQL)
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
    "description_label_pairs.txt",            # Description-without-label cleanup (Emma 2026-07-07): compound desc-then-label pair units (sub-lines joined by ||, executed in order); capped ~100/day below; regenerated in CI by generate_description_fixes.py
    "description_adds.txt",                   # Description MAKER (Emma 2026-07-07): standardized descriptions for items that already have a label in the language but no description; simple adds, uncapped; regenerated in CI by generate_description_adds.py
    "p3225_corporate_numbers.txt",           # Japan Corporate Numbers from the jawiki temple infobox (generate_p3225_quickstatements.py; field ~1%-filled, essentially exhausted at 2 lines 2026-07-08)
    "ronsha_ranking_qualifiers.txt",         # P1352 likelihood qualifiers (1=likely, 0=rest) on ronsha P460 candidates, from cloud-RAG answers (collector: shinto_miraheze/collect_ronsha_rankings.py)
    "saijin_p825.txt",                       # Enshrined deities (祭神) from the jawiki shrine infobox as P825, wikilinked-only precision path (generate_saijin_quickstatements.py); jawiki-cited
    "honzon_p825.txt",                       # Principal images (本尊) from the jawiki temple infobox as P825, wikilinked-only precision path (generate_honzon_quickstatements.py); jawiki-cited
    "souken_p571.txt",                       # Founding dates (創建/創建年) from jawiki infoboxes as P571 year-precision; conservative single-clean-year parser (generate_souken_quickstatements.py); jawiki-cited
    "souken_den_p571.txt",                   # Traditional (伝/社伝/寺伝) founding dates as P571 + P1480=Q18122778 "presumably"; disjoint accept-set from souken_p571 (generate_souken_den_quickstatements.py); jawiki-cited
    "miscellaneous_edits.txt",               # Emma 2026-07-10: the miscellaneous-edits queue — small, safe, non-urgent fixes that wait behind conflict_gate. Currently a Commons-category-name English label on Q138565446, plus the Kikuna Shrine statements ブルーノ・プラス stripped, re-added to OUR item Q134926804 (not the husk). ADD-only; diffed against live state so it shrinks as values land. See docs/bruno_plus_analysis_2026-07.md.
    "province_exclusions.txt",                # Engishiki-list exclusions (Emma 2026-07-10: "wire them into the atomic statements thing so that they gradually get done over time"). ADD-only: <list>|P3113|<shrine>|P3831|<class>|P1013|<criterion>, 113 new exclusions + 258 role backfills, point-in-polygon over the CODH province boundaries. assert_add_only() refuses a "-" line from any code path (generate_province_exclusions.py). The paired REMOVAL script (generate_province_exclusion_removals.py) stays UNREGISTERED on purpose: it is add-first/remove-later and must only run once SPARQL confirms the adds landed.
    "sango_p1448.txt",                       # 山号 (sangō) from the jawiki temple infobox as P1448 monolingual ja + P3831=Q11058522 role (Emma 2026-07-10: "official name (P1448) with a qualifier object of statement has role (P3831) sangō (Q11058522). Simple thing."). Filled on 92% of temple articles; parser strips citations, takes a piped wikilink's DISPLAY text, drops parenthetical readings, and refuses anything naming two sangō (generate_sango_quickstatements.py); jawiki-cited
    "kofun_imports.txt",                     # Kofun shapes (P31 shape-classes, the live convention) + construction periods (P571 century precision) from the jawiki kofun infobox (generate_kofun_quickstatements.py); jawiki-cited
    "description_enrichment_en.txt",         # Unique English descriptions for collision groups, from cloud-RAG answers (collector: shinto_miraheze/collect_description_enrichment.py; stage 1 of docs/description_enrichment_pipeline.md)
]

# Files that contribute at most N randomly chosen lines per run — used to
# intersperse a bounded slice of a large cohort through the day's selection
# instead of letting it swamp the pool (Emma 2026-07-07: ~100 description
# fixes/day, randomly interspersed, no separate queue).
FILE_DAILY_CAPS = {
    "description_label_pairs.txt": 100,
}
# Description ADDS are capped until January 2027 so descriptions don't become
# the dominant edit type while other backlogs drain (Emma 2026-07-07); the cap
# lifts automatically on 2027-01-01 — a date rule, not a value to revert.
if edit_day() < datetime.date(2027, 1, 1):
    FILE_DAILY_CAPS["description_adds.txt"] = 50


def read_all_lines():
    """Read all non-empty lines from all atomic QS files (per-file caps apply)."""
    lines = []
    for filepath in ATOMIC_FILES:
        if not os.path.exists(filepath):
            continue
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


def item_is_editable(qid, today=None):
    """GATE 2 — per-item freshness. Never edit what someone else just touched.

    Emma: "I want to have the freshness constraint of no editing until something
    hasn't been edited by other users for a week." Unlike the global pause this is
    permanent and about nobody in particular: it removes the whole class of edit
    conflict with any human contributor.

    A lookup failure means we do not know, so we decline — same fail-closed rule.
    """
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

    session, csrf = wd_login()
    if not session:
        print("FATAL: login failed — no edits attempted. Failing the run.")
        return 1  # a broken/invalidated bot token must redden, not exit green

    succeeded = 0
    failed = 0
    skipped = 0

    rate_limited = False
    for i, line in enumerate(selected, 1):
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
                if success:
                    print(f"  OK: {msg}")
                    succeeded += 1
                else:
                    print(f"  FAIL: {msg}")
                    failed += 1
                    if "429" in msg:
                        print("  Rate-limited — stopping further edits")
                        rate_limited = True
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
