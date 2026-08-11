# 雲嘉南週末去哪玩 V1.7

這個資料夾已整理成可直接上傳 GitHub 的專案。

## 主要檔案
- `index.html`：App 主程式
- `weekly_feed.json`：每週推薦資料
- `update_feed.py`：每週更新腳本入口
- `.github/workflows/deploy-pages.yml`：GitHub Pages 自動部署
- `.github/workflows/weekly-refresh.yml`：每週一自動執行資料更新腳本的骨架

## 第一次部署
1. 到 GitHub 建立新的 Repository，例如 `yunjianan-weekend`
2. 把這個 ZIP 解壓縮後的所有檔案上傳到 Repository 根目錄
3. 確認預設 branch 為 `main`
4. GitHub Repository → Settings → Pages
5. Source 選擇 `GitHub Actions`
6. 回到 Actions，等待 `Deploy GitHub Pages` 執行完成
7. GitHub 會提供網站網址

之後手機只要開 GitHub Pages 網址即可，不需要再下載 HTML。

## 每週資料更新
只要更新 `weekly_feed.json` 並推送到 GitHub：
- Pages 會重新部署
- App 打開時會自動讀取新版 `weekly_feed.json`
- 同步失敗仍會使用手機快取

## weekly_feed.json 格式
外層：
- `version`
- `updated`
- `items`

每筆 item 建議包含：
`id, city, name, e, type, src, heat, updated, start, end, tags, place, q, why, url`

## 關於 weekly-refresh workflow
目前 `update_feed.py` 只更新 feed 的版本與日期，尚未自動抓取 Facebook / Instagram。
未來可以在這裡接：
- 官方活動來源
- 公開網頁資料
- 人工審核後的社群推薦資料

避免直接做未授權的大量社群平台爬取。
