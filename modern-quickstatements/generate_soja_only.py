"""One-off: generate just the Sōja (Q1107129) migration files locally."""
import io
import sys
import json
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
H = {"User-Agent": UA, "Accept": "application/sparql-results+json"}

VALUE = "Q1107129"        # sōja
DETERMINED_BY = "Q742460"  # ritsuryō
SRC_PROP = "P31"


def qid(uri):
    return uri.split("/")[-1]


def snak_to_qs(snak):
    if snak.get("snaktype") != "value":
        return {"novalue": "novalue", "somevalue": "somevalue"}.get(snak.get("snaktype"))
    dv = snak["datavalue"]
    t = dv["type"]
    v = dv["value"]
    if t == "wikibase-entityid":
        return v["id"]
    if t == "string":
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if t == "time":
        return f'{v["time"]}/{v["precision"]}'
    if t == "quantity":
        amt = v["amount"]
        unit = v.get("unit", "")
        if unit and "entity/" in unit:
            return f'{amt}U{unit.split("/")[-1]}'
        return str(amt)
    if t == "monolingualtext":
        return f'{v["language"]}:"{v["text"]}"'
    if t == "globecoordinate":
        return f'@{v["latitude"]}/{v["longitude"]}'
    return None


print("Fetching items with P31=Q1107129 needing migration...")
remaining_query = f"""
SELECT ?item WHERE {{
  ?item p:{SRC_PROP} ?stmt .
  ?stmt ps:{SRC_PROP} wd:{VALUE} .
  MINUS {{
    ?item p:P13723 ?s2 .
    ?s2 ps:P13723 wd:{VALUE} .
  }}
}}
ORDER BY ?item
"""
r = requests.get(SPARQL, params={"query": remaining_query, "format": "json"}, headers=H, timeout=90)
r.raise_for_status()
items_need_add = [qid(b["item"]["value"]) for b in r.json()["results"]["bindings"]]
print(f"  {len(items_need_add)} items need P13723 added")

time.sleep(10)
print("Fetching items safe to remove old P31=Q1107129...")
safe_remove_query = f"""
SELECT ?item WHERE {{
  ?item p:{SRC_PROP} ?stmt .
  ?stmt ps:{SRC_PROP} wd:{VALUE} .
  ?item p:P13723 ?s2 .
  ?s2 ps:P13723 wd:{VALUE} .
}}
ORDER BY ?item
"""
r = requests.get(SPARQL, params={"query": safe_remove_query, "format": "json"}, headers=H, timeout=90)
r.raise_for_status()
items_safe_remove = [qid(b["item"]["value"]) for b in r.json()["results"]["bindings"]]
print(f"  {len(items_safe_remove)} items safe to remove old {SRC_PROP}")


def fetch_batch(ids, props):
    out = {}
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        r = requests.get(API, params={
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": props,
            "format": "json",
        }, headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        out.update(r.json().get("entities", {}))
        if i + 50 < len(ids):
            time.sleep(1.5)
    return out


# jawiki sitelinks for references
print("Fetching jawiki sitelinks for references...")
sitelink_entities = fetch_batch(items_need_add, "sitelinks") if items_need_add else {}
item_refs = {}
for eid, entity in sitelink_entities.items():
    ja = entity.get("sitelinks", {}).get("jawiki", {})
    if ja:
        title = ja["title"].replace(" ", "_")
        url = f"https://ja.wikipedia.org/wiki/{title}"
        item_refs[eid] = ["S4656", f'"{url}"']
print(f"  Found jawiki for {len(item_refs)}/{len(items_need_add)}")

# Fetch full claims for items needing add (to preserve qualifiers + refs)
print("Fetching P31 claim details...")
claim_entities = fetch_batch(items_need_add, "claims") if items_need_add else {}


def claim_to_lines(item_id, claim, override_ref):
    mv = snak_to_qs(claim["mainsnak"])
    if not mv:
        return []
    parts = [item_id, "P13723", mv, "P459", DETERMINED_BY]
    qs = claim.get("qualifiers", {})
    qorder = claim.get("qualifiers-order", list(qs.keys()))
    for p in qorder:
        for sn in qs.get(p, []):
            v = snak_to_qs(sn)
            if v is not None:
                parts.extend([p, v])
    if override_ref is not None:
        parts.extend(override_ref)
        return ["|".join(parts)]
    refs = claim.get("references", [])
    if refs:
        ref = refs[0]
        ro = ref.get("snaks-order", list(ref.get("snaks", {}).keys()))
        for p in ro:
            for sn in ref["snaks"].get(p, []):
                v = snak_to_qs(sn)
                if v is not None:
                    parts.extend([f"S{p[1:]}", v])
    lines = ["|".join(parts)]
    for ref in refs[1:]:
        rp = [item_id, "P13723", mv]
        ro = ref.get("snaks-order", list(ref.get("snaks", {}).keys()))
        has = False
        for p in ro:
            for sn in ref["snaks"].get(p, []):
                v = snak_to_qs(sn)
                if v is not None:
                    rp.extend([f"S{p[1:]}", v])
                    has = True
        if has:
            lines.append("|".join(rp))
    return lines


add_lines = []
for item_id in items_need_add:
    entity = claim_entities.get(item_id, {})
    claims = entity.get("claims", {}).get(SRC_PROP, [])
    override = item_refs.get(item_id)
    for claim in claims:
        mv = snak_to_qs(claim.get("mainsnak", {}))
        if mv != VALUE:
            continue
        add_lines.extend(claim_to_lines(item_id, claim, override))

with open("migrate_soja_add.txt", "w", encoding="utf-8") as f:
    for l in add_lines:
        f.write(l + "\n")
print(f"Wrote {len(add_lines)} lines to migrate_soja_add.txt")

remove_lines = [f"-{iid}|{SRC_PROP}|{VALUE}" for iid in items_safe_remove]
with open("migrate_soja_remove.txt", "w", encoding="utf-8") as f:
    for l in remove_lines:
        f.write(l + "\n")
print(f"Wrote {len(remove_lines)} lines to migrate_soja_remove.txt")
