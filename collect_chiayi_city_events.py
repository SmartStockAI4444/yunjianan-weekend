from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFICIAL = ROOT / "sources" / "official_seed.json"

# 嘉義市政府 OpenData「活動總覽」
# 政府資料開放平臺資料集：https://data.gov.tw/dataset/52321
CHIAYI_CITY_EVENTS_URL = (
    "https://data.chiayi.gov.tw/opendata/api/getResource"
    "?oid=33c3225e-f786-4eaf-8b9c-774cc39c72e0"
    "&rid=a809167f-bba6-475d-9dfe-33b4ea7749f6"
)

# OpenData 偶爾逾時時，本週已由官方確認的重點活動先作短期備援。
# 日期過後會自動略過，不會一直留在推薦裡。
FALLBACK_EVENTS = [
    {
        "name": "2026嘉義市光織影舞",
        "start": "2026-09-25",
        "end": "2026-10-11",
        "place": "嘉義市・北香湖公園",
        "q": "北香湖公園 嘉義市",
        "why": (
            "嘉義市政府官方光影藝術活動，展期至10/11；"
            "雙十連假10/9～10/11仍有活動。"
        ),
        "url": (
            "https://travel.chiayi.gov.tw/"
            "DancingofLightandShadows2026/index.html"
        ),
    }
]


def read_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("items", [])
            return items if isinstance(items, list) else []
    except Exception as exc:
        print(f"讀取 {path} 失敗：{exc}")
    return []


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_json(url: str):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 YunJiaNanWeekend/2.2"
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        print(f"嘉義市活動 OpenData 取得失敗：{exc}")
        return []


def flatten_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(flatten_text(x) for x in value)
    if isinstance(value, dict):
        return " ".join(flatten_text(x) for x in value.values())
    return str(value)


def clean_html_text(value):
    text = flatten_text(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def find_records(obj):
    if isinstance(obj, list):
        if any(isinstance(x, dict) and "title" in x for x in obj):
            return obj
        for value in obj:
            found = find_records(value)
            if found:
                return found
    elif isinstance(obj, dict):
        if "title" in obj:
            return [obj]
        for value in obj.values():
            found = find_records(value)
            if found:
                return found
    return []


def normalize_date(value):
    text = flatten_text(value).strip()
    if not text:
        return ""

    # 西元：2026-10-09 / 2026/10/09 / 2026.10.09
    m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"

    # 民國：115/10/09
    m = re.search(r"(?<!\d)(\d{2,3})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
        if y < 1911:
            y += 1911
        return f"{y:04d}-{mo:02d}-{d:02d}"

    return text[:10]


def first_url(value):
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return ""
    if isinstance(value, list):
        for item in value:
            u = first_url(item)
            if u:
                return u
    if isinstance(value, dict):
        for item in value.values():
            u = first_url(item)
            if u:
                return u
    return ""


def make_id(name: str, start: str, end: str):
    digest = hashlib.sha1(
        f"{name}|{start}|{end}".encode("utf-8")
    ).hexdigest()[:12]
    return f"chiayi-city-event-{digest}"


def collect_city_events():
    raw = fetch_json(CHIAYI_CITY_EVENTS_URL)
    records = find_records(raw) if raw else []
    today = datetime.now().strftime("%Y-%m-%d")
    results = []

    for item in records:
        if not isinstance(item, dict):
            continue

        name = clean_html_text(item.get("title", ""))
        if not name:
            continue

        start = normalize_date(item.get("ActiveStart", ""))
        end = normalize_date(item.get("ActiveEnd", ""))
        content = clean_html_text(item.get("Content", ""))
        unit = clean_html_text(item.get("PostUnit", ""))
        url = first_url(item.get("Source", ""))

        results.append(
            {
                "id": make_id(name, start, end),
                "city": "嘉義",
                "name": name,
                "e": "🎉",
                "type": "活動",
                "src": "官方",
                "base_heat": 86,
                "updated": today,
                "start": start,
                "end": end,
                "tags": ["活動", "嘉義市政府"],
                "place": "嘉義市",
                "q": name,
                "why": (
                    content[:160]
                    or (
                        f"嘉義市政府{unit}官方活動"
                        if unit
                        else "嘉義市政府官方活動"
                    )
                ),
                "url": url,
            }
        )

    # 本週官方活動的短期備援：API 沒抓到時才補。
    existing_names = {
        str(x.get("name", "")).strip()
        for x in results
    }

    for item in FALLBACK_EVENTS:
        name = item["name"]
        end = item.get("end", "")

        if end and today > end:
            continue
        if name in existing_names:
            continue

        start = item.get("start", "")
        results.append(
            {
                "id": make_id(name, start, end),
                "city": "嘉義",
                "name": name,
                "e": "🎉",
                "type": "活動",
                "src": "官方",
                "base_heat": 92,
                "updated": today,
                "start": start,
                "end": end,
                "tags": ["活動", "嘉義市政府", "本週末"],
                "place": item.get("place", "嘉義市"),
                "q": item.get("q", name),
                "why": item.get(
                    "why",
                    "嘉義市政府本週官方活動",
                ),
                "url": item.get("url", ""),
            }
        )

    return results


def main():
    official = read_json(OFFICIAL)

    # 每次都先移除上一輪嘉義市政府活動，再放入最新資料，
    # 避免 official_seed.json 長期累積過期項目。
    official = [
        x
        for x in official
        if not str(x.get("id", "")).startswith(
            "chiayi-city-event-"
        )
    ]

    city_events = collect_city_events()

    # exact city + name + type 去重；嘉義市政府來源優先覆蓋同名活動。
    merged = {}
    for item in official:
        key = (
            str(item.get("city", "")),
            str(item.get("name", "")),
            str(item.get("type", "")),
        )
        merged[key] = item

    for item in city_events:
        key = (
            str(item.get("city", "")),
            str(item.get("name", "")),
            str(item.get("type", "")),
        )
        merged[key] = item

    final = list(merged.values())
    save_json(OFFICIAL, final)

    print("=" * 50)
    print("嘉義市政府官方活動補充完成")
    print(f"本次取得／補充：{len(city_events)} 筆")
    print(f"官方資料總數：{len(final)} 筆")
    print("=" * 50)


if __name__ == "__main__":
    main()
