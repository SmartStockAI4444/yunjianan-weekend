from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).resolve().parent
S = ROOT / "sources"
OUT = ROOT / "weekly_feed.json"

def read(p):
    return json.loads(p.read_text(encoding="utf-8"))

def heat(sig):
    r = min(int(sig.get("recent_mentions", 0)), 20)
    c = min(int(sig.get("creator_mentions", 0)), 10)
    p = min(int(sig.get("repeat_recommendations", 0)), 10)
    return max(0, min(100, round(55 + r * 1.2 + c * 1.6 + p)))

def expired(x, today):
    if x.get("type") != "活動" or not x.get("end"):
        return False
    try:
        return date.fromisoformat(x["end"]) < today
    except Exception:
        return False

def norm(x):
    y = dict(x)
    if "heat" not in y:
        y["heat"] = heat(y.get("signals", {})) if y.get("src") == "社群" else int(y.get("base_heat", 75))
    y.pop("base_heat", None)
    y["sources"] = [y.get("src")] if y.get("src") else []
    return y

def key(x):
    s = (
        x.get("city", "")
        + "|"
        + x.get("name", "")
        + "|"
        + x.get("start", "")
    ).replace(" ", "").lower()
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def merge_unique(a, b):
    out = []
    for v in list(a or []) + list(b or []):
        if v and v not in out:
            out.append(v)
    return out

today = date.today()

official = [norm(i) for i in read(S / "official_seed.json")]
social = [norm(i) for i in read(S / "social_candidates.json")]

merged = {}
order = []

for x in official + social:
    k = key(x)

    if k not in merged:
        merged[k] = x
        order.append(k)
        continue

    cur = merged[k]
    cur["sources"] = merge_unique(cur.get("sources"), x.get("sources"))
    cur["tags"] = merge_unique(cur.get("tags"), x.get("tags"))

    # 同一景點若同時存在官方與社群資料：
    # 只保留一張卡片，但保存社群熱門訊號。
    if x.get("src") == "社群":
        sig = x.get("signals", {})
        social_heat = heat(sig)

        cur["signals"] = sig
        cur["social_heat"] = social_heat
        cur["heat"] = max(int(cur.get("heat", 0)), social_heat)
        cur["social_updated"] = x.get("updated", "")
        cur["social_why"] = x.get("why", "")
        cur["social_url"] = x.get("url", "")

        if x.get("updated", "") > cur.get("updated", ""):
            cur["updated"] = x.get("updated", "")

items = []
expired_removed = 0

for k in order:
    x = merged[k]

    if expired(x, today):
        expired_removed += 1
        continue

    items.append(x)

items.sort(
    key=lambda x: (
        0 if "官方" in x.get("sources", []) else 1,
        -int(x.get("heat", 0)),
        x.get("city", ""),
        x.get("name", ""),
    )
)

feed = {
    "version": today.strftime("%Y.%m.%d") + "-auto",
    "updated": today.isoformat(),
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "stats": {
        "official": sum(1 for x in items if "官方" in x.get("sources", [])),
        "social": sum(1 for x in items if "社群" in x.get("sources", [])),
        "expired_removed": expired_removed,
        "total": len(items),
    },
    "items": items,
}

OUT.write_text(
    json.dumps(feed, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("generated", len(items), "items")
print(
    "official",
    feed["stats"]["official"],
    "social",
    feed["stats"]["social"],
)
