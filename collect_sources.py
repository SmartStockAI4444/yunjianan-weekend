from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"

OFFICIAL = SOURCES / "official_seed.json"
SOCIAL = SOURCES / "social_candidates.json"
TAINAN_ATTRACTIONS_URL = "https://www.twtainan.net/data/attractions_zh-tw.json"

def read_json(path):
    def fetch_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "YunJiaNanWeekend/1.0"
            }
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text)

    except Exception as e:
        print(f"網路資料取得失敗：{url}")
        print(e)
        return []
      def collect_tainan_attractions():
    raw = fetch_json(TAINAN_ATTRACTIONS_URL)

    if not isinstance(raw, list):
        return []

    results = []

    for item in raw:
        name = str(item.get("name", "")).strip()

        if not name:
            continue

        categories = item.get("category", [])
        if not isinstance(categories, list):
            categories = []

        results.append({
            "id": f"tainan-attraction-{item.get('id', name)}",
            "city": "台南",
            "name": name,
            "e": "📍",
            "type": "景點",
            "src": "官方",
            "base_heat": 70,
            "updated": str(item.get("update_time", ""))[:10],
            "tags": ["戶外"] if "自然景觀" in categories else ["親子"],
            "place": str(item.get("district", "")),
            "q": str(item.get("address", "")) or name,
            "why": str(item.get("summary", ""))[:120],
            "url": "https://www.twtainan.net/"
        })

    print(f"台南官方景點：{len(results)} 筆")
    return results  
    if not path.exists():
        print(f"找不到：{path}")
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("items", [])
    except Exception as e:
        print(f"讀取失敗 {path}: {e}")
        return []


def normalize(item, source_type):
    x = dict(item)

    x.setdefault("city", "")
    x.setdefault("name", "")
    x.setdefault("type", "景點")
    x.setdefault("url", "")
    x.setdefault("start_date", "")
    x.setdefault("end_date", "")
    x.setdefault("description", "")
    x.setdefault("signals", {})

    x["source_type"] = source_type
    x["collected_at"] = datetime.now().astimezone().isoformat()

    return x


def unique(items):
    result = []
    seen = set()

    for x in items:
        key = (
            str(x.get("city", "")).strip(),
            str(x.get("name", "")).strip(),
            str(x.get("start_date", "")).strip(),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(x)

    return result


def main():
    official_local = [
    normalize(x, "official")
    for x in read_json(OFFICIAL)
]

tainan_online = [
    normalize(x, "official")
    for x in collect_tainan_attractions()
]

official = official_local + tainan_online

    social = [
        normalize(x, "social")
        for x in read_json(SOCIAL)
    ]

    items = unique(official + social)

    print("=== 雲嘉南資料蒐集完成 ===")
    print(f"官方資料：{len(official)}")
    print(f"社群候選：{len(social)}")
    print(f"去重後：{len(items)}")


if __name__ == "__main__":
    main()
