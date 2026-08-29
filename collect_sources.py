from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"

OFFICIAL = SOURCES / "official_seed.json"
FACTORY = SOURCES / "factory_seed.json"
SOCIAL = SOURCES / "social_candidates.json"

# 台南官方旅遊網：保留目前已經穩定運作的來源
TAINAN_ATTRACTIONS_URL = (
    "https://www.twtainan.net/data/attractions_zh-tw.json"
)

# 交通部觀光署「觀光資訊資料庫」
# 官方全國景點與活動，每日更新
TAIWAN_ATTRACTIONS_ZIP = (
    "https://media.taiwan.net.tw/"
    "XMLReleaseAll_public/v2.0/Zh_tw/Attraction-json.zip"
)

TAIWAN_EVENTS_ZIP = (
    "https://media.taiwan.net.tw/"
    "XMLReleaseAll_public/v2.0/Zh_tw/Event-json.zip"
)

TARGET_CITIES = {
    "雲林縣": "雲林",
    "雲林": "雲林",
    "嘉義縣": "嘉義",
    "嘉義市": "嘉義",
    "嘉義": "嘉義",
    "臺南市": "台南",
    "台南市": "台南",
    "臺南": "台南",
    "台南": "台南",
}


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

        if isinstance(data, dict):
            items = data.get("items", [])
            if isinstance(items, list):
                return items

    except Exception as exc:
        print(f"讀取失敗：{path}")
        print(exc)

    return []


def fetch_bytes(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 YunJiaNanWeekend/2.0"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=45,
        ) as response:
            return response.read()

    except Exception as exc:
        print(f"網路取得失敗：{url}")
        print(exc)
        return None


def fetch_json(url):
    raw = fetch_bytes(url)

    if not raw:
        return []

    try:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8-sig")

        return json.loads(text)

    except Exception as exc:
        print(f"JSON 解析失敗：{url}")
        print(exc)
        return []


def find_records(obj, name_field):
    """
    官方 ZIP 內 JSON 的最外層結構若日後調整，
    仍盡量自動找到真正的景點/活動資料陣列。
    """

    if isinstance(obj, list):
        if any(
            isinstance(x, dict) and name_field in x
            for x in obj
        ):
            return obj

        for value in obj:
            found = find_records(value, name_field)
            if found:
                return found

    elif isinstance(obj, dict):
        if name_field in obj:
            return [obj]

        for value in obj.values():
            found = find_records(value, name_field)
            if found:
                return found

    return []


def fetch_zip_json(url, name_field):
    raw = fetch_bytes(url)

    if not raw:
        return []

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            json_files = [
                name
                for name in zf.namelist()
                if name.lower().endswith(".json")
            ]

            if not json_files:
                print("ZIP 裡找不到 JSON")
                return []

            all_records = []

            for filename in json_files:
                content = zf.read(filename)

                try:
                    text = content.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = content.decode(
                        "utf-8",
                        errors="replace",
                    )

                data = json.loads(text)

                records = find_records(
                    data,
                    name_field,
                )

                all_records.extend(records)

            return all_records

    except Exception as exc:
        print(f"ZIP 解析失敗：{url}")
        print(exc)
        return []


