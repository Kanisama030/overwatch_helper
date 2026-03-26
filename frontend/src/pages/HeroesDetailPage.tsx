/**
 * HeroesDetailPage
 * 英雄全資訊詳情頁（按 overwatch_master Guide section 1~8 順序完整呈現）
 * 與 HeroDetailPage 的差異：不看地圖、按指南原始順序 1~8 排列全部 section
 */
import { useState, useMemo, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useDataset } from '../contexts/dataContextStore';
import { useLocale } from '../contexts/localeContextStore';
import { getHeroById, normalizeHeroIdentifier, toMarkdown } from '../data/selectors';
import { TierBadge } from '../components/common/TierBadge';
import { HeroImage } from '../components/common/HeroImage';
import { MarkdownContent } from '../components/common/MarkdownContent';
import { FloatingTOC } from '../components/common/FloatingTOC';
import { useHeroTranslation } from '../hooks/useHeroTranslation';
import type { GuideSection } from '../types';

// ── 通用樣式常數 ──
const textCls = 'text-base leading-relaxed text-white mb-3 last:mb-0';
const listItemCls = 'text-base leading-relaxed text-gray-200';
const imgCls = 'inline-block align-text-bottom w-6 h-6 md:w-7 md:h-7 mx-1 my-0 rounded-sm border border-white/10 object-contain transition-transform duration-200 hover:scale-[2.6] hover:z-10 relative cursor-zoom-in';

// ── 工具函式 ──
function getRoleLabel(locale: string, role: string, t: ReturnType<typeof useLocale>['t']) {
  if (locale !== 'zh-TW') return role;
  if (role === 'Tank') return t.heroes.filterTank;
  if (role === 'Damage') return t.heroes.filterDamage;
  if (role === 'Support') return t.heroes.filterSupport;
  return role;
}

/**
 * 將扁平 guide sections 依頂層 id（1, 2, 3...）分組
 * 回傳 [{ topSection, children }]
 */
function groupSections(sections: GuideSection[]) {
  const groups: { topSection: GuideSection; children: GuideSection[] }[] = [];
  let currentGroup: { topSection: GuideSection; children: GuideSection[] } | null = null;

  for (const s of sections) {
    if (!s.id.includes('.')) {
      // 頂層 section（1, 2, 3...）
      currentGroup = { topSection: s, children: [] };
      groups.push(currentGroup);
    } else if (currentGroup) {
      currentGroup.children.push(s);
    }
  }
  return groups;
}

// ── Section icon 對照 ──
function getSectionIcon(sectionId: string): string {
  const icons: Record<string, string> = {
    '1': 'auto_awesome',
    '2': 'summarize',
    '3': 'insights',
    '4': 'joystick',
    '5': 'star',
    '6': 'map',
    '7': 'groups',
    '8': 'swords',
  };
  return icons[sectionId] || 'article';
}

function getSectionTitle(id: string, originalTitle: string | undefined, locale: string, t: ReturnType<typeof useLocale>['t']): string {
  if (!originalTitle) return '';
  if (locale !== 'zh-TW') return originalTitle;
  const map: Record<string, string> = {
    '1': t.hero.overview,
    '2': t.hero.strengthsAndWeaknessesSummarized,
    '3': t.hero.strengthsAndWeaknessesExplained,
    '4': t.hero.abilityTips,
    '5': t.hero.perks,
    '6': t.nav.maps,
    '6.1': 'Best Maps',
    '6.2': 'Worst Maps',
    '7': t.hero.teamCompSynergies,
    '8': t.hero.howToCounter,
    '8.2': '特定英雄反制',
  };
  return map[id] || originalTitle;
}

