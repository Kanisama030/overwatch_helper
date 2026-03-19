# Overwatch Helper

Overwatch 遊戲助手 — 依地圖情境推薦英雄、提供策略與反制建議。

## 架構

```
overwatch_helper/
├── scrapers/         # 資料爬蟲（Mobalytics、Blizzard）
├── scripts/          # 資料整合與衍生資料建置腳本
├── data/             # 資料檔（raw/ 原始、app/ 前端用）
└── frontend/         # React + Vite 前端網頁應用
    ├── src/          # 原始碼
    ├── public/data/  # 靜態 JSON 資料（build 時自動包進 dist）
    └── dist/         # 靜態 build 輸出（直接部署）
```

---

## 快速開始（靜態網頁）

### 方法 1：預覽模式（推薦）
```bash
cd frontend
npm run preview
# 開啟瀏覽器 http://localhost:4173
```

### 方法 2：用 Python HTTP Server 開啟 dist
```bash
cd frontend/dist
python -m http.server 8080
# 開啟瀏覽器 http://localhost:8080
```

### 方法 3：開發模式（即時重載）
```bash
cd frontend
npm run dev
# 開啟瀏覽器 http://localhost:5173
```

---

## 重新 Build 靜態網頁

```bash
# 1. 更新資料（需要 Python 環境）
python scripts/build_app_data.py

# 2. 複製資料到前端 public
Copy-Item data/app/* frontend/public/data/ -Recurse

# 3. Build 前端
cd frontend
npm run build
# 輸出於 frontend/dist/
```

---

## 資料更新（完整流程）

```bash
# 執行爬蟲 + 整合 + 衍生資料（需 conda 環境）
# 預設使用 Cloudflare Markdown 方法抓 Mobalytics
conda run -n overwatch python scripts/update.py
```

### Cloudflare 設定（Mobalytics 新方法）

```bash
set CLOUDFLARE_ACCOUNT_ID=你的_account_id
set CLOUDFLARE_API_TOKEN=你的_api_token
```

### 切回舊方法（Playwright）

```bash
conda run -n overwatch python scripts/update.py --mobalytics-method playwright
```

### 只測單一英雄（Smoke Test）

```bash
conda run -n overwatch python scripts/update.py --mobalytics-smoke-hero roadhog
```

### Markdown 留存位置

Mobalytics 原始 markdown 會留存於 `data/raw/mobalytics_markdown/`。

## Gemini 補齊腳本（獨立，不整合 update.py）

可用 Gemini 讀取 `overwatch_master.json` 的指定章節，補齊：

- `6.1.x` Best Maps
- `6.2.x` Worst Maps
- `8.2` Specific Hero Counters names（僅英雄 id 列表）

預設模型：`gemini-3.1-flash-lite-preview`

### 前置

1. 設定 API Key（擇一）

```bash
set GEMINI_API_KEY=你的_key
```

或在專案根目錄 `.env` 設定：

```bash
GEMINI_API_KEY=你的_key
```

2. 安裝 Gemini Python SDK

```bash
pip install google-genai
```

### 執行方式

先建議跑完整更新流程，再跑補齊腳本：

```bash
conda run -n overwatch python scripts/update.py
conda run -n overwatch python scripts/enrich_master_with_gemini.py --only-missing
```

單英雄測試（只看 Domina）：

```bash
conda run -n overwatch python scripts/enrich_master_with_gemini.py --hero domina --dry-run
```

強制覆蓋既有 `6.1/6.2/8.2`：

```bash
conda run -n overwatch python scripts/enrich_master_with_gemini.py --force
```

### 參數

- `--hero <id>`: 只處理指定英雄。
- `--only-missing`: 只補缺漏（預設啟用）。
- `--dry-run`: 只輸出預覽，不寫回檔案。
- `--force`: 覆蓋既有 `6.1/6.2` 子項與 `8.2 content`。
- `--model`: 指定模型，預設 `gemini-3.1-flash-lite-preview`。
- `--max-retries`: 失敗重試次數（預設 3）。
- `--retry-base-seconds`: 指數退避基礎秒數（預設 1.5）。

### 原始內容 vs AI 輸出（5 英雄對照測試）

若你想先人工比對原始內容與 AI 推論結果，可使用預覽腳本（不會寫回 `overwatch_master.json`）：

```bash
conda run -n overwatch python scripts/preview_gemini_enrichment.py
```

預設會測 5 位英雄：`domina,zarya,ana,roadhog,kiriko`，輸出檔案：

`data/app/gemini_preview_report.json`

自訂英雄（逗號分隔）：

```bash
conda run -n overwatch python scripts/preview_gemini_enrichment.py --heroes domina,sigma,tracer,echo,mercy
```

## 資料格式

主要資料檔為 `data/overwatch_master.json`，頂層結構如下：

```json
{
  "heroes": [
    {
      "Hero": "ana",
      "Tier": "A",
      "Guide": [
        { "id": "1", "title": "...", "content": ["..."] }
      ]
    }
  ],
  "meta_commentary": [
    { "category": "Tank Commentary", "heros": [...] }
  ]
}
```

### 欄位說明

- `heroes`: 英雄資料陣列（每位英雄一筆）
- `Hero`: 英雄 id（對應 `data/overwatch_mapping.json`）
- `Tier`: 來自 tier list 的分級（如 `S/A/B/C/D`）
- `Guide`: 由 Mobalytics 英雄頁 markdown 轉換後的章節陣列
- `meta_commentary`: 來自 tier list 文章的分組評論內容

### Guide 章節編號規則

- `id` 採階層編號：`6`、`6.1`、`6.1.1`（代表章節、子章節、子項）
- 常見主章節：
  - `1` Hero Overview
  - `2` Abilities
  - `3` Matchups
  - `4` Hero Playstyle
  - `5` Perks
  - `6` Maps
  - `7` Team Comp Synergies
  - `8` Hero Counters

### Maps（6）正規化規則

- 固定保留：
  - `6`: `Maps`
  - `6.1`: `Best Maps`
  - `6.2`: `Worst Maps`
- 若來源只有清單（如 `* Havana`），會展平成 `6.1.x` / `6.2.x` 子項，`title` 為地圖名。
- 若清單項目含說明，說明會掛在對應地圖子項的 `content`。
- 若無說明，子項維持 `content: []`。
- 某些英雄可能只有 `6` 或只有 `6.1`/`6.2`，屬於來源資料正常情況。

---

## 功能

- **Step 1 地圖選擇**：依模式（Assault/Control/Escort/Hybrid/Push 等）分組，支援搜尋與篩選
- **Step 2 英雄推薦**：針對所選地圖顯示 Best Picks / Avoid Picks / All Heroes，含 Tier Badge 與勝率
- **Step 3 英雄詳情**：
  - Strategy Overview：TLDR、戰術筆記、地圖勝率、Gemini AI 佔位符
  - Play Against Advisor：威脅清單、應對技巧、推薦換角

---

## 技術棧

- **前端**：React 19 + Vite 8 + TypeScript + Tailwind CSS v4
- **路由**：React Router v7（HashRouter，靜態部署無需 server rewrite）
- **資料**：靜態 JSON（`fetch('./data/app_ready_dataset.json')`）
- **語系**：英文（zh-TW 預留，coming soon）
