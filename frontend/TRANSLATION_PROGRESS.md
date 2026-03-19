# 翻譯進度 UI 使用指南

## 概述

翻譯進度 UI 提供視覺化回饋，讓使用者了解 AI 翻譯的進度與狀態。

## 測試頁面

### 使用方式

1. 啟動後端 API:
```bash
start_translation_api.bat
```

2. 開啟測試頁面:
```
file:///e:/projects/overwatch_helper/frontend/public/translation-test.html
```

3. 點擊英雄按鈕測試翻譯進度顯示

### 進度畫面包含

- **🤖 動畫圖示**: 脈動效果表示處理中
- **進度條**: 實時顯示載入百分比
- **步驟指示器**: 4 個步驟視覺化
  1. 檢查快取 (灰色 → 橘色)
  2. 呼叫 API (灰色 → 橘色)
  3. AI 翻譯 (灰色 → 橘色)
  4. 完成 (綠色 ✓)
- **動態訊息**: 根據進度更新說明文字

### 兩種情境

**快取命中** (0.5 秒):
```
檢查本地快取... → 讀取快取資料... → 載入完成！
```

**首次翻譯** (~65 秒):
```
檢查本地快取... → 連接翻譯伺服器... → AI 翻譯中... (顯示段落數) → 完成翻譯！
```

## React 元件整合

### 1. 安裝元件

元件已建立於:
```
frontend/src/components/common/TranslationProgress.tsx
```

### 2. 使用範例

```tsx
import { TranslationProgress } from '../components/common/TranslationProgress';
import { useHeroTranslation } from '../hooks/useHeroTranslation';
import { useLocale } from '../contexts/localeContextStore';

function HeroDetailPage() {
  const { heroId } = useParams();
  const { locale } = useLocale();
  
  const { 
    sections, 
    loading, 
    error,
    currentStep,
    isFromCache 
  } = useHeroTranslation(heroId, locale, true);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="max-w-md w-full p-6">
          <TranslationProgress
            isFromCache={isFromCache}
            currentStep={currentStep}
            onComplete={() => console.log('翻譯完成')}
          />
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="text-red-500">翻譯錯誤: {error}</div>;
  }

  // 渲染翻譯內容
  return (
    <div>
      {/* 使用 sections 渲染內容 */}
    </div>
  );
}
```

### 3. Hook API

`useHeroTranslation` 回傳值:

```typescript
{
  sections: Record<string, TranslationSection> | null;
  loading: boolean;          // 是否載入中
  error: string | null;      // 錯誤訊息
  progress: number;          // 進度 0-100
  currentStep: number;       // 當前步驟 1-4
  isFromCache: boolean;      // 是否從快取載入
}
```

### 4. 客製化樣式

TranslationProgress 元件使用 Tailwind CSS，可透過 props 或修改元件來客製化:

```tsx
<TranslationProgress
  isFromCache={false}
  currentStep={3}
  onComplete={() => {
    // 完成後的處理邏輯
    showSuccessToast('翻譯完成！');
  }}
/>
```

## 樣式細節

### 顏色設計

- **主色 (橘色)**: `#f27f0d` - 進度條、活動步驟
- **成功 (綠色)**: `#22c55e` - 完成步驟
- **背景**: 半透明橘色漸層
- **文字**: 灰色 `#9ca3af` 與白色

### 動畫效果

- **脈動動畫**: 1.5 秒循環，用於 loading 圖示
- **步驟脈動**: 1 秒循環，用於當前步驟
- **進度條**: 0.3 秒過渡，平滑移動
- **發光效果**: `box-shadow` 模擬橘色光暈

### 響應式設計

- 手機螢幕: 單欄顯示，步驟縮小
- 平板/桌面: 完整顯示，步驟橫向排列
- 進度條與步驟指示器自適應寬度

## 整合檢查清單

- [ ] 確認 API 伺服器運行於 `http://127.0.0.1:8888`
- [ ] 測試快取命中情境（二次載入同英雄）
- [ ] 測試首次翻譯情境（首次載入或清除快取）
- [ ] 確認進度訊息正確更新
- [ ] 測試錯誤處理（關閉 API 伺服器）
- [ ] 驗證完成動畫與 `onComplete` 回調

## 效能考量

- 進度模擬使用 100ms interval，對效能影響極小
- localStorage 讀寫操作同步，快取命中時幾乎無延遲
- 元件卸載時自動清理 interval，避免記憶體洩漏

## 已知限制

1. **進度預估**: 基於平均時間模擬，實際翻譯速度可能有變化
2. **段落計數**: 固定顯示 `/29`，不同英雄段落數可能不同
3. **並發請求**: 多個請求同時進行時，進度顯示可能不準確

## 未來改進

- [ ] 從 API 回傳實際翻譯進度（需後端支援 SSE 或 WebSocket）
- [ ] 加入暫停/取消翻譯功能
- [ ] 支援批次翻譯進度顯示
- [ ] 加入音效提示（完成時播放提示音）
- [ ] 動態計算段落數（從 hero 資料取得）
