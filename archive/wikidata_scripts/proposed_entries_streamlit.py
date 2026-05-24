import os
import time
import re
from typing import Any, Dict, List, Set

import pandas as pd
import requests
import streamlit as st
import mwclient
import mwparserfromhell as mwp
from pymongo import MongoClient

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG – adjust creds / URIs if needed
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_URI = "mongodb://localhost:27017"
DB_NAME = "shinto_label_review"
COLL_PROP = "proposed_labels"   # items have QID but no en‑label
COLL_MISS = "missing_ills"      # no Wikidata item yet

WD_USER = "EmmaBot@EmmaBotMisc"
WD_PASS = "030akvvhf8b3f6fg7mpt85fo8rvp6d58"  # BotPassword

SW_USER = "EmmaBot"
SW_PASS = "[REDACTED_SECRET_1]"

WD_API = "https://www.wikidata.org/w/api.php"
UA = "ShintoLabelDashboard/0.7 (User:EmmaBot)"
PAUSE = 0.5   # seconds between ShintoWiki edits

DEL_COL = "✅ Delete"
CREATE_COL = "🆕 Create QID"

# ──────────────────────────────────────────────────────────────────────────────
# Mongo helpers
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def mongo_client(uri: str = DEFAULT_URI) -> MongoClient:
    return MongoClient(uri)

@st.cache_data(show_spinner=False)
def fetch_docs(coll: str, filters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    return list(mongo_client()[DB_NAME][coll].find(filters or {}, projection={"_id": False}))

def delete_many(coll: str, db_field: str, values: List[str]) -> int:
    res = mongo_client()[DB_NAME][coll].delete_many({db_field: {"$in": values}})
    return res.deleted_count

def mark_created(ja_label: str, qid: str) -> None:
    mongo_client()[DB_NAME][COLL_MISS].update_one({"ja": ja_label}, {"$set": {"qid": qid}})

# ──────────────────────────────────────────────────────────────────────────────
# Wikidata helpers
# ──────────────────────────────────────────────────────────────────────────────

def wd_login() -> tuple[requests.Session, str]:
    sess = requests.Session(); sess.headers.update({"User-Agent": UA})
    lg_token = sess.get(WD_API, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}, timeout=60).json()["query"]["tokens"]["logintoken"]
    login_out = sess.post(WD_API, data={"action": "login", "lgname": WD_USER, "lgpassword": WD_PASS, "lgtoken": lg_token, "format": "json"}, timeout=60).json()
    if login_out.get("login", {}).get("result") != "Success":
        raise RuntimeError(f"Wikidata login failed: {login_out}")
    csrf = sess.get(WD_API, params={"action": "query", "meta": "tokens", "format": "json"}, timeout=60).json()["query"]["tokens"]["csrftoken"]
    return sess, csrf

