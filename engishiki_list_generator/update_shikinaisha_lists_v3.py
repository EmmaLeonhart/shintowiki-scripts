#!/usr/bin/env python3
"""
update_shikinaisha_lists.py  •  2025-07-07

• Refresh every "List of Shikinaisha in X Province" sitting in
  [[Category:Lists of Shikinaisha by location]] on shinto.miraheze.org.
• Migrates the new columns you requested:
      – Same-as (P460)    (added previously)
      – Co-ords           (new here, P625)
• Counts fallback to zero if missing.
• Safe label helper prevents crashes from items that lack labels or redirect.
"""

import os, re, time, argparse, requests, sys, io
from html import escape

# Handle UTF-8 encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── No delay - start immediately ───────────────────────
import json
STATE_FILE = "shiki_list_progress.json"

def load_progress():
    """Load progress from state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_progress(state):
    """Save progress to state file."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

progress = load_progress()

# Flag to track when we've reached Izumi Province
started_from_izumi = False

print("[INFO] Starting update now...")
print(f"[INFO] Will skip all provinces until reaching Izumi Province, then process from there")

# ── endpoints ───────────────────────────────────────────
WIKI_API = "https://shinto.miraheze.org/w/api.php"
WD_API   = "https://www.wikidata.org/w/api.php"

USER = os.getenv("WIKI_USER") or "Immanuelle"
PASS = os.getenv("WIKI_PASS") or "[REDACTED_SECRET_2]"

S = requests.Session()
S.headers["User-Agent"] = "ShikinaishaListBot/0.7 (coords col)"

# ────────────────────────────────────────────────────────
#  MediaWiki helpers
# ────────────────────────────────────────────────────────
def wiki_login() -> str:
    import time as time_module
    attempt = 0
    while True:  # Infinite retries - NEVER give up
        attempt += 1
        try:
            r1 = S.get(WIKI_API, params={
                "action": "query", "meta": "tokens",
                "type": "login", "format": "json"}, timeout=30)
            r1.raise_for_status()
            t = r1.json()

            S.post(WIKI_API, data={
                "action": "login", "lgname": USER, "lgpassword": PASS,
                "lgtoken": t["query"]["tokens"]["logintoken"], "format": "json"},
                timeout=30)

            r2 = S.get(WIKI_API, params={
                "action": "query", "meta": "tokens", "format": "json"}, timeout=30)
            r2.raise_for_status()
            csrf = r2.json()["query"]["tokens"]["csrftoken"]
            print(f"[INFO] Login successful (attempt {attempt})", flush=True)
            return csrf
        except Exception as e:
            wait = 60 * min(attempt, 5)  # Cap at 300 seconds (5 minutes)
            print(f"[WARNING] Login failed (attempt {attempt}): {e}", flush=True)
            print(f"[INFO] Retrying in {wait} seconds...", flush=True)
            time_module.sleep(wait)

def cat_members(cat):
    cont = ""
    while True:
        r = S.get(WIKI_API, params={
            "action": "query", "list": "categorymembers", "cmtitle": cat,
            "cmlimit": "500", "cmcontinue": cont, "format": "json"}).json()
        for m in r["query"]["categorymembers"]:
            yield m["title"]
        if "continue" not in r:
            break
        cont = r["continue"]["cmcontinue"]

def wiki_get(title):
    r = S.get(WIKI_API, params={
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "content", "rvslots": "main", "format": "json"}).json()
    page = next(iter(r["query"]["pages"].values()))
    rev  = page.get("revisions")
    return rev[0]["slots"]["main"]["*"] if rev else ""

def wiki_edit(title, text, summary, token, dry):
    if dry:
        try:
            print(f"\n── {title} (preview) ──\n{text[:600]}…\n")
        except UnicodeEncodeError:
            print(f"\n── [page with unicode title] (preview) ──\n{text[:600]}…\n")
        return
    r = S.post(WIKI_API, data={
        "action": "edit", "title": title, "text": text, "token": token,
        "format": "json", "summary": summary, "bot": 1}).json()
    if "error" in r:
        raise RuntimeError(r["error"])
    try:
        print(f"[OK] {title}")
    except UnicodeEncodeError:
        print("[OK] [page with unicode title]")

