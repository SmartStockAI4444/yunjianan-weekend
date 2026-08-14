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

TAINAN_ATTRACTIONS_URL = (
    "https://www.twtainan.net/data/attractions_zh-tw.json"
)


def read_json(path):
    if not path.exists():
        print(f"找不到：{path}")
        return []

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        if isinstance(data, list):
            return data

        return []

    except Exception as e:
        print(f"讀取失敗 {path}: {e}")
        return []


def fetch_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "YunJiaNanWeekend/1.0"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            text = response.read().decode("utf-8")
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

        name = str(
            item.get("name", "")
        ).strip()

        if not name:
            continue

        item_id = item.get("id", name)

        categories = item.get(
            "category",
            [],
        )

        if not isinstance(categories, list):
            categories = []

        category_text = " ".join(
            str(x) for x in categories
        )

        if "自然" in category_text:
            tags = ["戶外", "自然"]
        elif "文化" in category_text:
            tags = ["文化"]
        else:
            tags = ["親子"]

        district = str(
            item.get("district", "")
        ).strip()

        address = str(
            item.get("address", "")
        ).strip()

        summary = str(
            item.get("summary", "")
        ).strip()

        update_time = str(
            item.get("update_time", "")
        ).strip()

        result = {
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
        }

        results.append(result)

    print(
        f"台南官方景點取得完成：{len(results)} 筆"
    )

    return results


def normalize(item, source_type):
    if not isinstance(item, dict):
        return None

    result = dict(item)

    if not result.get("name"):
        return None

    if not result.get("city"):
        return None

    if not result.get("src"):
        if source_type == "official":
            result["src"] = "官方"
        else:
            result["src"] = "社群"

    if not result.get("type"):
        result["type"] = "景點"

    if not result.get("e"):
        result["e"] = "📍"

    if not isinstance(
        result.get("tags"),
        list,
    ):
        result["tags"] = []

    if not result.get("updated"):
        result["updated"] = (
            datetime.now()
            .astimezone()
            .date()
            .isoformat()
        )

    return result


def save_json(path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    print("=" * 50)
    print("雲嘉南週末去哪玩 - 自動資料蒐集")
    print("=" * 50)

    official_local = []

    for item in read_json(OFFICIAL):
        normalized = normalize(
            item,
            "official",
        )

        if normalized:
            official_local.append(
                normalized
            )

    social_local = []

    for item in read_json(SOCIAL):
        normalized = normalize(
            item,
            "social",
        )

        if normalized:
            social_local.append(
                normalized
            )

    tainan_online = []

    for item in collect_tainan_attractions():
        normalized = normalize(
            item,
            "official",
        )

        if normalized:
            tainan_online.append(
                normalized
            )

    official = (
        official_local
        + tainan_online
    )

    print("")
    print("資料蒐集結果：")
    print(
        f"原有官方資料："
        f"{len(official_local)} 筆"
    )
    print(
        f"台南網路資料："
        f"{len(tainan_online)} 筆"
    )
    print(
        f"官方資料合計："
        f"{len(official)} 筆"
    )
    print(
        f"社群資料："
        f"{len(social_local)} 筆"
    )

    save_json(
        OFFICIAL,
        official,
    )

    save_json(
        SOCIAL,
        social_local,
    )

    print("")
    print("資料已寫入 sources/")
    print("collect_sources.py 完成")


if __name__ == "__main__":
    main()
