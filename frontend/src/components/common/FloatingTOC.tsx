/**
 * FloatingTOC — 浮動右側錨點目錄元件
 * 平時收合為細條，滑鼠 hover 後展開顯示目錄文字，
 * 點擊後平滑捲動至對應區段。
 * IntersectionObserver 自動高亮目前可見的段落。
 * 手機裝置（< md breakpoint）自動隱藏。
 */
import { useEffect, useRef, useState } from 'react';

export interface TOCItem {
  /** 對應 DOM 元素的 id */
  id: string;
  /** 顯示的標籤文字 */
  label: string;
  /** Material Symbols icon 名稱 */
  icon?: string;
}

interface FloatingTOCProps {
  items: TOCItem[];
  /** 捲動的容器選擇器（預設為頁面最近的 overflow-y-auto 祖先） */
  scrollContainerSelector?: string;
}

export function FloatingTOC({ items, scrollContainerSelector }: FloatingTOCProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [activeId, setActiveId] = useState<string>('');
  const observerRef = useRef<IntersectionObserver | null>(null);

  // ── IntersectionObserver：追蹤目前可見段落 ──
  useEffect(() => {
    if (items.length === 0) return;

    observerRef.current?.disconnect();

    // 找到捲動容器（預設偵測第一個 overflow-y-auto 容器）
    const scrollEl = scrollContainerSelector
      ? document.querySelector(scrollContainerSelector)
      : null;

    const options: IntersectionObserverInit = {
      root: scrollEl ?? null,
      // 從頂部 -10% ~ 底部 30%，只要段落進入這個視窗範圍就算可見
      rootMargin: '-10% 0px -60% 0px',
      threshold: 0,
    };

    observerRef.current = new IntersectionObserver((entries) => {
      // 找出最新進入視窗的項目
      const visible = entries.filter(e => e.isIntersecting);
      if (visible.length > 0) {
        // 優先取最靠近頂部的目標
        const topEntry = visible.reduce((prev, curr) =>
          prev.boundingClientRect.top < curr.boundingClientRect.top ? prev : curr
        );
        setActiveId(topEntry.target.id);
      }
    }, options);

    items.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observerRef.current!.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, [items, scrollContainerSelector]);

  if (items.length === 0) return null;

  const handleClick = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setActiveId(id);
  };

  return (
    // 手機完全隱藏（md 以上才顯示）
    <div
      className="hidden md:flex"
      style={{
        position: 'fixed',
        top: '50%',
        right: 0,
        transform: 'translateY(-50%)',
        zIndex: 50,
        // 展開時需要有足夠空間，收合時極細
        flexDirection: 'column',
        alignItems: 'flex-end',
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 外層容器：平時顯示細條，hover 後展開面板 */}
      <div
        style={{
          // 寬度過渡動畫
          width: isHovered ? '200px' : '36px',
          maxHeight: isHovered ? '80vh' : '120px',
          transition: 'width 0.28s cubic-bezier(0.4,0,0.2,1), max-height 0.28s cubic-bezier(0.4,0,0.2,1), opacity 0.2s',
          overflowY: isHovered ? 'auto' : 'hidden',
          overflowX: 'hidden',
          borderRadius: isHovered ? '12px 0 0 12px' : '8px 0 0 8px',
          backgroundColor: isHovered
            ? 'rgba(34, 25, 16, 0.96)'
            : 'rgba(242, 127, 13, 0.25)',
          // 細條版邊框
          border: isHovered
            ? '1px solid rgba(242,127,13,0.4)'
            : '1px solid rgba(242,127,13,0.5)',
          borderRight: 'none',
          backdropFilter: 'blur(8px)',
          boxShadow: isHovered
            ? '-4px 0 24px rgba(0,0,0,0.5), -1px 0 0 rgba(242,127,13,0.2)'
            : '-2px 0 12px rgba(0,0,0,0.3)',
          padding: isHovered ? '10px 0' : '0',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(242,127,13,0.3) transparent',
        }}
        // scrollbar 樣式用 CSS-in-JS 無法設定偽元素，改用 global class 處理
        className="floating-toc-panel cursor-pointer"
      >
        {/* 收合狀態：顯示小圖示提示 */}
        {!isHovered && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '120px',
              width: '100%',
              opacity: 0.9,
            }}
          >
            <span
              className="material-symbols-outlined"
              style={{ fontSize: '22px', color: '#f27f0d' }}
            >
              format_list_bulleted
            </span>
          </div>
        )}

        {/* 展開狀態：顯示目錄清單 */}
        {isHovered && (
          <nav aria-label="頁面目錄">
            {/* 標題列 */}
            <div
              style={{
                padding: '4px 14px 8px',
                borderBottom: '1px solid rgba(242,127,13,0.2)',
                marginBottom: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: '14px', color: '#f27f0d' }}
              >
                toc
              </span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 900,
                  color: '#f27f0d',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                }}
              >
                目錄 / Contents
              </span>
            </div>

            {/* 目錄項目清單 */}
            <ul style={{ listStyle: 'none', padding: '0 6px', margin: 0 }}>
              {items.map((item) => {
                const isActive = activeId === item.id;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => handleClick(item.id)}
                      title={item.label}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '5px 8px',
                        border: 'none',
                        borderRadius: '6px',
                        background: isActive
                          ? 'rgba(242,127,13,0.18)'
                          : 'transparent',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'background 0.15s',
                        // 活動項目左邊顯示橘色指示條
                        borderLeft: isActive
                          ? '2px solid #f27f0d'
                          : '2px solid transparent',
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLButtonElement).style.background =
                            'rgba(242,127,13,0.08)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLButtonElement).style.background =
                            'transparent';
                        }
                      }}
                    >
                      {/* 圖示 */}
                      {item.icon && (
                        <span
                          className="material-symbols-outlined"
                          style={{
                            fontSize: '14px',
                            color: isActive ? '#f27f0d' : '#9ca3af',
                            flexShrink: 0,
                            transition: 'color 0.15s',
                          }}
                        >
                          {item.icon}
                        </span>
                      )}
                      {/* 標籤文字 */}
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: isActive ? 700 : 400,
                          color: isActive ? '#f27f0d' : '#d1d5db',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          transition: 'color 0.15s, font-weight 0.1s',
                          lineHeight: 1.4,
                        }}
                      >
                        {item.label}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
        )}
      </div>
    </div>
  );
}