def extract_wikidata_qid(content: str) -> str | None:
    """Extract Wikidata QID from {{wikidata link|...}} template."""
    match = re.search(r"{{wikidata link\|([^}]+)}}", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def find_alias_name(base_name: str, province: str, existing_names: set) -> str:
    """Find a non-colliding alias name."""
    if base_name not in existing_names:
        return base_name
    alias = f"{base_name} ({province})"
    if alias not in existing_names:
        return alias
    counter = 2
    while True:
        alias = f"{base_name} ({province} {counter})"
        if alias not in existing_names:
            return alias
        counter += 1

def determine_shrine_page_name(qid: str, shrine_name: str, province: str, created_pages: dict = None) -> tuple[str, str]:
    """Determine what page name will be used for a shrine (WITHOUT creating the page).
    Returns (page_name, status_reason).

    Conservative logic: if a page has ANY wikidata link, skip it or create (QID) version.

    Args:
        qid: Wikidata QID of the shrine
        shrine_name: Base name of the shrine
        province: Province name (for alias generation)
        created_pages: Optional dict mapping qid -> actual_page_name for shrines already created in this batch
    """
    if created_pages is None:
        created_pages = {}

    ent = get_entity_cached(qid)

    # Get preferred page name (ShintoWiki > English Wikipedia > English label)
    pref_name = None
    for claim in ent.get("claims", {}).get("P11250", []):
        article_id = claim["mainsnak"]["datavalue"]["value"]
        if article_id.startswith("shinto:"):
            pref_name = article_id[7:]
            break

    if not pref_name:
        sitelinks = ent.get("sitelinks", {})
        if "enwiki" in sitelinks:
            pref_name = sitelinks["enwiki"]["title"]
        else:
            pref_name = _lbl(ent, qid)

    # Check if page exists
    r = S.get(WIKI_API, params={
        "action": "query", "titles": pref_name, "format": "json"}).json()
    pages = r["query"]["pages"]
    page = next(iter(pages.values()))

    if "missing" not in page:
        # Page exists - check if it has ANY wikidata link
        r2 = S.get(WIKI_API, params={
            "action": "query", "titles": pref_name, "prop": "revisions",
            "rvprop": "content", "format": "json"}).json()
        pages2 = r2["query"]["pages"]
        page2 = next(iter(pages2.values()))
        if "revisions" in page2:
            existing_content = page2["revisions"][0]["*"]
            existing_qid = extract_wikidata_qid(existing_content)

            if existing_qid:
                # Page already has a wikidata link
                if existing_qid == qid:
                    # Same QID - skip it
                    return (pref_name, "SKIP")
                else:
                    # Different QID - must use (QID) version to avoid collision
                    qid_name = f"{pref_name} ({qid})"
                    return (qid_name, "WILL_CREATE_QID_VERSION")
            else:
                # Existing page has NO wikidata link - safe to overwrite
                return (pref_name, "WILL_CREATE")

    # Page doesn't exist - check if name was created earlier in this batch
    if pref_name in created_pages.values():
        # The name was created in this batch - create (QID) version
        qid_name = f"{pref_name} ({qid})"
        return (qid_name, "WILL_CREATE_QID_VERSION")

    return (pref_name, "WILL_CREATE")

def create_shrine_page(qid: str, shrine_name: str, province: str, actual_page_name: str, table_row: str, token: str, dry: bool = False) -> str:
    """Create individual shrine page with the specified page name. Returns status string."""
    ent = get_entity_cached(qid)

    page_content = f"""'''{actual_page_name}''' is a shrine in the Engishiki Jinmyōchō. It is located in [[{province}]].

{table_row}

{{{{wikidata link|{qid}}}}}

[[Category:Shikinaisha in {province}]]
[[Category:Wikidata generated shikinaisha pages]]"""

    wiki_edit(actual_page_name, page_content, f"Bot: Create shrine page for {shrine_name}", token, dry)
    return "DONE"

# ────────────────────────────────────────────────────────
#  Wikidata helpers
# ────────────────────────────────────────────────────────
def wd_entity(qid: str) -> dict:
    return S.get(WD_API, params={
        "action": "wbgetentities", "ids": qid,
        "props": "labels|claims|sitelinks", "languages": "en,ja",
        "redirects": "yes", "format": "json"}).json()["entities"][qid]

# ── safe label helper -------------------------------------------------
def _lbl(ent: dict, fallback: str = "") -> str:
    """Return English label, else Japanese, else fallback."""
    return (ent.get("labels", {})
              .get("en", ent.get("labels", {}).get("ja", {}))
              .get("value", fallback))

# ── global caches to avoid duplicate API hits ------------------------
_ENT_CACHE: dict[str, dict] = {}
def get_entity_cached(qid: str) -> dict:
    ent = _ENT_CACHE.get(qid)
    if ent is None:
        ent = wd_entity(qid)
        _ENT_CACHE[qid] = ent
    return ent

# ────────────────────────────────────────────────────────
#  Row harvesting / counts
# ────────────────────────────────────────────────────────
COUNT_CLASSES = {
    "Q134917286": "total",
    "Q134917287": "shosha",
    "Q134917288": "taisha",
}

def get_quantity(claim) -> str:
    for q in claim.get("qualifiers", {}).get("P1114", []):
        val = q["datavalue"]["value"]
        if isinstance(val, dict) and "amount" in val:
            return val["amount"].lstrip("+")
        return str(val).lstrip("+")
    return "0"

def harvest_shiki(ent):
    counts = {"total": "0", "shosha": "0", "taisha": "0"}
    rows   = []

    for cl in ent["claims"].get("P527", []):
        tgt = cl["mainsnak"]["datavalue"]["value"]["id"]

        if tgt in COUNT_CLASSES:                      # province counts
            counts[COUNT_CLASSES[tgt]] = get_quantity(cl)
            continue

        prov_ord = next((q["datavalue"]["value"]
                         for q in cl.get("qualifiers", {}).get("P1545", [])), "")

        sub  = get_entity_cached(tgt)
        name = _lbl(sub)
        kana = next((c["mainsnak"]["datavalue"]["value"]
                     for c in sub["claims"].get("P1814", [])), "")

        glob_ord = ""
        for p31 in sub["claims"].get("P31", []):
            if p31["mainsnak"]["datavalue"]["value"]["id"] == "Q134917286":
                glob_ord = next((q["datavalue"]["value"]
                                 for q in p31.get("qualifiers", {}).get("P1545", [])), "")
                break

        rank_qid = ""
        for rcl in sub["claims"].get("P31", []):
            rk = rcl["mainsnak"]["datavalue"]["value"]["id"]
            if rk in {"Q134917287", "Q134917288", "Q9610964"}:
                rank_qid = rk
                break

        rows.append((
            int(prov_ord or "9999"),
            prov_ord, glob_ord, name, kana, rank_qid, tgt
        ))

    rows.sort(key=lambda x: x[0])
    return rows, counts

# ────────────────────────────────────────────────────────
#  Extra column helpers
# ────────────────────────────────────────────────────────
DISTRICT_QIDS = {"Q1122846", "Q46426234"}
Q_SHRINE      = "Q845945"

SEAT_QID   = "Q135018062"
SUB_QID    = "Q135022834"

def build_ill_template(qid: str) -> str:
    """Build {{ill|}} template with proper destination priority and interwikis."""
    ent = get_entity_cached(qid)
    parts = []

    # Determine destination link (priority: shinto wiki, then enwiki, then en label, then fallback)
    sitelinks = ent.get("sitelinks", {})

    # Check for shinto wiki link (via P11250 Miraheze article ID)
    destination = None
    for claim in ent["claims"].get("P11250", []):
        article_id = claim["mainsnak"]["datavalue"]["value"]
        if article_id.startswith("shinto:"):
            destination = article_id[7:]  # Remove "shinto:" prefix
            break

    # Fall back to enwiki
    if not destination and "enwiki" in sitelinks:
        destination = sitelinks["enwiki"]["title"]

    # Fall back to en label
    if not destination:
        destination = ent.get("labels", {}).get("en", {}).get("value", "")

    # Final fallback
    if not destination:
        destination = _lbl(ent, qid)

    parts.append(escape(destination))

    # Add interwikis (prioritize enwiki and jawiki, then others)
    priority_order = ["enwiki", "jawiki"]
    other_langs = sorted([k for k in sitelinks.keys() if k not in priority_order])
    ordered_langs = [l for l in priority_order if l in sitelinks] + other_langs

    for lang_code in ordered_langs:
        lang = lang_code.replace("wiki", "")
        parts.append(lang)
        parts.append(escape(sitelinks[lang_code]["title"]))

    # Add English label with lt= if different from destination
    en_label = ent.get("labels", {}).get("en", {}).get("value", "")
    if en_label and en_label != destination:
        parts.append(f"lt={escape(en_label)}")

    # Add WD link at end
    parts.append(f"WD={qid}")

    return "{{" + "ill|" + "|".join(parts) + "}}"

def district_name(qid: str) -> str:
    ent = get_entity_cached(qid)
    for cl in ent["claims"].get("P131", []):
        loc_id = cl["mainsnak"]["datavalue"]["value"]["id"]
        loc    = get_entity_cached(loc_id)
        inst   = {x["mainsnak"]["datavalue"]["value"]["id"]
                  for x in loc["claims"].get("P31", [])}
        if inst & DISTRICT_QIDS:
            return build_ill_template(loc_id)
    return "—"

def seat_quantity(qid: str) -> str:
    ent = get_entity_cached(qid)
    seats = subs = 0

    for cl in ent["claims"].get("P527", []):
        part_id = cl["mainsnak"]["datavalue"]["value"]["id"]

        # --- safe quantity extraction ---
        qty_raw = next(
            (q["datavalue"]["value"]
             for q in cl.get("qualifiers", {}).get("P1114", [])),
            None
        )
        if isinstance(qty_raw, dict) and "amount" in qty_raw:
            qty = int(qty_raw["amount"].lstrip("+"))
        elif qty_raw is not None:
            try:
                qty = int(str(qty_raw).lstrip("+"))
            except ValueError:
                qty = 0
        else:
            qty = 0
        # --- end extractor ---

        if part_id == SEAT_QID:
            seats += qty or 1
        elif part_id == SUB_QID:
            subs += qty or 1

    if seats or subs:
        parts = []
        if seats: parts.append(f"{seats} seat{'s' if seats!=1 else ''}")
        if subs:  parts.append(f"{subs} shrine{'s' if subs!=1 else ''}")
        return " / ".join(parts)
    return "single"


def parent_shrine_links(qid: str) -> str:
    ent = get_entity_cached(qid)
    links = []
    for cl in ent["claims"].get("P361", []):
        tgt = cl["mainsnak"]["datavalue"]["value"]["id"]
        tgt_ent = get_entity_cached(tgt)
        if any(p["mainsnak"]["datavalue"]["value"]["id"] == Q_SHRINE
               for p in tgt_ent["claims"].get("P31", [])):
            name = _lbl(tgt_ent, tgt)
            links.append(f"{{{{ill|{escape(name)}|WD={tgt}}}}}")
    return "; ".join(links) if links else "—"

def same_as_qids(qid: str) -> list:
    """Get list of same-as shrine QIDs."""
    ent = get_entity_cached(qid)
    qids = []
    for cl in ent["claims"].get("P460", []):
        tgt = cl["mainsnak"]["datavalue"]["value"]["id"]
        qids.append(tgt)
    return qids

def same_as_links(qid: str) -> str:
    ent = get_entity_cached(qid)
    links = []
    for cl in ent["claims"].get("P460", []):
        tgt = cl["mainsnak"]["datavalue"]["value"]["id"]
        # Use the same proper linking format as build_shrine_link()
        links.append(build_shrine_link(tgt))
    return "; ".join(links) if links else "—"

def coord_cell(qid: str) -> str:
    ent = get_entity_cached(qid)
    p625 = next(iter(ent["claims"].get("P625", [])), None)
    if not p625:
        return '—'
    val = p625["mainsnak"]["datavalue"]["value"]
    return f"{{{{coord|{val['latitude']:.6f}|{val['longitude']:.6f}|display=inline}}}}"

SHRINE_DESIGNATION_MAP = {
    "Q1107129": "sōja",
    "Q1656379": "ichinomiya",
    "Q134917533": "Ni-no-Miya",
    "Q134917303": "San-no-Miya",
    "Q134917307": "Shi-no-Miya",
    "Q134917301": "Go-no-Miya",
    "Q135009625": "Roku-no-Miya",
}

def shrine_designation_notes(qid: str) -> list:
    """Get shrine designations (sōja, ichinomiya, etc.) as {{ill|}} links for notes."""
    ent = get_entity_cached(qid)
    designations = []

    for p31 in ent["claims"].get("P31", []):
        p31_id = p31["mainsnak"]["datavalue"]["value"]["id"]
        if p31_id in SHRINE_DESIGNATION_MAP:
            desig_label = SHRINE_DESIGNATION_MAP[p31_id]
            desig_ent = get_entity_cached(p31_id)
            desig_name = _lbl(desig_ent, p31_id)
            ill_link = f"{{{{ill|{escape(desig_name)}|WD={p31_id}|lt={desig_label}}}}}"
            designations.append(ill_link)

    return designations

# ────────────────────────────────────────────────────────
#  Table builders
# ────────────────────────────────────────────────────────
_RED  = ' style="background-color:#ffdddd;"|'

def build_shrine_link(qid: str) -> str:
    """Build {{ill|}} link for shrine using P11250 (Miraheze article ID), en.wiki, or label."""
    ent = get_entity_cached(qid)

    # Try P11250 (Miraheze article ID)
    shrine_name = None
    for claim in ent["claims"].get("P11250", []):
        article_id = claim["mainsnak"]["datavalue"]["value"]
        if article_id.startswith("shinto:"):
            shrine_name = article_id[7:]  # Remove "shinto:" prefix
            break

    # Fall back to en.wiki sitelink
    if not shrine_name:
        sitelinks = ent.get("sitelinks", {})
        if "enwiki" in sitelinks:
            shrine_name = sitelinks["enwiki"]["title"]
        else:
            # Fall back to English label
            shrine_name = _lbl(ent, qid)

    # Build the ill template
    parts = [escape(shrine_name)]

    # Add interwikis (prioritize enwiki and jawiki, then others)
    sitelinks = ent.get("sitelinks", {})
    priority_order = ["enwiki", "jawiki"]
    other_langs = sorted([k for k in sitelinks.keys() if k not in priority_order])
    ordered_langs = [l for l in priority_order if l in sitelinks] + other_langs

    for lang_code in ordered_langs:
        lang = lang_code.replace("wiki", "")
        parts.append(lang)
        parts.append(escape(sitelinks[lang_code]["title"]))

    # Always add English label with lt= (for display consistency)
    en_label = ent.get("labels", {}).get("en", {}).get("value", "")
    if en_label:
        parts.insert(1, f"lt={escape(en_label)}")

    # Add WD link
    parts.append(f"WD={qid}")

    return "{{" + "ill|" + "|".join(parts) + "}}"

KANPEI_QID = "Q135160338"
KOKUHEI_QID = "Q135160342"

def get_designation(qid: str) -> str:
    """Get Kanpei-sha or Kokuhei-sha designation as ill link with custom lt= parameters."""
    ent = get_entity_cached(qid)
    for p31 in ent["claims"].get("P31", []):
        p31_id = p31["mainsnak"]["datavalue"]["value"]["id"]
        if p31_id == KANPEI_QID:
            desig_ent = get_entity_cached(KANPEI_QID)
            desig_name = _lbl(desig_ent, KANPEI_QID)
            return f"{{{{ill|{escape(desig_name)}|WD={KANPEI_QID}|lt=Kanpei}}}}"
        elif p31_id == KOKUHEI_QID:
            desig_ent = get_entity_cached(KOKUHEI_QID)
            desig_name = _lbl(desig_ent, KOKUHEI_QID)
            return f"{{{{ill|{escape(desig_name)}|WD={KOKUHEI_QID}|lt=Kokuhei}}}}"
    return "—"

CELEB_MAP = {
    "Q135009132": "Q135009132",  # Tsukinami-/Niiname-sai
    "Q135009152": "Q135009152",  # Hoe & Quiver
    "Q135009157": "Q135009157",  # Tsukinami-/Niiname-/Ainame-sai
    "Q135009205": "Q135009205",  # Hoe offering
    "Q135009221": "Q135009221",  # Quiver offering
}
SUBTYPE_MAP = {
    "Q135009975": "Keidai-Sessha", "Q135009973": "Keidai-sha",
    "Q135009904": "Sessha",        "Q135009974": "Keigai-sha",
    "Q135009977": "Keigai-Sessha", "Q135009978": "Keigai-Massha",
    "Q135009906": "Massha",        "Q135009899": "Betsu-gū",
    "Q11412524":  "Gōshi",
}

RANK_MAP = {
    "Q134917287": "Q134917287",  # Shosha
    "Q134917288": "Q134917288",  # Taisha
    "Q9610964": "Q9610964",      # (other rank)
}

def get_rank_link(rank_qid: str) -> str:
    """Get Shosha/Taisha rank as ill link."""
    if not rank_qid or rank_qid not in RANK_MAP:
        return "—"
    rank_ent = get_entity_cached(rank_qid)
    rank_name = _lbl(rank_ent, rank_qid)
    return f"{{{{ill|{escape(rank_name)}|WD={rank_qid}}}}}"

def get_celebration_link(celeb_qid: str) -> str:
    """Get celebration/festival QID as ill link with custom lt= parameters and inline footnote if needed."""
    if not celeb_qid or celeb_qid not in CELEB_MAP:
        return "—"

    # Custom display labels and inline footnotes for specific celebration QIDs
    celeb_labels = {
        "Q135009132": ("Tsukinami", "{{efn|gets offerings for the yearly {{ill|Niiname-no-Matsuri|en|Niiname-no-Matsuri|ja|新嘗祭|WD=Q11501518}} and the monthly {{ill|Tsukinami-no-Matsuri|simple|Tsukinami-no-Matsuri|ja|月次祭|WD=Q11516161}}.}}"),  # Tsukinami-/Niiname-sai
        "Q135009152": ("Hoe and Quiver", ""),      # Hoe & Quiver
        "Q135009157": ("Ainame", "{{efn|gets offerings for the {{ill|Ainame Festival|ja|相嘗祭|zh|相嘗祭|WD=Q11581944}} and the lower ranked {{ill|Tsukinami-no-Matsuri|simple|Tsukinami-no-Matsuri|ja|月次祭|WD=Q11516161}} and {{ill|Niiname-no-Matsuri|en|Niiname-no-Matsuri|ja|新嘗祭|WD=Q11501518}}.}}"),  # Tsukinami-/Niiname-/Ainame-sai
        "Q135009205": ("Hoe", ""),                  # Hoe offering
        "Q135009221": ("Quiver", ""),               # Quiver offering
    }

    celeb_ent = get_entity_cached(celeb_qid)
    celeb_name = _lbl(celeb_ent, celeb_qid)
    lt_param, footnote = celeb_labels.get(celeb_qid, ("", ""))

    if lt_param:
        link = f"{{{{ill|{escape(celeb_name)}|WD={celeb_qid}|lt={lt_param}}}}}"
    else:
        link = f"{{{{ill|{escape(celeb_name)}|WD={celeb_qid}}}}}"

    # Append footnote inline if it exists
    if footnote:
        link += footnote

    return link

def shrine_archive_url(qid: str) -> str | None:
    ent = get_entity_cached(qid)

    # First try P13677 (Kokugakuin University Digital Museum entry ID)
    for p13677 in ent["claims"].get("P13677", []):
        entry_id = p13677["mainsnak"]["datavalue"]["value"]
        return f"https://jmapps.ne.jp/kokugakuin/det.html?data_id={entry_id}"

    # Fallback to P1343 (described by) with P2699 (URL)
    KOKU = "Q135159299"
    for ref in ent["claims"].get("P1343", []):
        if ref["mainsnak"]["datavalue"]["value"]["id"] != KOKU:
            continue
        for q in ref.get("qualifiers", {}).get("P2699", []):
            return q["datavalue"]["value"]
    return None

def _dup_keys(rows, idx):
    seen, dups = set(), set()
    for r in rows:
        k = r[idx]
        if k in seen:
            dups.add(k)
        else:
            seen.add(k)
    return dups

def build_shiki_table(rows, token=None, dry=False, province=""):
    dup_qids = _dup_keys(rows, 6)
    hdr = ('{| class="wikitable sortable"\n'
           '! District !! Name !! Funding&nbsp;category '
           '!! Rank !! Notes !! Same&nbsp;as !! Co-ords !! Shrine&nbsp;DB')

    lines = [hdr]
    created_pages = {}  # Track created pages: {qid: actual_page_name}

    for _, prov, glob, name, kana, rank, q in rows:
        dup   = q in dup_qids
        style = _RED if dup else ''
        cell  = lambda txt: f'|{style} {txt}'.rstrip()

        url    = shrine_archive_url(q)
        dbcell = f'[{url} DB]' if url else '—'

        ent    = get_entity_cached(q)
        celeb_qid = next((c["mainsnak"]["datavalue"]["value"]["id"]
                          for c in ent["claims"].get("P31", [])
                          if c["mainsnak"]["datavalue"]["value"]["id"] in CELEB_MAP),
                         '—')
        celeb_link = get_celebration_link(celeb_qid)

        seats   = seat_quantity(q)
        dist    = district_name(q)
        desig   = get_designation(q)

        # Merge celebration into funding category
        if celeb_link != "—" and desig != "—":
            combined_desig = f"{desig} ({celeb_link})"
        elif celeb_link != "—":
            combined_desig = celeb_link
        else:
            combined_desig = desig

        rank_link = get_rank_link(rank)

        # Build Notes column with parent shrine, seats, and shrine designation info
        parents = parent_shrine_links(q)
        seats = seat_quantity(q)
        designations = shrine_designation_notes(q)
        notes_parts = []

        if parents != "—":
            notes_parts.append(f"part of {parents}")

        if seats != "single":
            notes_parts.append(seats)

        if designations:
            notes_parts.extend(designations)

        notes = ", ".join(notes_parts) if notes_parts else "—"

        same_as = same_as_links(q)
        coords  = coord_cell(q)

        # Process shrine page creation and track created pages
        actual_page_name = None
        if token and province:
            actual_page_name, status = determine_shrine_page_name(q, name, province, created_pages)

            if status not in ("SKIP", "SKIP_MATCHES"):
                # Build full table row with all columns using full interlanguage links
                shrine_link = build_shrine_link(q)
                table_content = (
                    "== Shikinaisha (式内社) ==\n"
                    '{| class="wikitable sortable"\n'
                    "! District !! Name !! Funding&nbsp;category !! Rank !! Notes !! Same&nbsp;as !! Co-ords !! Shrine&nbsp;DB\n"
                    "|-\n"
                    f"| {escape(dist)} || {shrine_link} || {escape(combined_desig)} || {escape(rank_link)} || {escape(notes)} || {escape(same_as)} || {escape(coords)} || {escape(dbcell)}\n"
                    "|}"
                )

                try:
                    create_shrine_page(q, name, province, actual_page_name, table_content, token, dry)
                    # Track this page as created
                    created_pages[q] = actual_page_name
                except Exception as e:
                    try:
                        print(f"ERROR creating shrine page for {name}: {e}")
                    except UnicodeEncodeError:
                        print(f"ERROR creating shrine page: {e}")

        # Build the shrine link for the list table - always use build_shrine_link for full interlanguage links
        link = build_shrine_link(q)

        lines += [
            '|-',
            cell(dist), cell(link),
            cell(combined_desig), cell(rank_link),
            cell(notes), cell(same_as), cell(coords), cell(dbcell)
        ]

        # Add secondary rows for same-as shrines with "RONSHA" district
        same_as_shrine_qids = same_as_qids(q)
        for same_as_q in same_as_shrine_qids:
            same_as_url = shrine_archive_url(same_as_q)
            same_as_dbcell = f'[{same_as_url} DB]' if same_as_url else '—'

            same_as_ent = get_entity_cached(same_as_q)
            same_as_celeb_qid = next((c["mainsnak"]["datavalue"]["value"]["id"]
                                      for c in same_as_ent["claims"].get("P31", [])
                                      if c["mainsnak"]["datavalue"]["value"]["id"] in CELEB_MAP),
                                     '—')
            same_as_celeb_link = get_celebration_link(same_as_celeb_qid)

            same_as_desig = get_designation(same_as_q)
            if same_as_celeb_link != "—" and same_as_desig != "—":
                same_as_combined_desig = f"{same_as_desig} ({same_as_celeb_link})"
            elif same_as_celeb_link != "—":
                same_as_combined_desig = same_as_celeb_link
            else:
                same_as_combined_desig = same_as_desig

            same_as_rank = next((r["mainsnak"]["datavalue"]["value"]["id"]
                                 for r in same_as_ent["claims"].get("P4075", [])), None)
            same_as_rank_link = get_rank_link(same_as_rank)

            same_as_parents = parent_shrine_links(same_as_q)
            same_as_seats = seat_quantity(same_as_q)
            same_as_designations = shrine_designation_notes(same_as_q)
            same_as_notes_parts = []

            if same_as_parents != "—":
                same_as_notes_parts.append(f"part of {same_as_parents}")

            if same_as_seats != "single":
                same_as_notes_parts.append(same_as_seats)

            if same_as_designations:
                same_as_notes_parts.extend(same_as_designations)

            same_as_notes = ", ".join(same_as_notes_parts) if same_as_notes_parts else "—"
            same_as_same_as = same_as_links(same_as_q)
            same_as_coords = coord_cell(same_as_q)

            # Process same-as shrine page creation and track created pages
            same_as_name = _lbl(same_as_ent, same_as_q)
            same_as_actual_page_name = None
            if token and province:
                same_as_actual_page_name, same_as_status = determine_shrine_page_name(same_as_q, same_as_name, province, created_pages)

                if same_as_status not in ("SKIP", "SKIP_MATCHES"):
                    # Build full table row with all columns (RONSHA district) using full interlanguage links
                    shrine_link = build_shrine_link(same_as_q)
                    table_content = (
                        "== Shikinaisha (式内社) ==\n"
                        '{| class="wikitable sortable"\n'
                        "! District !! Name !! Funding&nbsp;category !! Rank !! Notes !! Same&nbsp;as !! Co-ords !! Shrine&nbsp;DB\n"
                        "|-\n"
                        f"| RONSHA || {shrine_link} || {escape(same_as_combined_desig)} || {escape(same_as_rank_link)} || {escape(same_as_notes)} || {escape(same_as_same_as)} || {escape(same_as_coords)} || {escape(same_as_dbcell)}\n"
                        "|}"
                    )

                    try:
                        create_shrine_page(same_as_q, same_as_name, province, same_as_actual_page_name, table_content, token, dry)
                        # Track this page as created
                        created_pages[same_as_q] = same_as_actual_page_name
                    except Exception as e:
                        try:
                            print(f"ERROR creating shrine page for {same_as_name}: {e}")
                        except UnicodeEncodeError:
                            print(f"ERROR creating shrine page: {e}")

            # Build the shrine link for the list table - always use build_shrine_link for full interlanguage links
            same_as_link = build_shrine_link(same_as_q)

            lines += [
                '|-',
                cell('RONSHA'), cell(same_as_link),
                cell(same_as_combined_desig), cell(same_as_rank_link),
                cell(same_as_notes), cell(same_as_same_as), cell(same_as_coords), cell(same_as_dbcell)
            ]

    lines.append('|}')
    return '\n'.join(lines)

# ── Shikigeisha table (unchanged except label safety) ---------------
KOKUGAKUIN = "Q135159299"

def shikige_rows(ent):
    rows=[]
    for cl in ent["claims"].get("P3113", []):
        tgt = cl["mainsnak"]["datavalue"]["value"]["id"]
        sub = get_entity_cached(tgt)
        name = _lbl(sub)
        src_bits=[]
        for s in sub["claims"].get("P1343",[]):
            sid = s["mainsnak"]["datavalue"]["value"]["id"]
            if sid == KOKUGAKUIN: continue
            slabel = _lbl(get_entity_cached(sid), sid)
            ill = f"{{{{ill|{escape(slabel)}|WD={sid}}}}}"
            url = next((q["datavalue"]["value"]
                        for q in s.get("qualifiers",{}).get("P2699",[])), "")
            src_bits.append( ill + (f" : [ {url} archive ]" if url else "") )
        rows.append((name, tgt, "; ".join(src_bits) ))
    rows.sort(key=lambda x:x[0])
    return rows

def build_shikige_table(rows):
    if not rows:
        return "''(none listed)''"
    dup_names = _dup_keys(rows, 0)
    lines = ['{| class="wikitable sortable"',
             '! Name !! Historical source(s)']
    for name, q, src in rows:
        dup = name in dup_names
        style = _RED if dup else ''
        cell = lambda t: f'|{style} {t}'.rstrip()
        link = f"{{{{ill|{escape(name)}|WD={q}}}}}"
        lines += ['|-', cell(link), cell(src or '—')]
    lines.append('|}')
    return '\n'.join(lines)

# ────────────────────────────────────────────────────────
#  Page processing
# ────────────────────────────────────────────────────────
def ja_list_title(ent):
    sl = ent.get("sitelinks", {}).get("jawiki")
    return sl["title"] if sl else None

def build_interwiki_links(ent):
    """Build interwiki links from all sitelinks in the Wikidata item."""
    sitelinks = ent.get("sitelinks", {})
    links = []

    for lang_code in sorted(sitelinks.keys()):
        title = sitelinks[lang_code]["title"]
        # Convert language codes to MediaWiki format
        if lang_code == "enwiki":
            links.append(f"[[en:{title}]]")
        elif lang_code == "jawiki":
            links.append(f"[[ja:{title}]]")
        else:
            # For other languages, use the code without 'wiki' suffix
            lang = lang_code.replace("wiki", "")
            links.append(f"[[{lang}:{title}]]")

    return "\n".join(links) if links else ""

LEAD_TEMPLATE = (
    "{{{{afc comment|Wikidata entry [[d:{qid}]]\n\n"
    "[[:ja:{ja_title}]]\n\n~~~~}}}}\n"
    "This is a list of Shikinaisha in [[{prov}]]. That is the shrines in the "
    "[[Engishiki Jinmyōchō]] in the province.\n\n"
    "The Engishiki Jinmyōchō counts {tot} Shikinaisha in the province – "
    "{sho} Shikinai Shosha and {tai} Shikinai Taisha.\n\n"
)

def process(title, token, dry):
    src = wiki_get(title)
    # Support both [[d:Q...]] and [[da:d:Q...]] formats
    m = re.search(r"(?:\[\[d:|da:d:)(Q\d+)\]\]", src)
    if not m:
        return
    qid = m.group(1)

    ent              = get_entity_cached(qid)
    shiki_rows, cnt  = harvest_shiki(ent)
    prov             = title.split(" in ",1)[-1]
    shiki_tbl        = build_shiki_table(shiki_rows, token=token, dry=dry, province=prov)
    shikige_tbl      = build_shikige_table(shikige_rows(ent))

    foot_tmpl = re.search(r"{{translated page[^}]+}}", src, flags=re.I|re.S)
    foot      = foot_tmpl.group(0) if foot_tmpl else ""
    ja_title  = ja_list_title(ent) or prov + "の式内社一覧"

    interwiki_links = build_interwiki_links(ent)

    text = (
        LEAD_TEMPLATE.format(qid=qid, prov=prov, ja_title=ja_title,
                             tot=cnt["total"], sho=cnt["shosha"], tai=cnt["taisha"])
        + "== Shikinaisha (式内社) ==\n" + shiki_tbl + "\n\n"
        + "== Shikigeisha (式外社) ==\n"  + shikige_tbl + "\n\n"
        + "== References ==\n"
        + '<references group="lower-alpha"/>\n'
        + foot + "\n"
        + "{{List of Shikinaisha}}\n"
        + interwiki_links + "\n"
        + f"{{{{wikidata link|{qid}}}}}\n"
        + f"[[Category:Shikinaisha in {prov}]]\n"
        + "[[Category:Lists of Shikinaisha by location]]"
    )

    wiki_edit(title, text,
              "Bot: Update list and create individual shrine pages",
              token, dry)

# ────────────────────────────────────────────────────────
#  CLI
# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="preview only; don't save edits")
    args = ap.parse_args()

    csrf = wiki_login()

    # Get all pages in order
    all_pages = list(cat_members("Category:Lists_of_Shikinaisha_by_location"))
    print(f"[INFO] Found {len(all_pages)} total province lists")

    # Find Izumi Province index
    izumi_index = None
    for i, page in enumerate(all_pages):
        if "Izumi" in page:
            izumi_index = i
            print(f"[INFO] Found Izumi Province at index {i}: {page}")
            break

    if izumi_index is None:
        print("[ERROR] Could not find Izumi Province in category!")
        sys.exit(1)

    # Process from Izumi onwards
    for page in all_pages[izumi_index:]:
        # Skip if already processed
        if page in progress:
            print(f"[SKIP] {page} (already processed)")
            continue

        try:
            process(page, csrf, args.dry)
            # Record as successful
            progress[page] = True
            save_progress(progress)
        except Exception as e:
            try:
                print(f"ERROR {page}: {e}")
            except UnicodeEncodeError:
                print(f"ERROR [page with unicode title]: {e}")
        time.sleep(1.0)
