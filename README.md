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
conda run -n overwatch python scripts/update.py
```

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
