/**
 * TranslationProgress 元件
 * 顯示翻譯進度與步驟指示
 */
import { useEffect, useState } from 'react';

interface TranslationProgressProps {
  isFromCache: boolean;
  currentStep: number; // 1: 檢查快取, 2: 呼叫 API, 3: AI 翻譯, 4: 完成
  onComplete?: () => void;
}

export function TranslationProgress({ 
  isFromCache, 
  currentStep,
  onComplete 
}: TranslationProgressProps) {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('正在準備翻譯...');

  useEffect(() => {
    if (currentStep === 4 && onComplete) {
      const timer = setTimeout(onComplete, 500);
      return () => clearTimeout(timer);
    }
  }, [currentStep, onComplete]);

  useEffect(() => {
    const targetTime = isFromCache ? 500 : 65000;
    const updateFrequency = 100;
    const totalSteps = targetTime / updateFrequency;
    const progressPerStep = 100 / totalSteps;

    const interval = setInterval(() => {
      setProgress(prev => {
        const next = prev + progressPerStep;
        if (next >= 100) {
          clearInterval(interval);
          return 100;
        }
        return next;
      });
    }, updateFrequency);

    return () => clearInterval(interval);
  }, [isFromCache]);

  useEffect(() => {
    if (isFromCache) {
      if (progress < 30) setMessage('檢查本地快取...');
      else if (progress < 70) setMessage('讀取快取資料...');
      else setMessage('載入完成！');
    } else {
      if (progress < 10) setMessage('檢查本地快取...');
      else if (progress < 20) setMessage('連接翻譯伺服器...');
      else if (progress < 95) {
        const sections = Math.floor((progress - 20) / 2.5);
        setMessage(`AI 翻譯中... (約 ${sections}/29 段落)`);
      } else setMessage('完成翻譯！');
    }
  }, [progress, isFromCache]);

  const steps = [
    { id: 1, label: '檢查快取', icon: '1' },
    { id: 2, label: '呼叫 API', icon: '2' },
    { id: 3, label: 'AI 翻譯', icon: '3' },
    { id: 4, label: '完成', icon: '✓' },
  ];

  return (
    <div className="translation-progress">
      <div className="text-center mb-6">
        <div className="text-5xl mb-4 animate-pulse">🤖</div>
        <h3 className="text-xl font-bold mb-2" style={{ color: '#f27f0d' }}>
          AI 即時翻譯中...
        </h3>
        <p className="text-sm" style={{ color: '#9ca3af' }}>
          {message}
        </p>
      </div>

      {/* 進度條 */}
      <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden mb-6">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${progress}%`,
            background: 'linear-gradient(90deg, #f27f0d, #ff9f4a)',
            boxShadow: '0 0 10px rgba(242, 127, 13, 0.5)',
          }}
        />
      </div>

      {/* 步驟指示器 */}
      <div className="flex justify-between items-start px-4">
        {steps.map((step, index) => (
          <div key={step.id} className="flex flex-col items-center flex-1 relative">
            {/* 連接線 */}
            {index < steps.length - 1 && (
              <div
                className="absolute top-[15px] left-1/2 right-[-50%] h-0.5 -z-10"
                style={{
                  background: currentStep > step.id
                    ? '#22c55e'
                    : 'rgba(242, 127, 13, 0.2)',
                }}
              />
            )}

            {/* 圖示 */}
            <div
              className={`
                w-8 h-8 rounded-full flex items-center justify-center
                text-sm font-bold mb-2 transition-all duration-300
                ${currentStep > step.id ? 'bg-green-500 text-white' : ''}
                ${currentStep === step.id ? 'bg-[#f27f0d] text-white animate-pulse' : ''}
                ${currentStep < step.id ? 'bg-[#f27f0d]/20 text-gray-500' : ''}
              `}
              style={
                currentStep === step.id
                  ? { boxShadow: '0 0 15px rgba(242, 127, 13, 0.6)' }
                  : {}
              }
            >
              {step.icon}
            </div>

            {/* 標籤 */}
            <div
              className={`
                text-xs text-center
                ${currentStep > step.id ? 'text-green-500 font-bold' : ''}
                ${currentStep === step.id ? 'text-[#f27f0d] font-bold' : ''}
                ${currentStep < step.id ? 'text-gray-500' : ''}
              `}
            >
              {step.label}
            </div>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.1); }
        }
        .animate-pulse {
          animation: pulse 1.5s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