// ── 單一子 section 渲染 ──
function ChildSection({
  section,
  translatedSections,
  translationLoading,
  locale,
  depth,
  dataset,
  t,
}: {
  section: GuideSection;
  translatedSections: Record<string, { title?: string; content: string[] }> | null;
  translationLoading: boolean;
  locale: string;
  depth: number;
  dataset: import('../types').AppDataset;
  t: ReturnType<typeof useLocale>['t'];
}) {
  const translated = translatedSections?.[section.id];
  const title = getSectionTitle(section.id, translated?.title || section.title, locale, t);
  const content = translated?.content ?? section.content ?? [];
  const md = toMarkdown(content);
  const isTranslating = locale === 'zh-TW' && translationLoading && !translated;

  // 判斷是否為分組標題（無 content）
  const isGroupHeader = !section.content || section.content.length === 0;
  if (isGroupHeader && !isTranslating) {
    // 像 3.1（Strengths）、3.2（Weaknesses）、5.1（Minor Perks）等純標題
    return (
      <p
        className="text-xs font-black uppercase tracking-widest mt-4 mb-2"
        style={{ color: depth <= 1 ? '#f27f0d' : '#d97706' }}
      >
        {title}
      </p>
    );
  }

  // 處理 8.2 特定英雄清單：轉為英雄卡片
  if (section.id === '8.2') {
    // 永遠用原本的英文 content 來解析 ID，避免翻譯破壞
    const origContent = section.content ?? [];
    const merged = origContent.join(' ');
    const names = merged.split(/[\s,]+/);
    
    // 手動做 normalize 或引入 normalizeHeroIdentifier
    const validIds = Array.from(new Set(
      names.map(name => {
        const normalized = name.toLowerCase().trim();
        if (!normalized) return null;
        if (dataset.heroes.some(h => h.id === normalized)) return normalized;
        const byName = dataset.heroes.find(h => h.en.toLowerCase() === normalized);
        if (byName) return byName.id;
        const bySlug = dataset.heroes.find(h => h.en.toLowerCase().replace(/[.\s]+/g, '-') === normalized);
        if (bySlug) return bySlug.id;
        return null;
      }).filter((id): id is string => id !== null)
    ));

    const heroes = validIds.map(id => dataset.heroes.find(h => h.id === id)).filter((h): h is import('../types').HeroSummary => !!h);

    return (
      <div
        className="rounded p-4 mb-2"
        style={{
          border: '1px solid rgba(242,127,13,0.15)',
          backgroundColor: 'rgba(242,127,13,0.04)',
        }}
      >
        {title && (
          <p className="text-base font-bold text-white mb-3">{title}</p>
        )}
        {isTranslating ? (
          <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
        ) : heroes.length > 0 ? (
          <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-8 gap-2">
            {heroes.map(hero => (
              <div
                key={hero.id}
                className="relative cursor-default rounded-lg overflow-hidden transition-all"
                style={{
                  border: '1px solid rgba(242,127,13,0.3)',
                  backgroundColor: 'rgba(242,127,13,0.08)'
                }}
              >
                <div className="relative" style={{ aspectRatio: '1/1' }}>
                  <HeroImage heroId={hero.id} heroName={locale === 'zh-TW' ? (hero.zh ?? hero.en) : hero.en} className="w-full h-full object-cover object-top opacity-90" />
                </div>
                <div className="px-1.5 py-1 text-center" style={{ background: 'linear-gradient(to top, rgba(34,25,16,0.95), transparent)' }}>
                  <p className="text-[9px] text-white font-bold truncate">{locale === 'zh-TW' ? (hero.zh ?? hero.en) : hero.en}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm" style={{ color: '#6b7280' }}>無資料</p>
        )}
      </div>
    );
  }

  return (
    <div
      className="rounded p-3 mb-2"
      style={{
        border: '1px solid rgba(242,127,13,0.15)',
        backgroundColor: 'rgba(242,127,13,0.04)',
      }}
    >
      {title && (
        <p className="text-base font-bold text-white mb-2">{title}</p>
      )}
      {isTranslating ? (
        <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
      ) : md ? (
        <MarkdownContent
          content={md}
          textClassName={textCls}
          listItemClassName={listItemCls}
          imageClassName={imgCls}
        />
      ) : null}
    </div>
  );
}

// ── 2. 優缺點總結 (Summarized) ──
function SummarizedCard({
  group,
  translatedSections,
  translationLoading,
  locale
}: {
  group: { topSection: GuideSection; children: GuideSection[] };
  translatedSections: Record<string, { title?: string; content: string[] }> | null;
  translationLoading: boolean;
  locale: string;
}) {
  const { topSection } = group;
  const translated = translatedSections?.[topSection.id];
  const title = translated?.title || topSection.title;
  const isTranslating = locale === 'zh-TW' && translationLoading && !translated;

  const contentItems = (translated?.content ?? topSection.content ?? [])
    .map(item => item.replace(/^\s*[*•-]\s*/, '').trim())
    .filter(Boolean);

  if (contentItems.length === 0 && !isTranslating) return null;

  return (
    // 錨點 id 供 TOC 跳轉使用
    <div id={`section-${topSection.id}`} className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>summarize</span>
        <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>2. {title}</span>
      </div>
      {isTranslating ? (
        <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
          {contentItems.map((item, idx) => (
            <div
              key={`${item}-${idx}`}
              className="rounded p-3 text-center text-lg font-bold leading-tight"
              style={{ border: '1px solid rgba(242,127,13,0.2)', backgroundColor: 'rgba(242,127,13,0.08)', color: '#e5e7eb' }}
            >
              <MarkdownContent
                content={item}
                textClassName="text-lg font-bold leading-tight mb-0"
                listItemClassName={listItemCls}
                imageClassName={imgCls}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 3. 優缺點詳解 (Explained) ──
function ExplainedCard({
  group,
  translatedSections,
  translationLoading,
  locale,
  t
}: {
  group: { topSection: GuideSection; children: GuideSection[] };
  translatedSections: Record<string, { title?: string; content: string[] }> | null;
  translationLoading: boolean;
  locale: string;
  t: ReturnType<typeof useLocale>['t'];
}) {
  const { topSection, children } = group;
  const topTranslated = translatedSections?.[topSection.id];
  const title = topTranslated?.title || topSection.title;
  const isTopTranslating = locale === 'zh-TW' && translationLoading && !topTranslated;

  const strengths = children.filter(c => c.id.startsWith('3.1.') && c.id !== '3.1');
  const weaknesses = children.filter(c => c.id.startsWith('3.2.') && c.id !== '3.2');
  const overview = toMarkdown(topTranslated?.content ?? topSection.content ?? []);

  return (
    // 錨點 id 供 TOC 跳轉使用
    <div id={`section-${topSection.id}`} className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>insights</span>
        <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>3. {title}</span>
      </div>
      
      {isTopTranslating && <p className="text-sm animate-pulse mb-3" style={{ color: '#9ca3af' }}>翻譯中...</p>}
      {!isTopTranslating && overview && (
        <MarkdownContent
          content={overview}
          className="mb-3"
          textClassName={textCls}
          listItemClassName={listItemCls}
          imageClassName={imgCls}
        />
      )}

      {strengths.length > 0 && (
        <div className="space-y-3 mb-4">
          <p className="text-xs font-black uppercase tracking-widest" style={{ color: '#22c55e' }}>{t.hero.strengths}</p>
          {strengths.map(item => {
            const trans = translatedSections?.[item.id];
            const itemTitle = trans?.title || item.title;
            const md = toMarkdown(trans?.content ?? item.content ?? []);
            const isTranslating = locale === 'zh-TW' && translationLoading && !trans;

            return (
              <div key={item.id} className="rounded p-3" style={{ border: '1px solid rgba(34,197,94,0.25)', backgroundColor: 'rgba(34,197,94,0.08)' }}>
                {isTranslating ? (
                  <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
                ) : (
                  <>
                    {itemTitle && <p className="text-lg font-bold mb-2 text-white">{itemTitle}</p>}
                    <MarkdownContent
                      content={md}
                      textClassName={textCls}
                      listItemClassName={listItemCls}
                      imageClassName={imgCls}
                    />
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}

      {weaknesses.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-black uppercase tracking-widest" style={{ color: '#ef4444' }}>{t.hero.weaknesses}</p>
          {weaknesses.map(item => {
            const trans = translatedSections?.[item.id];
            const itemTitle = trans?.title || item.title;
            const md = toMarkdown(trans?.content ?? item.content ?? []);
            const isTranslating = locale === 'zh-TW' && translationLoading && !trans;

            return (
              <div key={item.id} className="rounded p-3" style={{ border: '1px solid rgba(239,68,68,0.25)', backgroundColor: 'rgba(239,68,68,0.08)' }}>
                {isTranslating ? (
                  <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
                ) : (
                  <>
                    {itemTitle && <p className="text-lg font-bold mb-2 text-white">{itemTitle}</p>}
                    <MarkdownContent
                      content={md}
                      textClassName={textCls}
                      listItemClassName={listItemCls}
                      imageClassName={imgCls}
                    />
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── 5. Perks ──
function PerksCard({
  group,
  translatedSections,
  translationLoading,
  locale,
  t
}: {
  group: { topSection: GuideSection; children: GuideSection[] };
  translatedSections: Record<string, { title?: string; description?: string; content: string[] }> | null;
  translationLoading: boolean;
  locale: string;
  t: ReturnType<typeof useLocale>['t'];
}) {
  const { topSection, children } = group;
  const topTranslated = translatedSections?.[topSection.id];
  const groupTitle = topTranslated?.title || topSection.title;
  
  const minorPerks = children.filter(c => c.id.startsWith('5.1.') && c.id !== '5.1').map(p => ({ ...p, perkType: 'minor' as const }));
  const majorPerks = children.filter(c => c.id.startsWith('5.2.') && c.id !== '5.2').map(p => ({ ...p, perkType: 'major' as const }));
  const allPerks = [...minorPerks, ...majorPerks];

  const [expandedPerkIds, setExpandedPerkIds] = useState<Record<string, boolean>>({});
  const togglePerk = (key: string) => {
    setExpandedPerkIds(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (allPerks.length === 0) return null;

  return (
    // 錨點 id 供 TOC 跳轉使用
    <div id={`section-${topSection.id}`} className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
      <div className="flex items-center gap-2 mb-4">
        <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>star</span>
        <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>5. {groupTitle}</span>
      </div>
      
      <div className="space-y-3">
        {allPerks.map((perk, i) => {
          const key = perk.id;
          const isExpanded = !!expandedPerkIds[key] || i === 0; // 預設展開第一個
          
          const trans = translatedSections?.[perk.id] as { title?: string; description?: string; content: string[] } | undefined;
          const isTranslating = locale === 'zh-TW' && translationLoading && !trans;
          
          const title = trans?.title || perk.title;
          const description = trans?.description || perk.description;
          const md = toMarkdown(trans?.content ?? perk.content ?? []);

          return (
            <div key={key} className="rounded overflow-hidden" style={{ border: '1px solid rgba(242,127,13,0.2)', backgroundColor: 'rgba(242,127,13,0.08)' }}>
              <button
                type="button"
                onClick={() => togglePerk(key)}
                className="w-full text-left p-3 md:p-4 flex items-start gap-2 touch-manipulation"
                style={{ minHeight: '52px' }}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-black px-1.5 py-0.5 rounded" style={perk.perkType === 'minor' ? { backgroundColor: 'rgba(242,127,13,0.3)', color: '#f27f0d' } : { backgroundColor: 'rgba(242,127,13,0.5)', color: '#221910' }}>
                      {perk.perkType === 'minor' ? t.hero.minorPerks : t.hero.majorPerks}
                    </span>
                    <h5 className="text-base font-bold truncate min-w-0" style={{ color: '#f27f0d' }}>
                      {title}
                    </h5>
                  </div>
                </div>
                <span className="material-symbols-outlined text-base mt-0.5" style={{ color: '#f27f0d' }}>
                  {isExpanded ? 'expand_less' : 'expand_more'}
                </span>
              </button>
              
              {isExpanded && isTranslating && (
                <div className="px-3 md:px-4 pb-4 pt-0">
                  <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
                </div>
              )}
              {isExpanded && !isTranslating && (description || md) && (
                <div className="px-3 md:px-4 pb-4 pt-0">
                  {description && (
                    <p className="text-sm mb-3" style={{ color: '#f5d7b3' }}>{description}</p>
                  )}
                  <MarkdownContent
                    content={md}
                    textClassName={textCls}
                    listItemClassName={listItemCls}
                    imageClassName={imgCls}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 6. Maps（Best / Worst 子清單） ──
function MapsCard({
  group,
  translatedSections,
  translationLoading,
  locale,
  t
}: {
  group: { topSection: GuideSection; children: GuideSection[] };
  translatedSections: Record<string, { title?: string; description?: string; content: string[] }> | null;
  translationLoading: boolean;
  locale: string;
  t: ReturnType<typeof useLocale>['t'];
}) {
  const { topSection, children } = group;
  const topTranslated = translatedSections?.[topSection.id];
  const title = getSectionTitle(topSection.id, topTranslated?.title || topSection.title, locale, t);
  const topMd = toMarkdown(topTranslated?.content ?? topSection.content ?? []);
  const isTopTranslating = locale === 'zh-TW' && translationLoading && !topTranslated;

  const mapGroups = [
    { id: '6.1', accent: '#22c55e', icon: 'trending_up' },
    { id: '6.2', accent: '#ef4444', icon: 'trending_down' },
  ] as const;

  return (
    <div id={`section-${topSection.id}`} className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>map</span>
        <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>6. {title}</span>
      </div>

      {isTopTranslating ? (
        <p className="text-sm animate-pulse mb-3" style={{ color: '#9ca3af' }}>翻譯中...</p>
      ) : topMd ? (
        <div className="mb-3">
          <MarkdownContent
            content={topMd}
            textClassName={textCls}
            listItemClassName={listItemCls}
            imageClassName={imgCls}
          />
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {mapGroups.map(({ id, accent, icon }) => {
          const parent = children.find(c => c.id === id);
          const parentTrans = parent ? translatedSections?.[parent.id] : undefined;
          const parentTitle = getSectionTitle(id, parentTrans?.title || parent?.title || '', locale, t);
          const parentMd = toMarkdown(parentTrans?.content ?? parent?.content ?? []);
          const isParentTranslating = locale === 'zh-TW' && translationLoading && parent && !parentTrans;

          const itemSections = children.filter(c => c.id.startsWith(`${id}.`) && c.id !== id);

          return (
            <div
              key={id}
              className="rounded p-3"
              style={{ border: `1px solid ${accent}40`, backgroundColor: `${accent}12` }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-base" style={{ color: accent }}>{icon}</span>
                <p className="text-xs font-black uppercase tracking-widest" style={{ color: accent }}>
                  {parentTitle}
                </p>
              </div>

              {isParentTranslating ? (
                <p className="text-sm animate-pulse mb-2" style={{ color: '#9ca3af' }}>翻譯中...</p>
              ) : parentMd ? (
                <MarkdownContent
                  content={parentMd}
                  className="mb-2"
                  textClassName={textCls}
                  listItemClassName={listItemCls}
                  imageClassName={imgCls}
                />
              ) : null}

              <div className="space-y-2">
                {itemSections.map((item, idx) => {
                  const trans = translatedSections?.[item.id];
                  const itemTitle = getSectionTitle(item.id, trans?.title || item.title, locale, t);
                  const itemMd = toMarkdown(trans?.content ?? item.content ?? []);
                  const isTranslating = locale === 'zh-TW' && translationLoading && !trans;

                  return (
                    <div
                      key={item.id}
                      className="rounded p-2.5"
                      style={{ border: '1px solid rgba(255,255,255,0.1)', backgroundColor: 'rgba(255,255,255,0.03)' }}
                    >
                      <p className="text-sm font-bold mb-1.5 text-white">
                        {idx + 1}. {itemTitle}
                      </p>
                      {isTranslating ? (
                        <p className="text-sm animate-pulse" style={{ color: '#9ca3af' }}>翻譯中...</p>
                      ) : itemMd ? (
                        <MarkdownContent
                          content={itemMd}
                          textClassName={textCls}
                          listItemClassName={listItemCls}
                          imageClassName={imgCls}
                        />
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 頂層 section 卡片 ──
function SectionCard({
  topSection,
  children,
  translatedSections,
  translationLoading,
  locale,
  defaultExpanded,
  dataset,
  t,
}: {
  topSection: GuideSection;
  children: GuideSection[];
  translatedSections: Record<string, { title?: string; content: string[] }> | null;
  translationLoading: boolean;
  locale: string;
  defaultExpanded: boolean;
  dataset: import('../types').AppDataset;
  t: ReturnType<typeof useLocale>['t'];
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const icon = getSectionIcon(topSection.id);
  const translated = translatedSections?.[topSection.id];
  const title = getSectionTitle(topSection.id, translated?.title || topSection.title, locale, t);
  const topContent = translated?.content ?? topSection.content ?? [];
  const topMd = toMarkdown(topContent);
  const isTranslating = locale === 'zh-TW' && translationLoading && !translated;

  return (
    // 錨點 id 供 TOC 跳轉使用
    <div
      id={`section-${topSection.id}`}
      className="rounded-lg overflow-hidden"
      style={{
        backgroundColor: 'rgba(242,127,13,0.05)',
        border: '1px solid rgba(242,127,13,0.15)',
      }}
    >
      {/* 標題列（可收合） */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left touch-manipulation"
      >
        <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>{icon}</span>
        <span className="flex-1 text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>
          {topSection.id}. {title}
        </span>
        <span className="material-symbols-outlined text-base" style={{ color: '#f27f0d' }}>
          {expanded ? 'expand_less' : 'expand_more'}
        </span>
      </button>

      {/* 展開的內容 */}
      {expanded && (
        <div className="px-4 pb-4">
          {/* 頂層 section 自己的 content */}
          {isTranslating ? (
            <p className="text-sm animate-pulse mb-3" style={{ color: '#9ca3af' }}>翻譯中...</p>
          ) : topMd ? (
            <div className="mb-3">
              <MarkdownContent
                content={topMd}
                textClassName={textCls}
                listItemClassName={listItemCls}
                imageClassName={imgCls}
              />
            </div>
          ) : null}

          {/* 子 sections */}
          {children.map(child => (
            <ChildSection
              key={child.id}
              section={child}
              translatedSections={translatedSections}
              translationLoading={translationLoading}
              locale={locale}
              depth={child.id.split('.').length}
              dataset={dataset}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── 統計指標 ──
function StatPill({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="text-center px-3 py-1 rounded" style={{ backgroundColor: 'rgba(242,127,13,0.1)' }}>
      <p className="text-[10px] uppercase tracking-widest" style={{ color: '#9ca3af' }}>{label}</p>
      <p className="text-sm font-black" style={{ color: '#f27f0d' }}>{value ?? '—'}</p>
    </div>
  );
}

// ── 主元件 ──
export function HeroesDetailPage() {
  const { heroId } = useParams<{ heroId: string }>();
  const { dataset } = useDataset();
  const { locale, t } = useLocale();
  const navigate = useNavigate();

  if (!dataset || !heroId) return null;

  const normalizedHeroId = normalizeHeroIdentifier(heroId, dataset);
  const hero = normalizedHeroId ? getHeroById(dataset, normalizedHeroId) : undefined;

  useEffect(() => {
    if (normalizedHeroId && normalizedHeroId !== heroId) {
      navigate(`/heroes-list/${normalizedHeroId}`, { replace: true });
    }
  }, [heroId, normalizedHeroId, navigate]);

  if (!hero) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: '#9ca3af' }}>
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl block mb-2">person_off</span>
          <p>{t.hero.heroNotFound}</p>
        </div>
      </div>
    );
  }

  const heroName = locale === 'zh-TW' ? (hero.zh ?? hero.en) : hero.en;
  const roleLabel = getRoleLabel(locale, hero.role, t);
  const {
    sections: translatedSections,
    loading: translationLoading,
  } = useHeroTranslation(hero.id, locale, locale === 'zh-TW');

  // 依頂層 id 分組
  const guide = hero.guide ?? [];
  const sectionGroups = useMemo(() => groupSections(guide), [guide]);

  // 構建 TOC 項目（僅含頂層 section）
  const tocItems = useMemo(() => {
    return sectionGroups.map(({ topSection }) => ({
      id: `section-${topSection.id}`,
      label: `${topSection.id}. ${getSectionTitle(topSection.id, topSection.title, locale, t)}`,
      icon: getSectionIcon(topSection.id),
    }));
  }, [sectionGroups, locale, t]);

  return (
    <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide min-h-0">
      {/* 麵包屑 */}
      <div className="px-4 md:px-8 pt-6 pb-2">
        <nav className="text-xs" style={{ color: '#6b7280' }}>
          <Link to="/heroes-list" style={{ color: '#f27f0d' }}>{t.nav.heroesPage}</Link>
          <span className="mx-2">›</span>
          <span className="text-white">{heroName}</span>
        </nav>
      </div>

      {/* Hero Header */}
      <div className="px-4 md:px-8 pb-4">
        <div
          className="rounded-lg p-4 md:p-6 flex flex-col sm:flex-row items-start gap-6"
          style={{ background: 'linear-gradient(135deg, #3d2a10, #221910)', border: '1px solid rgba(242,127,13,0.3)' }}
        >
          {/* 頭像 */}
          <div
            className="relative w-32 h-32 md:w-40 md:h-40 rounded-lg overflow-hidden flex-shrink-0"
            style={{ border: '3px solid rgba(242,127,13,0.5)' }}
          >
            <HeroImage heroId={hero.id} heroName={heroName} className="w-full h-full object-cover object-top" />
          </div>

          {/* 資訊 */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <TierBadge tier={hero.tier} />
              <span
                className="text-xs px-2 py-0.5 rounded font-bold uppercase"
                style={{ backgroundColor: 'rgba(255,255,255,0.1)', color: '#9ca3af' }}
              >
                {roleLabel}
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black text-white uppercase tracking-tight mb-3">{heroName}</h1>
            <div className="flex flex-wrap gap-3">
              <StatPill
                label={t.heroes.winRate}
                value={hero.default_win_rate != null ? `${hero.default_win_rate.toFixed(1)}%` : null}
              />
              <StatPill
                label={t.heroes.pickRate}
                value={hero.default_pick_rate != null ? `${hero.default_pick_rate.toFixed(1)}%` : null}
              />
            </div>
          </div>

          {/* 返回列表 */}
          <button
            onClick={() => navigate('/heroes-list')}
            className="px-4 py-2.5 rounded text-xs font-bold uppercase tracking-wider transition-all self-start"
            style={{ backgroundColor: 'rgba(242,127,13,0.15)', color: '#f27f0d', border: '1px solid rgba(242,127,13,0.3)' }}
          >
            <span className="material-symbols-outlined text-sm align-middle mr-1">arrow_back</span>
            {t.nav.heroesPage}
          </button>
        </div>
      </div>

      {/* Guide sections 1~8 */}
      <div className="px-4 md:px-8 pb-8 space-y-3">
        {sectionGroups.map((group, idx) => {
          if (group.topSection.id === '2') {
            return <SummarizedCard key={group.topSection.id} group={group} translatedSections={translatedSections} translationLoading={translationLoading} locale={locale} />;
          }
          if (group.topSection.id === '3') {
            return <ExplainedCard key={group.topSection.id} group={group} translatedSections={translatedSections} translationLoading={translationLoading} locale={locale} t={t} />;
          }
          if (group.topSection.id === '5') {
            return <PerksCard key={group.topSection.id} group={group} translatedSections={translatedSections} translationLoading={translationLoading} locale={locale} t={t} />;
          }
          if (group.topSection.id === '6') {
            return <MapsCard key={group.topSection.id} group={group} translatedSections={translatedSections} translationLoading={translationLoading} locale={locale} t={t} />;
          }

          return (
            <SectionCard
              key={group.topSection.id}
              topSection={group.topSection}
              children={group.children}
              translatedSections={translatedSections}
              translationLoading={translationLoading}
              locale={locale}
              defaultExpanded={idx < 3}
              dataset={dataset}
              t={t}
            />
          );
        })}
      </div>

      {/* 浮動目錄導覽 */}
      <FloatingTOC items={tocItems} />
    </div>
  );
}
