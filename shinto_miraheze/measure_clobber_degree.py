#!/usr/bin/env python3
"""One-off: measure the DEGREE of every git-synced clobber (Emma, 2026-06-08).
Read-only. For every 'overwriting divergent wiki edit' event across all
git-synced pages, diff the overwritten (parent) revision vs the clobber revision
and count lines removed (= content the sync deleted off the wiki) and added.
Classifies by prior editor (human vs bot) so we can tell real loss from churn."""
import requests, io, sys, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
UA="ClobberDegree/1.0 (User:EmmaBot; shinto.miraheze.org)"; API="https://shinto.miraheze.org/w/api.php"
S=requests.Session(); S.headers.update({"User-Agent":UA}); BOT={"EmmaBot"}; MARK="overwriting divergent wiki edit"
def jget(**p):
    for _ in range(4):
        r=S.get(API,params=p,timeout=60)
        if r.status_code==429: time.sleep(8); continue
        try: return r.json()
        except Exception: time.sleep(2)
    return {}
pages=[]; cont={}
while True:
    p=dict(action="query",list="categorymembers",cmtitle="Category:Git synced pages",cmtype="page",cmlimit="500",format="json",formatversion="2"); p.update(cont)
    d=jget(**p); pages+=[m["title"] for m in d.get("query",{}).get("categorymembers",[])]
    if "continue" not in d: break
    cont=d["continue"]; time.sleep(0.2)
events=[]  # (title, prior_user, parent_revid, clobber_revid)
for title in pages:
    revs=[]; cont={}
    while True:
        p=dict(action="query",prop="revisions",titles=title,rvprop="ids|user|comment",rvlimit="500",format="json",formatversion="2"); p.update(cont)
        d=jget(**p); revs+=d.get("query",{}).get("pages",[{}])[0].get("revisions",[])
        if "continue" not in d: break
        cont=d["continue"]; time.sleep(0.15)
    for j,rv in enumerate(revs):
        if rv.get("user") in BOT and MARK in (rv.get("comment") or "") and j+1<len(revs):
            events.append((title, revs[j+1].get("user"), revs[j+1]["revid"], rv["revid"]))
    time.sleep(0.1)
# batch fetch content
need=set()
for _,_,par,clob in events: need.add(par); need.add(clob)
content={}
need=list(need)
for i in range(0,len(need),50):
    d=jget(action="query",revids="|".join(map(str,need[i:i+50])),prop="revisions",rvprop="ids|content",rvslots="main",format="json",formatversion="2")
    for pg in d.get("query",{}).get("pages",[]):
        for rv in pg.get("revisions",[]):
            content[rv["revid"]]=rv.get("slots",{}).get("main",{}).get("content","")
    time.sleep(0.3)
rows=[]
for title,prior,par,clob in events:
    a=set((content.get(par,"") or "").splitlines()); b=set((content.get(clob,"") or "").splitlines())
    removed=len(a-b); added=len(b-a)
    rows.append({"title":title,"prior":prior,"removed_lines":removed,"added_lines":added})
human=[r for r in rows if r["prior"] not in BOT]
bot=[r for r in rows if r["prior"] in BOT]
def summ(rs): 
    rm=sorted((r["removed_lines"] for r in rs),reverse=True); return f"n={len(rs)} total_removed={sum(r['removed_lines'] for r in rs)} max_removed={rm[0] if rm else 0} zero_change={sum(1 for r in rs if r['removed_lines']==0 and r['added_lines']==0)}"
print("=== DEGREE OF CLOBBERING ===")
print("HUMAN-overwritten:", summ(human))
print("BOT-overwritten:  ", summ(bot))
print("\nTop 12 by removed lines:")
for r in sorted(rows,key=lambda x:-x["removed_lines"])[:12]:
    print(f"  -{r['removed_lines']:4} +{r['added_lines']:4}  [{r['prior']}]  {r['title'][:50]}")
json.dump(rows,open("shinto_miraheze/measure_clobber_degree.out.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
print("\nwrote shinto_miraheze/measure_clobber_degree.out.json ; events:",len(events))
