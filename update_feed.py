import json, datetime
from pathlib import Path

p=Path("weekly_feed.json")
data=json.loads(p.read_text(encoding="utf-8"))
today=datetime.date.today().isoformat()
data["updated"]=today
data["version"]=today.replace("-",".")+"-01"

# 未來可在此加入：官方 API、公開網頁、人工審核後的社群推薦資料。
# 更新完成後重新寫回 weekly_feed.json。
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("updated",data["version"],"items",len(data["items"]))