def flatten_text(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        return " ".join(
            flatten_text(x)
            for x in value
        )

    if isinstance(value, dict):
        return " ".join(
            flatten_text(x)
            for x in value.values()
        )

    return str(value)


def first_url(value):
    if isinstance(value, str):
        if value.startswith("http://") or value.startswith(
            "https://"
        ):
            return value
        return ""

    if isinstance(value, list):
        for item in value:
            result = first_url(item)
            if result:
                return result

    if isinstance(value, dict):
        for item in value.values():
            result = first_url(item)
            if result:
                return result

    return ""


def detect_city(item):
    location_text = " ".join(
        [
            flatten_text(
                item.get("LocatedCities", "")
            ),
            flatten_text(
                item.get("PostalAddress", "")
            ),
            flatten_text(
                item.get("Address", "")
            ),
        ]
    )

    for keyword, city in TARGET_CITIES.items():
        if keyword in location_text:
            return city

    return ""


def short_date(value):
    text = flatten_text(value).strip()

    if not text:
        return ""

    return text[:10]


def make_place(item, city):
    address = flatten_text(
        item.get("PostalAddress", "")
    ).strip()

    if address:
        return address[:100]

    return city


def collect_taiwan_attractions():
    print("開始取得交通部觀光署全國景點資料...")

    raw = fetch_zip_json(
        TAIWAN_ATTRACTIONS_ZIP,
        "AttractionName",
    )

    results = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        city = detect_city(item)

        if not city:
            continue

        name = flatten_text(
            item.get("AttractionName", "")
        ).strip()

        if not name:
            continue

        item_id = flatten_text(
            item.get("AttractionID", name)
        ).strip()

        description = flatten_text(
            item.get("Description", "")
        ).strip()

        classes = flatten_text(
            item.get("AttractionClasses", "")
        )

        tags = ["景點"]

        if any(
            word in classes + description
            for word in [
                "自然",
                "生態",
                "森林",
                "海岸",
                "步道",
                "公園",
            ]
        ):
            tags.append("戶外")

        if any(
            word in classes + description
            for word in [
                "文化",
                "古蹟",
                "歷史",
                "藝術",
                "博物館",
            ]
        ):
            tags.append("文化")

        website = first_url(
            item.get("WebsiteURL", "")
        )

        if not website:
            website = first_url(
                item.get("SameAsURLs", "")
            )

        results.append(
            {
                "id":
                    f"tourism-attraction-{item_id}",
                "city": city,
                "name": name,
                "e": "📍",
                "type": "景點",
                "src": "官方",
                "base_heat": 72,
                "updated": short_date(
                    item.get("UpdateTime", "")
                ),
                "tags": list(dict.fromkeys(tags)),
                "place": make_place(item, city),
                "q": make_place(item, city),
                "why":
                    description[:160]
                    or f"{city}官方旅遊景點",
                "url": website,
            }
        )

    print(
        f"交通部景點取得完成：{len(results)} 筆"
    )

    return results


def collect_taiwan_events():
    print("開始取得交通部觀光署全國活動資料...")

    raw = fetch_zip_json(
        TAIWAN_EVENTS_ZIP,
        "EventName",
    )

    results = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        city = detect_city(item)

        if not city:
            continue

        name = flatten_text(
            item.get("EventName", "")
        ).strip()

        if not name:
            continue

        item_id = flatten_text(
            item.get("EventID", name)
        ).strip()

        description = flatten_text(
            item.get("Description", "")
        ).strip()

        website = first_url(
            item.get("WebsiteURL", "")
        )

        if not website:
            website = first_url(
                item.get("SameAsURLs", "")
            )

        start = short_date(
            item.get("StartDateTime", "")
        )

        end = short_date(
            item.get("EndDateTime", "")
        )

        results.append(
            {
                "id":
                    f"tourism-event-{item_id}",
                "city": city,
                "name": name,
                "e": "🎉",
                "type": "活動",
                "src": "官方",
                "base_heat": 80,
                "updated": short_date(
                    item.get("UpdateTime", "")
                ),
                "start": start,
                "end": end,
                "tags": ["活動"],
                "place": make_place(item, city),
                "q": make_place(item, city),
                "why":
                    description[:160]
                    or f"{city}近期官方活動",
                "url": website,
            }
        )

    print(
        f"交通部活動取得完成：{len(results)} 筆"
    )

    return results


def collect_tainan_attractions():
    print("開始取得台南官方景點資料...")

    raw = fetch_json(TAINAN_ATTRACTIONS_URL)

    if not isinstance(raw, list):
        print("台南官方來源格式異常")
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
            item.get("categories", ""),
        )

        category_text = flatten_text(categories)

        if "自然" in category_text:
            tags = ["戶外", "自然"]
        elif "文化" in category_text:
            tags = ["文化"]
        else:
            tags = ["親子"]

        district = str(
            item.get(
                "district",
                item.get("area", "台南"),
            )
        ).strip()

        address = str(
            item.get("address", "")
        ).strip()

        summary = str(
            item.get(
                "summary",
                item.get("description", ""),
            )
        ).strip()

        update_time = str(
            item.get(
                "updated_at",
                item.get("updated", ""),
            )
        )

        results.append(
            {
                "id":
                    f"tainan-attraction-{item_id}",
                "city": "台南",
                "name": name,
                "e": "📍",
                "type": "景點",
                "src": "官方",
                "base_heat": 70,
                "updated": update_time[:10],
                "tags": tags,
                "place": district or "台南",
                "q": address or name,
                "why":
                    summary[:160]
                    or "台南官方旅遊景點",
                "url":
                    f"https://www.twtainan.net/"
                    f"zh-tw/attractions/detail/{item_id}",
            }
        )

    print(
        f"台南官方景點取得完成：{len(results)} 筆"
    )

    return results


