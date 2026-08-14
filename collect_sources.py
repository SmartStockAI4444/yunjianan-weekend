from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"

OFFICIAL = SOURCES / "official_seed.json"
SOCIAL = SOURCES / "social_candidates.json"


def read_json(path):
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
    official = [
        normalize(x, "official")
        for x in read_json(OFFICIAL)
    ]

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
