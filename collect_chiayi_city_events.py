from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFICIAL = ROOT / "sources" / "official_seed.json"

# 嘉義市政府 OpenData：活動總覽
CHIAYI_CITY_EVENTS_URL = (
    "https://data.chiayi.gov.tw/opendata/api/getResource"
    "?oid=33c3225e-f786-4eaf-8b9c-774cc39c72e0"
    "&rid=a809167f-bba6-475d-9dfe-33b4ea7749f6"
)

# 嘉義市政府 OpenData：新聞總覽（最新 50 則、每日更新）
# data.gov.tw/dataset/52319
CHIAYI_CITY_NEWS_URL = (
    "https://data.chiayi.gov.tw/opendata/api/getResource"
    "?oid=6dcaf207-e99b-4846-bd72-c334ce0d4b59"
    "&rid=87d4b27c-07c3-4546-815d-1e733dfd9497"
)

# 只把「民眾可參加／可旅遊」的市府新聞轉成活動，
# 不把一般施政、會議、工程新聞塞進旅遊 App。
TRAVEL_EVENT_KEYWORDS = [
    "活動", "音樂祭", "搖滾", "市集", "集點", "大白熊",
    "光織影舞", "媽祖", "贊境", "購物節", "展覽", "展演",
    "節慶", "燈會", "演唱", "演出", "親子", "尋寶", "體驗",
    "免費入場", "文化節", "藝術節", "嘉年華", "賞光影",
    "木吉", "城市IP",
]

# 排除較像純行政／交通公告、非遊程本體的新聞。
NEGATIVE_KEYWORDS = [
    "招標", "採購", "徵才", "會議紀錄", "預算", "決算",
    "停水", "停電", "施工公告", "垃圾清運", "人事",
]

