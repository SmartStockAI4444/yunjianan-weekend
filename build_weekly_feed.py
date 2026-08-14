from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import date, datetime

ROOT=Path(__file__).resolve().parent
S=ROOT/"sources"
OUT=ROOT/"weekly_feed.json"

def read(p): return json.loads(p.read_text(encoding="utf-8"))

def heat(sig):
    r=min(int(sig.get("recent_mentions",0)),20)
    c=min(int(sig.get("creator_mentions",0)),10)
    p=min(int(sig.get("repeat_recommendations",0)),10)
    return max(0,min(100,round(55+r*1.2+c*1.6+p)))

def expired(x,today):
    if x.get("type")!="活動" or not x.get("end"): return False
    try: return date.fromisoformat(x["end"]) < today
    except: return False

def norm(x):
    y=dict(x)
    if "heat" not in y:
        y["heat"]=heat(y.get("signals",{})) if y.get("src")=="社群" else int(y.get("base_heat",75))
    y.pop("base_heat",None)
    return y

def key(x):
    s=(x.get("city","")+"|"+x.get("name","")+"|"+x.get("start","")).replace(" ","").lower()
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

today=date.today()
items=[]
seen=set()
expired_removed=0
for x in [norm(i) for i in read(S/"official_seed.json")+read(S/"social_candidates.json")]:
    k=key(x)
    if k in seen: continue
    seen.add(k)
    if expired(x,today):
        expired_removed+=1
        continue
    items.append(x)

items.sort(key=lambda x:(0 if x.get("src")=="官方" else 1,-int(x.get("heat",0)),x.get("city",""),x.get("name","")))
feed={
 "version":today.strftime("%Y.%m.%d")+"-auto",
 "updated":today.isoformat(),
 "generated_at":datetime.now().astimezone().isoformat(timespec="seconds"),
 "stats":{
   "official":sum(1 for x in items if x.get("src")=="官方"),
   "social":sum(1 for x in items if x.get("src")=="社群"),
   "expired_removed":expired_removed,
   "total":len(items)
 },
 "items":items
}
OUT.write_text(json.dumps(feed,ensure_ascii=False,indent=2),encoding="utf-8")
print("generated",len(items),"items")
