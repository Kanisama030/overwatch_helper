import { useState, useMemo } from 'react';
import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom';
import { useDataset } from '../contexts/dataContextStore';
import { 
  getHeroById, getMapById, getHeroWinRateForMap,
  extractCounterHeroIds, sortHeroes, toMarkdown
} from '../data/selectors';
import { TierBadge } from '../components/common/TierBadge';
import { HeroImage } from '../components/common/HeroImage';
import { MarkdownContent } from '../components/common/MarkdownContent';
import type { HeroSummary, AppDataset } from '../types';

type Tab = 'strategy' | 'counter';

function StatPill({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="text-center px-3 py-1 rounded" style={{ backgroundColor: 'rgba(242,127,13,0.1)' }}>
      <p className="text-[10px] uppercase tracking-widest" style={{ color: '#9ca3af' }}>{label}</p>
      <p className="text-sm font-black" style={{ color: '#f27f0d' }}>{value ?? '—'}</p>
    </div>
  );
}

function StrategyTab({ hero }: { hero: HeroSummary }) {
  const playAsMarkdown = toMarkdown(hero.counter_data.play_as || []);
  const mapSuggestionMarkdown = (hero.map_recommendations.maps_summary || '').trim();
  const teamCompMarkdown = toMarkdown(hero.counter_data.team_comp_synergies || []);
  const strengthsSummaryItems = (hero.counter_data.strengths_weaknesses_summarized || [])
    .map(item => item.replace(/^\s*[*•-]\s*/, '').trim())
    .filter(Boolean);
  const explained = hero.counter_data.strengths_weaknesses_explained;
  const explainedOverviewMarkdown = toMarkdown(explained?.overview || []);
  const explainedStrengths = (explained?.strengths || []).filter(item => item.title.trim().toLowerCase() !== 'strengths');
  const explainedWeaknesses = (explained?.weaknesses || []).filter(item => item.title.trim().toLowerCase() !== 'weaknesses');
  const heroAnalysisTextClass = 'text-base leading-relaxed text-white mb-3 last:mb-0';
  const heroAnalysisListItemClass = 'text-base leading-relaxed text-gray-200';
  const heroAnalysisImageClass = 'inline-block align-text-bottom w-6 h-6 md:w-7 md:h-7 mx-1 my-0 rounded-sm border border-white/10 object-contain transition-transform duration-200 hover:scale-[2.6] hover:z-10 relative cursor-zoom-in';

  const minorPerks = hero.perks?.minor || [];
  const majorPerks = hero.perks?.major || [];
  const allPerks = [
    ...minorPerks.map(perk => ({ ...perk, perkType: 'minor' as const })),
    ...majorPerks.map(perk => ({ ...perk, perkType: 'major' as const })),
  ];
  const [expandedPerkIds, setExpandedPerkIds] = useState<Record<string, boolean>>({});

  const togglePerk = (key: string) => {
    setExpandedPerkIds(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const renderCard = (title: string, icon: string, markdown: string) => {
    if (!markdown) return null;
    return (
      <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>{icon}</span>
          <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>{title}</span>
        </div>
        <MarkdownContent
          content={markdown}
          textClassName={heroAnalysisTextClass}
          listItemClassName={heroAnalysisListItemClass}
          imageClassName={heroAnalysisImageClass}
        />
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {allPerks.length > 0 && (
        <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
          <div className="flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>star</span>
            <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>Perks</span>
          </div>
          <div className="space-y-3">
            {allPerks.map((perk, i) => {
              const key = `${perk.perkType}-${perk.id || i}`;
              const isExpanded = !!expandedPerkIds[key];
              const recommendedReason = perk.recommended_reason || null;
              const perkMarkdown = toMarkdown(perk.content || []);
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
                          {perk.perkType.toUpperCase()}
                        </span>
                        {perk.recommended_flag && (
                          <span className="text-[10px] font-black px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(34,197,94,0.25)', color: '#22c55e' }}>
                            Recommended
                          </span>
                        )}
                        <h5 className="text-base font-bold truncate" style={{ color: '#f27f0d' }}>{perk.title}</h5>
                      </div>
                      {recommendedReason && (
                        <p className="text-xs mt-1 font-bold" style={{ color: '#22c55e' }}>{recommendedReason}</p>
                      )}
                    </div>
                    <span className="material-symbols-outlined text-base mt-0.5" style={{ color: '#f27f0d' }}>
                      {isExpanded ? 'expand_less' : 'expand_more'}
                    </span>
                  </button>
                  {isExpanded && perkMarkdown && (
                    <div className="px-3 md:px-4 pb-4 pt-0">
                      <MarkdownContent
                        content={perkMarkdown}
                        textClassName={heroAnalysisTextClass}
                        listItemClassName={heroAnalysisListItemClass}
                        imageClassName={heroAnalysisImageClass}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="rounded-lg p-4" style={{ backgroundColor: '#1a1208', border: '1px solid rgba(242,127,13,0.15)' }}>
        <div className="flex items-center gap-2 mb-2">
          <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>psychology</span>
          <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>Gemini AI Analysis</span>
          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: 'rgba(107,114,128,0.3)', color: '#9ca3af' }}>COMING SOON</span>
        </div>
        <p className="text-sm" style={{ color: '#6b7280' }}>
          AI tactical analysis will be available in a future update. Powered by Gemini Flash.
        </p>
      </div>

      {renderCard('TLDR', 'auto_awesome', playAsMarkdown)}
      {renderCard('Map Suggestion', 'map', mapSuggestionMarkdown)}
      {renderCard('Team Comp Synergies', 'groups', teamCompMarkdown)}
      {strengthsSummaryItems.length > 0 && (
        <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>summarize</span>
            <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>Strengths And Weaknesses Summarized</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            {strengthsSummaryItems.map((item, idx) => (
              <div
                key={`${item}-${idx}`}
                className="rounded p-3 text-center text-lg font-bold leading-tight"
                style={{ border: '1px solid rgba(242,127,13,0.2)', backgroundColor: 'rgba(242,127,13,0.08)', color: '#e5e7eb' }}
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {(explainedOverviewMarkdown || explainedStrengths.length > 0 || explainedWeaknesses.length > 0) && (
        <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>insights</span>
            <span className="text-sm font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>Strengths And Weaknesses Explained</span>
          </div>
          {explainedOverviewMarkdown && (
            <MarkdownContent
              content={explainedOverviewMarkdown}
              className="mb-3"
              textClassName={heroAnalysisTextClass}
              listItemClassName={heroAnalysisListItemClass}
              imageClassName={heroAnalysisImageClass}
            />
          )}
          {explainedStrengths.length > 0 && (
            <div className="space-y-3 mb-4">
              <p className="text-xs font-black uppercase tracking-widest" style={{ color: '#22c55e' }}>Strengths</p>
              {explainedStrengths.map(item => (
                <div key={item.id} className="rounded p-3" style={{ border: '1px solid rgba(34,197,94,0.25)', backgroundColor: 'rgba(34,197,94,0.08)' }}>
                  {item.title && <p className="text-lg font-bold mb-2 text-white">{item.title}</p>}
                  <MarkdownContent
                    content={toMarkdown(item.content)}
                    textClassName={heroAnalysisTextClass}
                    listItemClassName={heroAnalysisListItemClass}
                    imageClassName={heroAnalysisImageClass}
                  />
                </div>
              ))}
            </div>
          )}
          {explainedWeaknesses.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-black uppercase tracking-widest" style={{ color: '#ef4444' }}>Weaknesses</p>
              {explainedWeaknesses.map(item => (
                <div key={item.id} className="rounded p-3" style={{ border: '1px solid rgba(239,68,68,0.25)', backgroundColor: 'rgba(239,68,68,0.08)' }}>
                  {item.title && <p className="text-lg font-bold mb-2 text-white">{item.title}</p>}
                  <MarkdownContent
                    content={toMarkdown(item.content)}
                    textClassName={heroAnalysisTextClass}
                    listItemClassName={heroAnalysisListItemClass}
                    imageClassName={heroAnalysisImageClass}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CounterTab({ hero, dataset, mapId, navigate }: { 
  hero: HeroSummary; 
  dataset: AppDataset | null; 
  mapId: string | null;
  navigate: ReturnType<typeof useNavigate>;
}) {
  // Threats to You 改用 8.2 Specific Hero Counters，排除自身
  const threatIds = useMemo(() => {
    if (!dataset) return [];
    const counters82 = hero.counter_data.specific_counters_82 || [];
    const ids = extractCounterHeroIds(counters82, dataset);
    // 排除自己
    return ids.filter(id => id !== hero.id);
  }, [hero, dataset]);

  const threats = useMemo(() => {
    if (!dataset) return [];
    return threatIds.map(id => getHeroById(dataset, id)).filter((h): h is HeroSummary => h !== undefined);
  }, [threatIds, dataset]);

  // Threat 選單預設使用第一個（不強制寫回 state）
  const [selectedThreatId, setSelectedThreatId] = useState<string | null>(null);
  const [pendingSwapId, setPendingSwapId] = useState<string | null>(null);
  const effectiveThreatId = selectedThreatId ?? threats[0]?.id ?? null;
  const selectedThreat = dataset && effectiveThreatId ? getHeroById(dataset, effectiveThreatId) : null;

  // How to Fight Back 改為：顯示被選中的 threat 英雄其 1.1.2 Play Against 內容
  const fightBackMarkdown = useMemo(() => {
    if (!selectedThreat) return '';
    const playAgainst = selectedThreat.counter_data.play_against || selectedThreat.counter_data.play_against_summary || [];
    return toMarkdown(playAgainst);
  }, [selectedThreat]);

  // Recommended Swaps 改為：顯示被選中的 threat 英雄其 8.2 Specific Hero Counters，並按 tier->勝率排序
  const recommendedSwaps = useMemo(() => {
    if (!dataset || !selectedThreat) return [];
    const counters82 = selectedThreat.counter_data.specific_counters_82 || [];
    const ids = extractCounterHeroIds(counters82, dataset);
    const swaps = ids.map(id => getHeroById(dataset, id)).filter((h): h is HeroSummary => h !== undefined);
    // 按 tier->勝率排序
    return sortHeroes(swaps, 'tier_then_winrate').slice(0, 6);
  }, [selectedThreat, dataset]);

  if (!dataset) return null;

  const handleConfirmSwap = () => {
    if (pendingSwapId) {
      navigate(`/hero/${pendingSwapId}${mapId ? `?map=${mapId}` : ''}`);
      setPendingSwapId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* 移除 Disclaimer */}
      
      {/* Threats to You - 改用更小的英雄卡片，移除不透明遮罩 */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-lg" style={{ color: '#ef4444' }}>warning</span>
          <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#ef4444' }}>Threats to You</span>
          <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(239,68,68,0.2)' }} />
        </div>
        {threats.length === 0 ? (
          <p className="text-sm" style={{ color: '#6b7280' }}>No specific threat data available.</p>
        ) : (
          <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-8 gap-2">
            {threats.map(threat => (
              <div
                key={threat.id}
                  onClick={() => setSelectedThreatId(threat.id)}
                className="relative cursor-pointer rounded-lg overflow-hidden transition-all"
                style={{
                    border: effectiveThreatId === threat.id ? '2px solid #ef4444' : '1px solid rgba(239,68,68,0.3)',
                    backgroundColor: effectiveThreatId === threat.id ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.08)'
                  }}
                >
                  <div className="relative" style={{ aspectRatio: '1/1' }}>
                    <HeroImage heroId={threat.id} heroName={threat.en} className="w-full h-full object-cover object-top" 
                      style={{ opacity: effectiveThreatId === threat.id ? 0.95 : 0.85 }} />
                  </div>
                <div className="px-1.5 py-1 text-center">
                  <p className="text-[9px] text-white font-bold truncate">{threat.en}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How to Fight Back - 顯示選中 threat 的 Play Against */}
      {selectedThreat && fightBackMarkdown.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>swords</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>
              How to Fight Back vs {selectedThreat.en}
            </span>
            <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(242,127,13,0.15)' }} />
          </div>
          <div className="rounded p-3" style={{ border: '1px solid rgba(242,127,13,0.2)', backgroundColor: 'rgba(242,127,13,0.08)' }}>
            <MarkdownContent content={fightBackMarkdown} />
          </div>
        </div>
      )}

      {/* Recommended Swaps - 移除不透明遮罩，改用邊框高亮 */}
      {selectedThreat && recommendedSwaps.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#22c55e' }}>swap_horiz</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#22c55e' }}>
              Recommended Swaps vs {selectedThreat.en}
            </span>
            <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(34,197,94,0.2)' }} />
          </div>
          <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-8 gap-2">
            {recommendedSwaps.map(h => {
              const displayWinRate = mapId ? (getHeroWinRateForMap(h, mapId) ?? h.default_win_rate) : h.default_win_rate;
              const isSelected = pendingSwapId === h.id;
              return (
                <div
                  key={h.id}
                  onClick={() => setPendingSwapId(h.id)}
                  className="relative cursor-pointer rounded-lg overflow-hidden transition-all"
                  style={{
                    border: isSelected ? '2px solid #22c55e' : '1px solid rgba(34,197,94,0.3)',
                    backgroundColor: isSelected ? 'rgba(34,197,94,0.15)' : 'rgba(34,197,94,0.05)'
                  }}
                >
                  <div className="relative" style={{ aspectRatio: '1/1' }}>
                    <HeroImage heroId={h.id} heroName={h.en} className="w-full h-full object-cover object-top" 
                      style={{ opacity: isSelected ? 0.95 : 0.85 }} />
                    <div className="absolute top-1 left-1">
                      <TierBadge tier={h.tier} />
                    </div>
                  </div>
                  <div className="px-1.5 py-1 text-center" style={{ background: 'linear-gradient(to top, rgba(34,25,16,0.95), transparent)' }}>
                    <p className="text-[9px] text-white font-bold truncate">{h.en}</p>
                    {displayWinRate != null && (
                      <p className="text-[8px] mt-0.5" style={{ color: '#22c55e' }}>{displayWinRate.toFixed(1)}% WR</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {pendingSwapId && (
            <div className="mt-4 flex justify-center">
              <button
                onClick={handleConfirmSwap}
                className="px-6 py-2.5 rounded-lg text-sm font-bold uppercase tracking-wider transition-all"
                style={{ backgroundColor: '#22c55e', color: '#221910' }}
              >
                <span className="material-symbols-outlined text-sm align-middle mr-1">check_circle</span>
                Confirm Swap to {getHeroById(dataset, pendingSwapId)?.en}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function HeroDetailPage() {
  const { heroId } = useParams<{ heroId: string }>();
  const [searchParams] = useSearchParams();
  const mapId = searchParams.get('map');
  const { dataset } = useDataset();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('strategy');

  if (!dataset || !heroId) return null;

  const hero = getHeroById(dataset, heroId);
  const map = mapId ? getMapById(dataset, mapId) : null;

  if (!hero) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: '#9ca3af' }}>
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl block mb-2">person_off</span>
          <p>Hero not found</p>
        </div>
      </div>
    );
  }

  const mapWinRate = mapId ? getHeroWinRateForMap(hero, mapId) : null;
  const displayWinRate = mapWinRate ?? hero.default_win_rate;

  return (
    <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide min-h-0">
      {/* Breadcrumbs */}
      <div className="px-4 md:px-8 pt-6 pb-2">
        <nav className="text-xs" style={{ color: '#6b7280' }}>
          <Link to="/" style={{ color: '#f27f0d' }}>Maps</Link>
          {map && (
            <>
              <span className="mx-2">›</span>
              <Link to={`/heroes?map=${mapId}`} style={{ color: '#f27f0d' }}>{map.en}</Link>
            </>
          )}
          <span className="mx-2">›</span>
          <span className="text-white">{hero.en}</span>
        </nav>
      </div>

      {/* Hero Header - 放大英雄圖並調整佈局 */}
      <div className="px-4 md:px-8 pb-4">
        <div className="rounded-lg p-4 md:p-6 flex flex-col sm:flex-row items-start gap-6"
          style={{ background: 'linear-gradient(135deg, #3d2a10, #221910)', border: '1px solid rgba(242,127,13,0.3)' }}>
          {/* Hero portrait - 放大至 160px */}
          <div className="relative w-32 h-32 md:w-40 md:h-40 rounded-lg overflow-hidden flex-shrink-0"
            style={{ border: '3px solid rgba(242,127,13,0.5)' }}>
            <HeroImage heroId={hero.id} heroName={hero.en} className="w-full h-full object-cover object-top" />
          </div>

          {/* Hero info - 視覺上下對齊 */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <TierBadge tier={hero.tier} />
              <span className="text-xs px-2 py-0.5 rounded font-bold uppercase"
                style={{ backgroundColor: 'rgba(255,255,255,0.1)', color: '#9ca3af' }}>
                {hero.role}
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black text-white uppercase tracking-tight mb-3">{hero.en}</h1>
            <div className="flex flex-wrap gap-3">
              <StatPill label="Win Rate" value={displayWinRate != null ? `${displayWinRate.toFixed(1)}%` : null} />
              <StatPill label="Pick Rate" value={hero.default_pick_rate != null ? `${hero.default_pick_rate.toFixed(1)}%` : null} />
              {map && <StatPill label="Map" value={map.en} />}
            </div>
          </div>

          {/* Change hero button */}
          <button
            onClick={() => navigate(map ? `/heroes?map=${mapId}` : '/heroes')}
            className="px-4 py-2.5 rounded text-xs font-bold uppercase tracking-wider transition-all self-start"
            style={{ backgroundColor: 'rgba(242,127,13,0.15)', color: '#f27f0d', border: '1px solid rgba(242,127,13,0.3)' }}>
            <span className="material-symbols-outlined text-sm align-middle mr-1">swap_horiz</span>
            Change Hero
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 md:px-8 pb-2">
        <div className="flex gap-1 p-1 rounded-lg" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
          {([
            { key: 'strategy', label: 'Strategy Overview', icon: 'strategy' },
            { key: 'counter', label: 'Play Against Advisor', icon: 'swords' },
          ] as const).map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded text-xs font-bold uppercase tracking-wider transition-all"
              style={tab === t.key
                ? { backgroundColor: '#f27f0d', color: '#221910' }
                : { color: '#9ca3af' }}
            >
              <span className="material-symbols-outlined text-sm">{t.icon}</span>
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="px-4 md:px-8 pb-8">
        {tab === 'strategy' ? (
          <StrategyTab hero={hero} />
        ) : (
          <CounterTab hero={hero} dataset={dataset} mapId={mapId} navigate={navigate} />
        )}
      </div>
    </div>
  );
}