def normalize(item, source_type):
    if not isinstance(item, dict):
        return None

    result = dict(item)

    name = str(
        result.get("name", "")
    ).strip()

    if not name:
        return None

    city = str(
        result.get("city", "")
    ).strip()

    if city in ("臺南", "臺南市", "台南市"):
        city = "台南"
    elif city in ("雲林縣",):
        city = "雲林"
    elif city in ("嘉義縣", "嘉義市"):
        city = "嘉義"

    result["city"] = city

    if not result.get("id"):
        result["id"] = (
            f"{source_type}-{city}-{name}"
        )

    if not result.get("src"):
        result["src"] = (
            "官方"
            if source_type == "official"
            else "社群"
        )

    if not result.get("type"):
        result["type"] = "景點"

    if not result.get("e"):
        result["e"] = (
            "🎉"
            if result["type"] == "活動"
            else "📍"
        )

    if not isinstance(
        result.get("tags"),
        list,
    ):
        result["tags"] = []

    if not result.get("place"):
        result["place"] = city

    if not result.get("q"):
        result["q"] = (
            result.get("place")
            or name
        )

    if not result.get("why"):
        result["why"] = (
            f"{city}{result['type']}推薦"
        )

    if "base_heat" not in result:
        result["base_heat"] = 70

    if not result.get("updated"):
        result["updated"] = (
            datetime.now().strftime("%Y-%m-%d")
        )

    if "url" not in result:
        result["url"] = ""

    return result


def dedupe(items):
    """
    有 id 優先使用 id 去重。
    沒有 id 時使用 city + name。
    """

    unique = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        key = str(
            item.get("id", "")
        ).strip()

        if not key:
            key = (
                f"{item.get('city', '')}-"
                f"{item.get('name', '')}"
            )

        if key:
            unique[key] = item

    return list(unique.values())


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


def normalized_file(path, source_type):
    results = []

    for item in read_json(path):
        normalized = normalize(
            item,
            source_type,
        )

        if normalized:
            results.append(normalized)

    return results


def main():
    print("=" * 50)
    print(
        "雲嘉南週末去哪玩 - "
        "自動資料蒐集 V2.0"
    )
    print("=" * 50)

    # official_seed.json 會被每次工作流程重新寫入。
    # 因此先排除上一輪自動抓取的資料，
    # 避免每週重複累積。
    generated_prefixes = (
        "tainan-attraction-",
        "tourism-attraction-",
        "tourism-event-",
    )

    official_local = [
        x
        for x in normalized_file(
            OFFICIAL,
            "official",
        )
        if not str(
            x.get("id", "")
        ).startswith(generated_prefixes)
    ]

    factory_local = normalized_file(
        FACTORY,
        "official",
    )

    social_local = normalized_file(
        SOCIAL,
        "social",
    )

    # 全國官方資料，只保留雲嘉南
    taiwan_attractions = []

    for item in collect_taiwan_attractions():
        normalized = normalize(
            item,
            "official",
        )

        if normalized:
            taiwan_attractions.append(
                normalized
            )

    taiwan_events = []

    for item in collect_taiwan_events():
        normalized = normalize(
            item,
            "official",
        )

        if normalized:
            taiwan_events.append(
                normalized
            )

    # 保留原本已驗證成功的台南來源作補充
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

    official = dedupe(
        official_local
        + factory_local
        + taiwan_attractions
        + taiwan_events
        + tainan_online
    )

    social = dedupe(social_local)

    print("")
    print("資料蒐集結果：")
    print(
        f"原有官方資料："
        f"{len(official_local)} 筆"
    )
    print(
        f"觀光工廠資料："
        f"{len(factory_local)} 筆"
    )
    print(
        f"交通部雲嘉南景點："
        f"{len(taiwan_attractions)} 筆"
    )
    print(
        f"交通部雲嘉南活動："
        f"{len(taiwan_events)} 筆"
    )
    print(
        f"台南旅遊網景點："
        f"{len(tainan_online)} 筆"
    )
    print(
        f"官方資料去重後："
        f"{len(official)} 筆"
    )
    print(
        f"社群資料去重後："
        f"{len(social)} 筆"
    )

    save_json(
        OFFICIAL,
        official,
    )

    save_json(
        SOCIAL,
        social,
    )

    print("")
    print("資料已寫入 sources/")
    print("collect_sources.py V2.0 完成")


if __name__ == "__main__":
    main()
