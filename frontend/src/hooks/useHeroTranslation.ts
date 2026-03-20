/**
 * useHeroTranslation Hook
 * 按需載入英雄翻譯並管理狀態
 */
import { useState, useEffect } from 'react';
import { getHeroTranslation, getTranslationFromCache } from '../services/translationClient';
import type { Locale } from '../types';

interface TranslationSection {
  title?: string;
  description?: string;
  content: string[];
  content_hash: string;
}

interface UseHeroTranslationResult {
  sections: Record<string, TranslationSection> | null;
  loading: boolean;
  error: string | null;
  progress: number; // 0-100
  currentStep: number; // 1-4
  isFromCache: boolean;
}

/**
 * 按需載入英雄的繁中翻譯
 * 
 * @param heroId 英雄 ID
 * @param locale 當前語系
 * @param enabled 是否啟用（用於灰度控制）
 * @returns 翻譯 sections、載入狀態、進度與錯誤訊息
 */
export function useHeroTranslation(
  heroId: string | undefined,
  locale: Locale,
  enabled: boolean = true
): UseHeroTranslationResult {
  const [sections, setSections] = useState<Record<string, TranslationSection> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(1);
  const [isFromCache, setIsFromCache] = useState(false);

  useEffect(() => {
    // 不需要翻譯的情況
    if (!heroId || locale !== 'zh-TW' || !enabled) {
      setSections(null);
      setLoading(false);
      setError(null);
      setProgress(0);
      setCurrentStep(1);
      return;
    }

    let isCancelled = false;
    let progressInterval: number | null = null;

    async function fetchTranslation() {
      setError(null);
      setProgress(0);
      setCurrentStep(1);

      // 檢查本地快取（有快取就直接展示）
      const cached = getTranslationFromCache(heroId!, locale);
      const cachedExists = cached !== null;
      setIsFromCache(cachedExists);

      if (cached) {
        if (!isCancelled) {
          setSections(cached.sections);
          setLoading(false);
          setProgress(100);
          setCurrentStep(4);
        }
        return;
      }

      setLoading(true);

      // 模擬進度更新
      const targetTime = 65000;
      const updateFrequency = 100;
      const totalSteps = targetTime / updateFrequency;
      const progressPerStep = 100 / totalSteps;

      progressInterval = window.setInterval(() => {
        setProgress(prev => {
          const next = prev + progressPerStep;
          if (next >= 100) {
            if (progressInterval !== null) {
              window.clearInterval(progressInterval);
            }
            return 100;
          }
          return next;
        });
      }, updateFrequency);

      try {
        // 步驟 1: 檢查快取
        setCurrentStep(1);
        await new Promise(resolve => setTimeout(resolve, 200));

        // 步驟 2: 呼叫 API
        if (!isCancelled) setCurrentStep(2);
        const result = await getHeroTranslation(heroId!, locale);

        // 步驟 3: AI 翻譯 (或讀取快取)
        if (!isCancelled) setCurrentStep(3);
        
        if (!isCancelled) {
          // 步驟 4: 完成
          setCurrentStep(4);
          setProgress(100);
          setSections(result.sections);
          setLoading(false);
          
          if (progressInterval !== null) {
            window.clearInterval(progressInterval);
          }
        }
      } catch (err) {
        if (!isCancelled) {
          console.error('[Translation] 翻譯失敗:', err);
          const message = err instanceof Error ? err.message : '翻譯載入失敗';
          if (message.includes('找不到翻譯檔')) {
            setError(null);
          } else {
            setError(message);
          }
          setLoading(false);
          setProgress(0);
          setCurrentStep(1);
          setSections(null);
          
          if (progressInterval !== null) {
            window.clearInterval(progressInterval);
          }
        }
      }
    }

    fetchTranslation();

    return () => {
      isCancelled = true;
      if (progressInterval !== null) {
        window.clearInterval(progressInterval);
      }
    };
  }, [heroId, locale, enabled]);

  return { sections, loading, error, progress, currentStep, isFromCache };
}