def request_json(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

def wd_create_item(sess: requests.Session, csrf: str, labels_by_lang: Dict[str, List[str]], summary: str) -> str:
    """Create a new item with labels + aliases for every language present."""
    data: Dict[str, Any] = {"labels": {}, "aliases": {}}
    for lang, variants in labels_by_lang.items():
        if not variants:
            continue
        data["labels"][lang] = {"language": lang, "value": variants[0]}
        if len(variants) > 1:
            data["aliases"][lang] = [{"language": lang, "value": v} for v in variants[1:]]

    out = sess.post(
        WD_API,
        data={
            "action": "wbeditentity",
            "new": "item",
            "data": request_json(data),
            "token": csrf,
            "bot": 1,
            "summary": summary,
            "format": "json",
        },
        timeout=60,
    ).json()
    if out.get("success") != 1:
        raise RuntimeError(out)
    return out["entity"]["id"]

# ──────────────────────────────────────────────────────────────────────────────
# ShintoWiki helpers
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def sw_site():
    site = mwclient.Site("shinto.miraheze.org", path="/w/")
    site.login(SW_USER, SW_PASS)
    return site

def patch_ill(tpl: mwp.nodes.template.Template, qid: str) -> bool:
    """Append or update |qid=Qxxx. Returns True if template changed."""
    for p in tpl.params:
        if p.showkey and str(p.name).strip().lower() == "qid":
            if str(p.value).strip() == qid:
                return False
            p.value = qid; return True
    tpl.params.append(mwp.nodes.template.Parameter(name="qid", value=qid, showkey=True))
    return True

def _extract_ja_label(tpl: mwp.nodes.template.Template) -> str | None:
    """Return the ja label inside a {{ill}} template, regardless of param order."""
    if tpl.has("ja"):
        return str(tpl.get("ja").value).strip()
    parts: List[str] = []
    numbered: Dict[int, str] = {}
    for p in tpl.params:
        if p.showkey:
            key = str(p.name).strip()
            if key.isdigit():
                numbered[int(key)] = str(p.value).strip()
        else:
            parts.append(str(p.value).strip())
    for idx, val in numbered.items():
        while len(parts) < idx:
            parts.append("")
        parts[idx - 1] = val
    i = 0
    while i < len(parts) - 1:
        if parts[i].lower() == "ja":
            return parts[i + 1]
        i += 1
    return None

def update_pages_with_qid(ja_label: str, qid: str, pages: Set[str]) -> None:
    """Insert |qid=<qid> into every {{ill}} with the given ja label.
    Falls back to regex when mwparserfromhell cannot rewrite the template."""
    site = sw_site()
    for title in pages:
        pg = site.pages[title]
        if not pg.exists:
            continue
        original_text = pg.text()
        code = mwp.parse(original_text)
        changed_structured = False

        for tpl in code.filter_templates(recursive=True):
            if tpl.name.strip().lower() != "ill":
                continue
            if _extract_ja_label(tpl) == ja_label:
                if patch_ill(tpl, qid):
                    changed_structured = True

        if changed_structured:
            pg.save(str(code), summary=f"Bot: add |qid={qid} in {{ill}}", minor=True)
            time.sleep(PAUSE)
            continue

        # regex fallback for odd cases
        def add_qid_match(match: re.Match) -> str:
            chunk = match.group(1)
            if "|qid=" in chunk.lower():
                return match.group(0)  # already has qid
            return chunk + f"|qid={qid}" + match.group(2)

        pattern = re.compile(r"(\{\{\s*ill[^{}]*?" + re.escape(ja_label) + r"[^{}]*?)(\}\})", re.IGNORECASE | re.DOTALL)
        new_text, n_sub = pattern.subn(add_qid_match, original_text)
        if n_sub:
            pg.save(new_text, summary=f"Bot: add |qid={qid} in {{ill}} (regex)", minor=True)
            time.sleep(PAUSE)

# ──────────────────────────────────────────────────────────────────────────────
# Data‑frame helpers
# ──────────────────────────────────────────────────────────────────────────────

def df_for_coll(coll: str, docs: List[Dict[str, Any]]) -> pd.DataFrame:
    if coll == COLL_PROP:
        return pd.DataFrame([(d["qid"], d["proposed_label"]) for d in docs], columns=["QID", "Proposed English Label"])
    rows = []
    for d in docs:
        labels = d.get("labels", {})
        rows.append({
            "JA label": d.get("ja", ""),
            "EN variants": ", ".join(labels.get("en", [])),
            "Languages": ", ".join(sorted(labels.keys())),
            "Occurrences": len(d.get("occurrences", [])),
        })
    return pd.DataFrame(rows)

# ──────────────────────────────────────────────────────────────────────────────
# Streamlit UI


# ──────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="ShintoWiki label dashboard", layout="wide")
st.title("ShintoWiki label review & cleanup tool")

uri = st.sidebar.text_input("Mongo URI", os.getenv("MONGO_URI", DEFAULT_URI))
if uri != DEFAULT_URI:
    mongo_client.clear(); fetch_docs.clear()
DEFAULT_URI = uri

collection = st.sidebar.selectbox("Collection", [COLL_PROP, COLL_MISS], format_func=lambda c: "Proposed English labels" if c == COLL_PROP else "ILLs with no Wikidata item")

text_filter = st.sidebar.text_input("Contains text …")
filters: Dict[str, Any] = {}
if text_filter:
    regex = {"$regex": text_filter, "$options": "i"}
    if collection == COLL_PROP:
        filters["$or"] = [{"qid": regex}, {"proposed_label": regex}]
    else:
        filters["$or"] = [{"ja": regex}, {"labels.en": regex}, {"labels": regex}]

raw_docs = fetch_docs(collection, filters)
show_df = df_for_coll(collection, raw_docs)

show_df[DEL_COL] = False
if collection == COLL_MISS:
    show_df[CREATE_COL] = False

st.subheader("Tick rows, then choose an action")
col_cfg = {DEL_COL: st.column_config.CheckboxColumn(required=False)}
if collection == COLL_MISS:
    col_cfg[CREATE_COL] = st.column_config.CheckboxColumn(required=False)

edited = st.data_editor(
    show_df,
    key="editor",
    use_container_width=True,
    column_config=col_cfg,
    disabled=[c for c in show_df.columns if c not in (DEL_COL, CREATE_COL)],
    hide_index=True,
)

rows_del = edited[edited[DEL_COL]]
rows_cr = edited[edited[CREATE_COL]] if collection == COLL_MISS else pd.DataFrame()

# Delete ---------------------------------------------------------------------
if not rows_del.empty and st.button("🚮 Apply deletions", type="secondary"):
    id_col, db_field = ("QID", "qid") if collection == COLL_PROP else ("JA label", "ja")
    n_deleted = delete_many(collection, db_field, rows_del[id_col].tolist())
    st.success(f"Deleted {n_deleted} document(s).")
    fetch_docs.clear(); st.rerun()

# Create ---------------------------------------------------------------------
if collection == COLL_MISS and not rows_cr.empty and st.button("🆕 Create Wikidata items", type="primary"):
    try:
        sess, csrf = wd_login()
    except RuntimeError as e:
        st.error(str(e)); st.stop()

    created: Dict[str, str] = {}

    for _, row in rows_cr.iterrows():
        ja_label = row["JA label"]
        doc = next((d for d in raw_docs if d.get("ja") == ja_label), None)
        if doc is None:
            st.warning(f"Could not find doc for {ja_label}. Skipping…"); continue

        labels_by_lang: Dict[str, List[str]] = doc.get("labels", {})
        # pick first English as main for summary display
        en_variants = labels_by_lang.get("en", [])
        en_main = en_variants[0] if en_variants else None

        occ = doc.get("occurrences", [{}])[0]
        jp_src = occ.get("translated_from", "?")
        en_page = occ.get("page", "?")
        summary = f"Created item for red‑link present on {jp_src}, {en_page} – '{ja_label}' / '{en_main or ''}'"

        try:
            qid = wd_create_item(sess, csrf, labels_by_lang, summary)
        except Exception as e:
            st.error(f"Failed to create item for {ja_label}: {e}"); continue

        pages_set = {o.get("page") for o in doc.get("occurrences", []) if o.get("page")}
        try:
            update_pages_with_qid(ja_label, qid, pages_set)
            mark_created(ja_label, qid)
            created[ja_label] = qid
        except Exception as e:
            st.error(f"Created {qid} but failed to update pages: {e}"); continue

        time.sleep(PAUSE)

    if created:
        st.success("Created " + ", ".join(created.values()))
    else:
        st.info("No items created.")
    fetch_docs.clear(); st.rerun()
