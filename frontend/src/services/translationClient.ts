/**
 * Translation API Client
 * 負責讀取靜態翻譯檔，並管理 localStorage 快取
 */

const CACHE_SCHEMA_VERSION = 'v5';

interface TranslationSection {
  title?: string;
  description?: string;
  content: string[];
  content_hash: string;
  prompt_version: string;
  glossary_version: string;
  timestamp: string;
}

interface TranslationResponse {
  hero_id: string;
  locale: string;
  sections: Record<string, TranslationSection>;
  metadata: {
    prompt_version: string;
    glossary_version: string;
    timestamp: string;
  };
}

interface CacheEntry {
  data: TranslationResponse;
  cached_at: string;
}

/**
 * localStorage 快取鍵
 */
function getCacheKey(heroId: string, locale: string): string {
  return `ow_i18n_${CACHE_SCHEMA_VERSION}_${heroId}_${locale}`;
}

/**
 * 從 localStorage 讀取快取
 */
export function getTranslationFromCache(
  heroId: string,
  locale: string
): TranslationResponse | null {
  try {
    const key = getCacheKey(heroId, locale);
    const cached = localStorage.getItem(key);
    if (!cached) return null;

    const entry: CacheEntry = JSON.parse(cached);
    
    // 快取有效期：7 天
    const cachedAt = new Date(entry.cached_at);
    const now = new Date();
    const daysDiff = (now.getTime() - cachedAt.getTime()) / (1000 * 60 * 60 * 24);
    
    if (daysDiff > 7) {
      localStorage.removeItem(key);
      return null;
    }

    return entry.data;
  } catch (error) {
    console.warn('讀取翻譯快取失敗:', error);
    return null;
  }
}

/**
 * 寫入 localStorage 快取
 */
export function setTranslationCache(
  heroId: string,
  locale: string,
  data: TranslationResponse
): void {
  try {
    const key = getCacheKey(heroId, locale);
    const entry: CacheEntry = {
      data,
      cached_at: new Date().toISOString(),
    };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch (error) {
    console.warn('寫入翻譯快取失敗:', error);
    // 如果 localStorage 空間不足，清理舊快取
    if (error instanceof Error && error.name === 'QuotaExceededError') {
      clearOldTranslationCache();
      // 重試一次
      try {
        const key = getCacheKey(heroId, locale);
        const entry: CacheEntry = {
          data,
          cached_at: new Date().toISOString(),
        };
        localStorage.setItem(key, JSON.stringify(entry));
      } catch {
        console.error('清理後仍無法寫入快取');
      }
    }
  }
}

/**
 * 清理超過 7 天的翻譯快取
 */
function clearOldTranslationCache(): void {
  const now = new Date();
  const keysToRemove: string[] = [];

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key || !key.startsWith('ow_i18n_')) continue;

    try {
      const cached = localStorage.getItem(key);
      if (!cached) continue;

      const entry: CacheEntry = JSON.parse(cached);
      const cachedAt = new Date(entry.cached_at);
      const daysDiff = (now.getTime() - cachedAt.getTime()) / (1000 * 60 * 60 * 24);

      if (daysDiff > 7) {
        keysToRemove.push(key);
      }
    } catch {
      keysToRemove.push(key);
    }
  }

  keysToRemove.forEach(key => localStorage.removeItem(key));
  console.log(`清理了 ${keysToRemove.length} 個過期翻譯快取`);
}

/**
 * 從靜態檔取得翻譯
 */
export async function fetchTranslationFromStatic(
  heroId: string,
  locale: string
): Promise<TranslationResponse> {
  if (locale !== 'zh-TW') {
    throw new Error(`不支援的語系: ${locale}，目前僅支援 zh-TW`);
  }

  const url = `/data/i18n/${locale}/${heroId}.json`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`找不到翻譯檔: ${heroId} (${locale})`);
    }
    throw new Error(`翻譯檔讀取失敗: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * 取得英雄翻譯（先查快取，未命中則讀取靜態檔）
 */
export async function getHeroTranslation(
  heroId: string,
  locale: string
): Promise<TranslationResponse> {
  // 1. 檢查本地快取
  const cached = getTranslationFromCache(heroId, locale);
  if (cached) {
    console.log(`[Translation] 命中本地快取: ${heroId}`);
    return cached;
  }

  // 2. 讀取靜態翻譯檔
  console.log(`[Translation] 讀取靜態翻譯: ${heroId}`);
  const translation = await fetchTranslationFromStatic(heroId, locale);

  // 3. 寫入本地快取
  setTranslationCache(heroId, locale, translation);

  return translation;
}

/**
 * 清除指定英雄的翻譯快取（用於手動失效）
 */
export function invalidateHeroTranslationCache(heroId: string, locale: string): void {
  const key = getCacheKey(heroId, locale);
  localStorage.removeItem(key);
  console.log(`[Translation] 已清除快取: ${heroId} (${locale})`);
}

/**
 * 清除所有翻譯快取
 */
export function clearAllTranslationCache(): void {
  const keys: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith('ow_i18n_')) {
      keys.push(key);
    }
  }
  keys.forEach(key => localStorage.removeItem(key));
  console.log(`[Translation] 已清除所有翻譯快取 (${keys.length} 個)`);
}
