from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"

OFFICIAL = SOURCES / "official_seed.json"
FACTORY = SOURCES / "factory_seed.json"
SOCIAL = SOURCES / "social_candidates.json"

TAINAN_ATTRACTIONS_URL = "https://www.twtainan.net/data/attractions_zh-tw.json"


def read_json(path):
    if not path.exists():
        print(f"找不到：{path}")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("items", [])
            return items if isinstance(items, list) else []
        return []
    except Exception as e:
        print(f"讀取失敗 {path}: {e}")
        return []


def fetch_json(url):
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "YunJiaNanWeekend/1.9"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        return json.loads(text)
    except Exception as e:
        print(f"網路資料取得失敗：{url}")
        print(f"原因：{e}")
        return []


def collect_tainan_attractions():
    print("開始取得台南官方景點資料...")
    raw = fetch_json(TAINAN_ATTRACTIONS_URL)
    if not isinstance(raw, list):
        print("台南官方資料格式不是清單。")
        return []

    results = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue

        item_id = item.get("id", name)
        categories = item.get("category", [])
        if not isinstance(categories, list):
            categories = []
        category_text = " ".join(str(x) for x in categories)

        if "自然" in category_text:
            tags = ["戶外", "自然"]
        elif "文化" in category_text:
            tags = ["文化"]
        else:
            tags = ["親子"]

        district = str(item.get("district", "")).strip()
        address = str(item.get("address", "")).strip()
        summary = str(item.get("summary", "")).strip()
        update_time = str(item.get("update_time", "")).strip()

        results.append({
            "id": f"tainan-attraction-{item_id}",
            "city": "台南",
            "name": name,
            "e": "📍",
            "type": "景點",
            "src": "官方",
            "base_heat": 70,
            "updated": update_time[:10],
            "tags": tags,
            "place": district,
            "q": address or name,
            "why": summary[:120],
            "url": "https://www.twtainan.net/",
        })

    print(f"台南官方景點取得完成：{len(results)} 筆")
    return results


def normalize(item, source_type):
    if not isinstance(item, dict):
        return None
    result = dict(item)
    if not result.get("name") or not result.get("city"):
        return None

    if not result.get("src"):
        result["src"] = "官方" if source_type == "official" else "社群"
    if not result.get("type"):
        result["type"] = "景點"
    if not result.get("e"):
        result["e"] = "🏭" if result["type"] == "觀光工廠" else "📍"
    if not isinstance(result.get("tags"), list):
        result["tags"] = []
    if not result.get("updated"):
        result["updated"] = datetime.now().astimezone().date().isoformat()

    return result


def dedupe(items):
    """依 id 優先去重；沒有 id 時以 city+name 去重。後面的資料覆蓋前面的資料。"""
    unique = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("id", "")).strip()
        if not key:
            key = f'{item.get("city", "")}|{item.get("name", "")}'.strip().lower()
        if key:
            unique[key] = item
    return list(unique.values())


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalized_file(path, source_type):
    results = []
    for item in read_json(path):
        normalized = normalize(item, source_type)
        if normalized:
            results.append(normalized)
    return results


def main():
    print("=" * 50)
    print("雲嘉南週末去哪玩 - 自動資料蒐集 V1.9")
    print("=" * 50)

    # 關鍵修正：
    # official_seed.json 可能已包含前幾週自動寫入的台南景點。
    # 先排除 tainan-attraction-*，避免每週累積重複資料。
    official_local = [
        x for x in normalized_file(OFFICIAL, "official")
        if not str(x.get("id", "")).startswith("tainan-attraction-")
    ]

    factory_local = normalized_file(FACTORY, "official")
    social_local = normalized_file(SOCIAL, "social")

    tainan_online = []
    for item in collect_tainan_attractions():
        normalized = normalize(item, "official")
        if normalized:
            tainan_online.append(normalized)

    official = dedupe(official_local + factory_local + tainan_online)
    social = dedupe(social_local)

    print("")
    print("資料蒐集結果：")
    print(f"原有官方資料：{len(official_local)} 筆")
    print(f"觀光工廠資料：{len(factory_local)} 筆")
    print(f"台南網路景點：{len(tainan_online)} 筆")
    print(f"官方資料去重後：{len(official)} 筆")
    print(f"社群資料去重後：{len(social)} 筆")

    save_json(OFFICIAL, official)
    save_json(SOCIAL, social)

    print("")
    print("資料已寫入 sources/")
    print("collect_sources.py V1.9 完成")


if __name__ == "__main__":
    main()
