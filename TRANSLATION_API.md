# Overwatch Helper - 繁中翻譯 API

## 概述

本專案實作「後端代呼叫 Gemini + 雙層快取」的繁中按需翻譯系統，並提供**視覺化進度 UI**。

### 核心功能

1. **後端翻譯 API** (`backend/main.py`)
   - FastAPI 服務於 `http://127.0.0.1:8888`
   - Gemini 3.1 Flash Lite Preview 模型
   - Endpoint: `GET /api/i18n/hero/{hero_id}?locale=zh-TW`

2. **雙層快取機制**
   - **伺服器快取**: JSON 檔案 (`backend/cache/{hero_id}.json`)
   - **客戶端快取**: localStorage (`ow_i18n_{hero_id}_{locale}`)
   - Content hash 自動失效 + prompt/glossary 版本控制

3. **專有名詞強制對照**
   - 從 `data/overwatch_mapping.json` 載入英雄/地圖/模式名稱
   - Prompt 注入 glossary，確保術語一致性

4. **Per-section 細粒度翻譯**
   - 按 Guide section ID 分別翻譯與快取
   - 英文原文變更時，僅重翻變動的 section

5. **✨ 視覺化進度 UI** (NEW!)
   - 動態進度條 (橘色漸層 + 發光效果)
   - 4 步驟指示器 (檢查快取 → API → AI → 完成)
   - 脈動動畫與智能訊息更新
   - 支援快取命中與首次翻譯兩種情境


## 快速開始

### 1. 啟動後端 API

```bash
# Windows
start_translation_api.bat

# 或手動啟動
cd backend
conda activate overwatch
uvicorn main:app --host 127.0.0.1 --port 8888 --reload
```

### 2. 測試 API

**方式一：使用測試網頁**（✨ 含進度 UI）
開啟瀏覽器訪問：
```
file:///e:/projects/overwatch_helper/frontend/public/translation-test.html
```
點擊 Ana / Mercy / Reinhardt 按鈕測試翻譯。
- 首次翻譯：顯示完整進度與段落計數
- 快取命中：快速載入動畫

**方式二：直接呼叫 API**
```bash
curl "http://127.0.0.1:8888/api/i18n/hero/ana?locale=zh-TW"
```

### 3. 查看快取統計

```bash
curl "http://127.0.0.1:8888/api/health"
```

## API 規格

### GET /api/i18n/hero/{hero_id}

**參數：**
- `hero_id`: 英雄 ID（例如：`ana`, `mercy`, `reinhardt`）
- `locale`: 語系（目前僅支援 `zh-TW`）

**回應範例：**
```json
{
  "hero_id": "ana",
  "locale": "zh-TW",
  "sections": {
    "1": {
      "content": ["翻譯後的段落1", "翻譯後的段落2"],
      "content_hash": "db26cfb3c2a5",
      "prompt_version": "v1",
      "glossary_version": "v1",
      "timestamp": "2026-03-19T13:30:00Z"
    }
  },
  "metadata": {
    "prompt_version": "v1",
    "glossary_version": "v1",
    "timestamp": "2026-03-19T13:30:00Z"
  }
}
```

## 效能指標

基於 Ana 英雄測試（29 個 sections）：

| 情境 | 時間 | 說明 |
|------|------|------|
| 首次翻譯（伺服器未快取） | ~65 秒 | 呼叫 29 次 Gemini API |
| 首次載入（伺服器已快取） | ~500 毫秒 | 讀取 JSON 快取檔 |
| 二次載入（客戶端已快取） | ~47 毫秒 | 從 localStorage 讀取 |

**快取加速比：1400 倍** 🚀

## 灰度名單

目前僅對以下英雄啟用繁中動態翻譯：
- ✅ Ana（安娜）
- ✅ Mercy（慈悲）
- ✅ Reinhardt（萊因哈特）

其他英雄預設使用英文，避免不必要的 Gemini API 呼叫成本。

## 快取管理

### 手動失效快取

**伺服器快取：**
```bash
# 刪除指定英雄快取
rm backend/cache/ana.json

# 清空所有快取
rm backend/cache/*.json
```

**客戶端快取：**
在瀏覽器 Console 執行：
```javascript
// 清除指定英雄
localStorage.removeItem('ow_i18n_ana_zh-TW');

// 清除所有翻譯快取
Object.keys(localStorage)
  .filter(k => k.startsWith('ow_i18n_'))
  .forEach(k => localStorage.removeItem(k));
```

### 自動失效觸發

快取會在以下情況自動失效：
1. **英文原文變更**：content hash 改變
2. **Prompt 規則更新**：`prompt_version` 遞增
3. **Glossary 更新**：`glossary_version` 遞增
4. **客戶端快取過期**：超過 7 天

## 目錄結構

