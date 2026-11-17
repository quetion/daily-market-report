# 每日財經報導

在本機做好的每日分析 HTML，放進 Google Drive 的「每日財經報導」資料夾，每天台北時間 08:00 自動上線。

## 日常使用

1. 把當天的 HTML 存進 Drive 資料夾 `我的雲端硬碟/每日財經報導/`
   - 檔名開頭用日期：`20261117_xxx.html` → 網址 `/2026-11-17/`
   - 同一天放了好幾份，只取最後修改的那份
   - 從資料夾刪掉的檔案，下次發布時網站上也會消失
2. 每天 08:00 自動發布。想馬上上線：
   - 本機執行 `./publish.sh`，或
   - GitHub repo → Actions →「發布每日財經報導」→ Run workflow

## 網站結構

- `/` 最新一篇（右下角有「歷史日報」按鈕）
- `/YYYY-MM-DD/` 每天的固定網址
- `/archive/` 歷史列表（標題取自 HTML 的 `<title>`）

## 本機預覽

```sh
python3 build.py --local "$HOME/Library/CloudStorage/GoogleDrive-<帳號>/我的雲端硬碟/每日財經報導"
open _site/index.html
```

## 一次性設定：Google 服務帳號

1. 到 https://console.cloud.google.com/ 建一個專案（隨便取名）
2. 「API 和服務」→「程式庫」→ 啟用 **Google Drive API**
3. 「IAM 與管理」→「服務帳號」→ 建立服務帳號（不用給角色）
4. 點進服務帳號 →「金鑰」→ 新增金鑰 → JSON，下載
5. 在 Drive 把「每日財經報導」資料夾**共用**給服務帳號的 email（`xxx@xxx.iam.gserviceaccount.com`），權限「檢視者」
6. 設定 GitHub secrets：
   ```sh
   gh secret set GDRIVE_SA_JSON < ~/Downloads/<金鑰檔>.json
   gh secret set GDRIVE_FOLDER_ID --body "<資料夾網址最後那段 ID>"
   rm ~/Downloads/<金鑰檔>.json   # 設好就刪掉本機金鑰
   ```

網站標題可在 repo 的 Settings → Secrets and variables → Actions → Variables 新增 `SITE_TITLE` 修改。
