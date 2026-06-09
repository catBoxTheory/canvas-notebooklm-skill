# Canvas → NotebookLM Auto-Sync

自動從 CityU Canvas 下載課程檔案，整理到本地資料夾，並同步上傳至 NotebookLM。

## 支援課程

- CS3402
- SDSC2004
- SDSC2005
- SDSC2102

---

## 首次設定步驟

### 1. 安裝依賴套件

```bash
cd "/Users/wctsang/My Drive/University/CityU/Year_3/Spring Sem /Tools/canvas_sync"
pip install -r requirements.txt
```

### 2. 設定 Canvas API Token

前往 [canvas.cityu.edu.hk](https://canvas.cityu.edu.hk) → **Account** → **Settings** → **New Access Token**，複製 token。

```bash
cp .env.example .env
# 用文字編輯器打開 .env，把 token 填進去
```

### 3. 找出各課程的 Canvas ID

```bash
python discover_courses.py
```

輸出範例：
```
ID           Course Code     Course Name
----------------------------------------------------------------------
12345        CS3402-T01      Database Systems
12346        SDSC2004-T02    Data Visualization
```

把對應的 ID 填入 `config.yaml` 的 `canvas_id` 欄位。

### 4. 設定 NotebookLM 登入（只需一次）

```bash
notebooklm auth
```

按照指示用瀏覽器登入 Google 帳號，儲存 cookies。

### 5. 手動測試執行

```bash
python sync.py
```

確認下載和上傳都正常後，才設定排程。

### 6. 啟用每日自動排程（每天早上 8:00）

```bash
cp com.cityu.canvas_sync.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.cityu.canvas_sync.plist
```

---

## 日常使用

| 指令 | 說明 |
|------|------|
| `python sync.py` | 完整同步（下載 + 上傳） |
| `python sync.py --download-only` | 只從 Canvas 下載 |
| `python sync.py --upload-only` | 只上傳到 NotebookLM |

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `sync.py` | 主程式入口 |
| `canvas_downloader.py` | Canvas 下載邏輯 |
| `notebooklm_uploader.py` | NotebookLM 上傳邏輯 |
| `discover_courses.py` | 查詢 Canvas 課程 ID |
| `config.yaml` | 所有設定（課程、路徑、排程） |
| `state.json` | 自動生成：記錄已下載/上傳的檔案 |
| `logs/` | 每日 log 檔案 |

---

## 停用排程

```bash
launchctl unload ~/Library/LaunchAgents/com.cityu.canvas_sync.plist
```