```
backend/
├── main.py                      # FastAPI 主應用
├── services/
│   ├── translation_service.py   # Gemini 翻譯邏輯
│   ├── cache_service.py         # 伺服器快取管理
│   └── glossary_service.py      # 專有名詞對照
├── cache/                       # 伺服器快取目錄
│   ├── ana.json
│   ├── mercy.json
│   └── reinhardt.json
└── requirements.txt

frontend/src/
├── services/
│   └── translationClient.ts     # API 客戶端 + localStorage
├── hooks/
│   └── useHeroTranslation.ts    # React Hook (含進度狀態)
├── components/common/
│   └── TranslationProgress.tsx  # 進度 UI 元件
└── public/
    └── translation-test.html    # 獨立測試頁面 (含進度 UI)
```

## 視覺化進度 UI

### 測試頁面預覽

翻譯進度畫面包含：
- 🤖 **動畫圖示**: 脈動效果表示處理中
- **進度條**: 橘色漸層 + 發光效果，實時顯示百分比
- **4 步驟指示器**: 
  1. ⚪ 檢查快取 → 🟠 (處理中) → 🟢 (完成)
  2. ⚪ 呼叫 API → 🟠 (處理中) → 🟢 (完成)
  3. ⚪ AI 翻譯 → 🟠 (處理中) → 🟢 (完成)
  4. ⚪ 完成 → ✅ (最終完成)
- **動態訊息**: 根據進度更新說明文字與段落計數

### React 元件使用

```tsx
import { TranslationProgress } from '../components/common/TranslationProgress';
import { useHeroTranslation } from '../hooks/useHeroTranslation';

function HeroDetailPage() {
  const { heroId } = useParams();
  const { locale } = useLocale();
  
  const { 
    sections, 
    loading, 
    currentStep,    // 當前步驟 1-4
    isFromCache     // 是否從快取載入
  } = useHeroTranslation(heroId, locale, true);

  if (loading) {
    return (
      <TranslationProgress
        isFromCache={isFromCache}
        currentStep={currentStep}
        onComplete={() => console.log('完成')}
      />
    );
  }

  // 渲染翻譯內容...
}
```

詳細文件請參閱：[TRANSLATION_PROGRESS.md](frontend/TRANSLATION_PROGRESS.md)

## 目錄結構

```
backend/
├── main.py                      # FastAPI 主應用
├── services/
│   ├── translation_service.py   # Gemini 翻譯邏輯
│   ├── cache_service.py         # 伺服器快取管理
│   └── glossary_service.py      # 專有名詞對照
├── cache/                       # 伺服器快取目錄
│   ├── ana.json
│   ├── mercy.json
│   └── reinhardt.json
└── requirements.txt

frontend/src/
├── services/
│   └── translationClient.ts     # API 客戶端 + localStorage
├── hooks/
│   └── useHeroTranslation.ts    # React Hook
├── components/common/
│   └── TranslationProgress.tsx  # 進度 UI 元件 (NEW!)
└── public/
    └── translation-test.html    # 獨立測試頁面
```

## 成本控制

### 避免重複呼叫 Gemini 的策略

1. **雙層快取**：伺服器 + 客戶端
2. **Per-section 快取**：僅重翻變動部分
3. **Content hash 驗證**：原文不變則不重翻
4. **灰度名單**：僅對 3 個英雄啟用

### 預估成本（50 英雄全量翻譯）

- 每英雄約 30 sections
- 每 section 約 500-2000 tokens
- Gemini 3.1 Flash Lite：免費額度內
- 首次翻譯後快取永久有效（除非原文變更）

## 已知限制

1. **前端未完全整合**：需手動訪問測試頁面
2. **僅支援 zh-TW**：其他語系需額外實作
3. **圖片連結未翻譯**：保留原始 Markdown 圖片語法
4. **無並發控制**：高並發時可能重複呼叫 Gemini（可加 single-flight 鎖）

## 後續優化方向

### 短期
- [ ] 整合到主前端 React App
- [ ] 加入載入狀態 UI 指示器
- [ ] 實作地圖/英雄名稱 mapping 直譯顯示

### 中期
- [ ] 加入 single-flight 去重鎖（避免並發重複呼叫）
- [ ] 支援手動重新翻譯指定 section
- [ ] 監控 Gemini API 使用量與錯誤率

### 長期
- [ ] 支援更多語系（日文、韓文等）
- [ ] 遷移到 Redis/Postgres 快取（高並發場景）
- [ ] 實作管理後台（查看快取、手動失效、統計報表）

## 技術棧

- **後端**: FastAPI 0.115.0 + Uvicorn 0.32.0
- **AI 模型**: Google Gemini 3.1 Flash Lite Preview
- **快取**: JSON 檔案 + localStorage
- **語言**: Python 3.12 + TypeScript 5.x

## 維護者

- 初始實作：2026-03-19
- 環境：Windows 10 + Conda (overwatch env)