# 本週重要官方活動短期保底；日期到期後自動失效。
# 這些都是使用者 2026-10-09 在嘉義市政府官方訊息看到的重點。
FALLBACK_EVENTS = [
    {
        "name": "2026嘉義市光織影舞",
        "start": "2026-09-25",
        "end": "2026-10-11",
        "place": "嘉義市・北香湖公園",
        "q": "北香湖公園 嘉義市",
        "why": "嘉義市政府官方光影藝術活動，雙十連假仍可前往。",
        "url": "https://travel.chiayi.gov.tw/DancingofLightandShadows2026/index.html",
        "heat": 96,
    },
    {
        "name": "熊熊抵嘉－大白熊集點趣",
        "start": "2026-10-05",
        "end": "2026-10-11",
        "place": "嘉義市・市區",
        "q": "嘉義市 大白熊 集點趣",
        "why": "尋找10隻大白熊蒐集電子章，完成集點可兌換限量好禮。",
        "url": "",
        "heat": 94,
    },
    {
        "name": "2026諸羅搖滾音樂祭",
        "start": "2026-10-10",
        "end": "2026-10-11",
        "place": "嘉義市・大同技術學院",
        "q": "大同技術學院 嘉義市 諸羅搖滾",
        "why": "雙十連假兩天登場，27組樂團接力演出，並有創意市集與美食。",
        "url": "",
        "heat": 97,
    },
    {
        "name": "白沙屯媽祖來嘉贊境",
        "start": "2026-10-09",
        "end": "2026-10-11",
        "place": "嘉義市",
        "q": "白沙屯媽祖 嘉義市 贊境",
        "why": "雙十連假宗教文化盛事；實際行經路線與交通管制請依官方即時公告。",
        "url": "",
        "heat": 95,
    },
    {
        "name": "2026嘉義市購物節",
        "start": "2026-07-01",
        "end": "2026-10-11",
        "place": "嘉義市・全市",
        "q": "2026嘉義市購物節",
        "why": "活動消費至10/11，符合資格發票可登錄抽獎；最後登錄期限依官方公告。",
        "url": "",
        "heat": 91,
    },
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
            headers={"User-Agent": "Mozilla/5.0 YunJiaNanWeekend/2.3"},
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        print(f"OpenData 取得失敗：{exc}")
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


def find_records(obj, key_name="title"):
    if isinstance(obj, list):
        if any(isinstance(x, dict) and key_name in x for x in obj):
            return obj
        for value in obj:
            found = find_records(value, key_name)
            if found:
                return found
    elif isinstance(obj, dict):
        if key_name in obj:
            return [obj]
        for value in obj.values():
            found = find_records(value, key_name)
            if found:
                return found
    return []


def normalize_date(value):
    text = flatten_text(value).strip()
    if not text:
        return ""

    m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"

    m = re.search(r"(?<!\d)(\d{2,3})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if m:
        y, mo, d = map(int, m.groups())
        if y < 1911:
            y += 1911
        return f"{y:04d}-{mo:02d}-{d:02d}"

    return ""


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


def make_id(prefix: str, name: str, start: str, end: str):
    digest = hashlib.sha1(
        f"{name}|{start}|{end}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}-{digest}"


def parse_news_dates(text: str, post_date: str):
    """從新聞標題/內文抽取西元、民國、10/9、10月9日等日期。
    回傳 (start, end)。只有一個活動日期時，start=end；
    若只找到截止日，會用發文日作 start。"""
    today_year = date.today().year
    dates = []

    def add(y, m, d):
        try:
            dates.append(date(int(y), int(m), int(d)))
        except Exception:
            pass

    # 西元
    for y, m, d in re.findall(
        r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text
    ):
        add(y, m, d)

    # 民國
    for y, m, d in re.findall(
        r"(?<!\d)(\d{2,3})[-/.](\d{1,2})[-/.](\d{1,2})", text
    ):
        yy = int(y)
        if yy < 1911:
            yy += 1911
        add(yy, m, d)

    # 10/9、10/11（避免把年份片段誤判）
    for m, d in re.findall(
        r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", text
    ):
        add(today_year, m, d)

    # 10月9日、10月11日
    for m, d in re.findall(
        r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", text
    ):
        add(today_year, m, d)

    dates = sorted(set(dates))
    pd = normalize_date(post_date)

    if not dates:
        return "", ""

    if len(dates) == 1:
        only = dates[0].isoformat()
        # 若內文有「至/截止」語氣，通常這個日期是結束日。
        if any(k in text for k in ("截止", "至", "到")) and pd:
            return pd, only
        return only, only

    return dates[0].isoformat(), dates[-1].isoformat()


def is_travel_event_news(title: str, content: str):
    text = f"{title} {content}"

    if any(k in text for k in NEGATIVE_KEYWORDS):
        return False

    hits = sum(1 for k in TRAVEL_EVENT_KEYWORDS if k in text)

    # 至少命中一個強活動關鍵字；避免一般市政新聞誤入。
    strong = any(
        k in text
        for k in (
            "音樂祭", "市集", "集點", "大白熊", "光織影舞",
            "媽祖", "贊境", "購物節", "節慶", "燈會",
            "演唱", "演出", "嘉年華", "免費入場",
        )
    )

    return strong or hits >= 2


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
                "id": make_id("chiayi-city-event", name, start, end),
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
                "why": content[:180] or (
                    f"嘉義市政府{unit}官方活動" if unit
                    else "嘉義市政府官方活動"
                ),
                "url": url,
            }
        )

    return results


def collect_city_news_events():
    raw = fetch_json(CHIAYI_CITY_NEWS_URL)
    records = find_records(raw) if raw else []
    today = date.today()
    results = []

    for item in records:
        if not isinstance(item, dict):
            continue

        title = clean_html_text(item.get("title", ""))
        content = clean_html_text(item.get("Content", ""))
        post_date = normalize_date(item.get("PostDate", ""))
        unit = clean_html_text(item.get("PostUnit", ""))
        url = first_url(item.get("Source", ""))

        if not title or not is_travel_event_news(title, content):
            continue

        # 只採最近 21 天新聞，避免舊聞反覆變成活動。
        if post_date:
            try:
                pd = date.fromisoformat(post_date)
                if (today - pd).days > 21:
                    continue
            except Exception:
                pass

        start, end = parse_news_dates(
            f"{title} {content}",
            post_date,
        )

        # 沒有可辨識活動日期的新聞，只放「更多推薦」的短期有效範圍，
        # 不讓它永久留在 feed。
        if not start:
            start = post_date or today.isoformat()
            end = (
                date.fromisoformat(start) + timedelta(days=10)
            ).isoformat()

        if not end:
            end = start

        # 已經完全過期的不加入。
        try:
            if date.fromisoformat(end) < today:
                continue
        except Exception:
            pass

        results.append(
            {
                "id": make_id("chiayi-city-news", title, start, end),
                "city": "嘉義",
                "name": title,
                "e": "📣",
                "type": "活動",
                "src": "官方",
                "base_heat": 93,
                "updated": post_date or today.isoformat(),
                "start": start,
                "end": end,
                "tags": ["活動", "嘉義市政府", "市府快報"],
                "place": "嘉義市",
                "q": title,
                "why": content[:200] or (
                    f"嘉義市政府{unit}最新官方消息"
                    if unit else "嘉義市政府最新官方消息"
                ),
                "url": url,
            }
        )

    return results


def fallback_events():
    today = date.today()
    out = []

    for item in FALLBACK_EVENTS:
        try:
            if date.fromisoformat(item["end"]) < today:
                continue
        except Exception:
            continue

        out.append(
            {
                "id": make_id(
                    "chiayi-city-fallback",
                    item["name"],
                    item["start"],
                    item["end"],
                ),
                "city": "嘉義",
                "name": item["name"],
                "e": "🎉",
                "type": "活動",
                "src": "官方",
                "base_heat": item.get("heat", 92),
                "updated": today.isoformat(),
                "start": item["start"],
                "end": item["end"],
                "tags": ["活動", "嘉義市政府", "本週末"],
                "place": item["place"],
                "q": item["q"],
                "why": item["why"],
                "url": item.get("url", ""),
            }
        )

    return out


def main():
    official = read_json(OFFICIAL)

    # 移除上一輪由此模組自動產生的資料，再放入最新版本。
    prefixes = (
        "chiayi-city-event-",
        "chiayi-city-news-",
        "chiayi-city-fallback-",
    )
    official = [
        x for x in official
        if not str(x.get("id", "")).startswith(prefixes)
    ]

    city_events = collect_city_events()
    news_events = collect_city_news_events()
    fallbacks = fallback_events()

    # 以 city + normalized name 去重。
    merged = {}
    for item in official + city_events + news_events + fallbacks:
        name = re.sub(
            r"[\s\-－—_：:「」『』（）()]+",
            "",
            str(item.get("name", "")).lower(),
        )
        key = (str(item.get("city", "")), name)

        if key not in merged:
            merged[key] = item
            continue

        # 同名時保留熱度高、資料較完整的那一筆。
        old = merged[key]
        if int(item.get("base_heat", 0)) >= int(old.get("base_heat", 0)):
            if not item.get("url") and old.get("url"):
                item["url"] = old["url"]
            merged[key] = item

    final = list(merged.values())
    save_json(OFFICIAL, final)

    print("=" * 60)
    print("嘉義市政府官方活動 + 市府新聞快報補充完成")
    print(f"活動總覽：{len(city_events)} 筆")
    print(f"新聞轉活動：{len(news_events)} 筆")
    print(f"本週重要活動保底：{len(fallbacks)} 筆")
    print(f"官方資料總數：{len(final)} 筆")
    print("=" * 60)


if __name__ == "__main__":
    main()
