import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDataset } from '../contexts/dataContextStore';
import { useLocale } from '../contexts/localeContextStore';
import {
  filterHeroesByRole, sortHeroes,
  getHeroWinRateByModeRank, type SortMode
} from '../data/selectors';
import { TierBadge } from '../components/common/TierBadge';
import { HeroImage } from '../components/common/HeroImage';
import type { AppDataset, CompetitiveRank, HeroSummary, Mode, Role } from '../types';

type RoleFilter = 'ALL' | Role;

// 模式 / 牌位標籤（與 HeroSelectionPage 相同）
const COMPETITIVE_RANKS: CompetitiveRank[] = ['All', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'Grandmaster', 'Champion'];
const MODE_LABELS: Record<Mode, { en: string; zh: string }> = {
  'Quick Play': { en: 'Quick Play', zh: '快速對戰' },
  Competitive: { en: 'Competitive', zh: '競技對戰' },
};
const COMPETITIVE_RANK_LABELS: Record<CompetitiveRank, { en: string; zh: string; index: number }> = {
  All: { en: 'All', zh: '全部', index: 0 },
  Bronze: { en: 'Bronze', zh: '青銅', index: 1 },
  Silver: { en: 'Silver', zh: '白銀', index: 2 },
  Gold: { en: 'Gold', zh: '黃金', index: 3 },
  Platinum: { en: 'Platinum', zh: '白金', index: 4 },
  Diamond: { en: 'Diamond', zh: '鑽石', index: 5 },
  Master: { en: 'Master', zh: '大師', index: 6 },
  Grandmaster: { en: 'Grandmaster', zh: '宗師', index: 7 },
  Champion: { en: 'Champion', zh: '王者', index: 8 },
};

/** 取英雄全地圖（all-maps）勝率：從 mode_rank_stats 取 all-maps 鍵 */
function getHeroAllMapsWinRate(
  dataset: AppDataset,
  heroId: string,
  selectedMode: Mode,
  selectedRank: CompetitiveRank
): number | null {
  return getHeroWinRateByModeRank(dataset, heroId, 'all-maps', selectedMode, selectedRank);
}

function HeroCard({
  hero,
  dataset,
  selectedMode,
  selectedRank,
  onClick,
}: {
  hero: HeroSummary;
  dataset: AppDataset | null;
  selectedMode: Mode;
  selectedRank: CompetitiveRank;
  onClick: () => void;
}) {
  const { locale } = useLocale();
  // 優先使用 mode_rank_stats 的 all-maps 勝率；回退 default_win_rate
  const allMapsWR = dataset
    ? getHeroAllMapsWinRate(dataset, hero.id, selectedMode, selectedRank)
    : null;
  const displayWinRate = allMapsWR ?? hero.default_win_rate;
  const heroName = locale === 'zh-TW' ? (hero.zh ?? hero.en) : hero.en;

  return (
    <div
      onClick={onClick}
      className="relative cursor-pointer rounded-lg overflow-hidden group"
      style={{ background: 'linear-gradient(135deg, #2a1f10 0%, #1a1208 100%)', border: '1px solid rgba(242,127,13,0.15)' }}
    >
      {/* 英雄圖片（方形） */}
      <div className="relative" style={{ aspectRatio: '1/1' }}>
        <HeroImage
          heroId={hero.id}
          heroName={heroName}
          className="w-full h-full object-cover object-top opacity-80 group-hover:opacity-95 transition-opacity"
        />
        <div className="absolute top-2 left-2">
          <TierBadge tier={hero.tier} />
        </div>
      </div>

      {/* 名稱 + 勝率 */}
      <div className="px-3 py-2.5">
        <p className="text-white font-bold text-base leading-tight truncate">{heroName}</p>
        {displayWinRate != null && (
          <p className="text-sm mt-1" style={{ color: '#f27f0d' }}>{displayWinRate.toFixed(1)}% WR</p>
        )}
      </div>

      {/* 懸停邊框 */}
      <div className="absolute inset-0 rounded-lg border-2 border-transparent group-hover:border-[#f27f0d] transition-colors" />
    </div>
  );
}

export function HeroesListPage() {
  const { dataset } = useDataset();
  const { locale, t } = useLocale();
  const navigate = useNavigate();

  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('ALL');
  const [sortMode, setSortMode] = useState<SortMode>('tier_then_winrate');
  // Mode/Rank 選擇器，預設 Quick Play / All（對應 all-maps 全地圖統計）
  const [selectedMode, setSelectedMode] = useState<Mode>('Quick Play');
  const [selectedRank, setSelectedRank] = useState<CompetitiveRank>('All');

  const allHeroes = dataset?.heroes ?? [];

  const filteredHeroes = useMemo(() => {
    let heroes = filterHeroesByRole(allHeroes, roleFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      heroes = heroes.filter(h => {
        const primary = locale === 'zh-TW' ? (h.zh ?? h.en) : h.en;
        return primary.toLowerCase().includes(q) || h.en.toLowerCase().includes(q);
      });
    }
    // 排序時以 all-maps 勝率為基準
    return sortHeroes(heroes, sortMode, { dataset, mapId: 'all-maps', selectedMode, selectedRank });
  }, [allHeroes, roleFilter, search, locale, sortMode, dataset, selectedMode, selectedRank]);

  const onSelect = (hero: HeroSummary) => {
    navigate(`/heroes-list/${hero.id}`);
  };

  const roles: { label: string; value: RoleFilter }[] = [
    { label: t.heroes.filterAll, value: 'ALL' },
    { label: t.heroes.filterTank, value: 'Tank' },
    { label: t.heroes.filterDamage, value: 'Damage' },
    { label: t.heroes.filterSupport, value: 'Support' },
  ];

  const modeOptions: { value: Mode; label: string }[] = [
    { value: 'Quick Play', label: locale === 'zh-TW' ? MODE_LABELS['Quick Play'].zh : MODE_LABELS['Quick Play'].en },
    { value: 'Competitive', label: locale === 'zh-TW' ? MODE_LABELS.Competitive.zh : MODE_LABELS.Competitive.en },
  ];
  const rankOptions = [...COMPETITIVE_RANKS]
    .sort((a, b) => COMPETITIVE_RANK_LABELS[a].index - COMPETITIVE_RANK_LABELS[b].index)
    .map(rank => ({
      value: rank,
      label: locale === 'zh-TW' ? COMPETITIVE_RANK_LABELS[rank].zh : COMPETITIVE_RANK_LABELS[rank].en,
    }));

  return (
    <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide min-h-0">
      {/* 頁面標題 */}
      <div className="px-4 md:px-8 pt-8 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <span className="w-1 h-8 rounded-full inline-block" style={{ backgroundColor: '#f27f0d' }} />
          <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tight italic">
            {t.heroesPage.title}
          </h1>
        </div>
        <p className="text-sm ml-4" style={{ color: '#9ca3af' }}>{t.heroesPage.subtitle}</p>
      </div>

      {/* 搜尋 + Role 篩選 + 排序 + Mode/Rank */}
      <div className="px-4 md:px-8 pb-4 flex flex-col sm:flex-row gap-3">
        {/* 搜尋框 */}
        <div className="relative flex-1 max-w-sm">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg"
            style={{ color: '#9ca3af' }}>search</span>
          <input
            className="w-full pl-10 pr-4 py-2 rounded-lg text-sm text-white outline-none"
            style={{ backgroundColor: 'rgba(242,127,13,0.08)', border: '1px solid rgba(242,127,13,0.25)' }}
            placeholder={t.heroes.search}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Role 篩選 / 排序 / Mode / Rank */}
        <div className="flex gap-2 flex-wrap">
          {roles.map(r => (
            <button key={r.value} onClick={() => setRoleFilter(r.value)}
              className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-all"
              style={roleFilter === r.value
                ? { backgroundColor: '#f27f0d', color: '#221910' }
                : { backgroundColor: 'rgba(242,127,13,0.1)', color: '#9ca3af', border: '1px solid rgba(242,127,13,0.2)' }}>
              {r.label}
            </button>
          ))}
          <div className="w-px h-6 self-center" style={{ backgroundColor: 'rgba(242,127,13,0.2)' }} />
          <button onClick={() => setSortMode('tier_then_winrate')}
            className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-all whitespace-nowrap"
            style={sortMode === 'tier_then_winrate'
              ? { backgroundColor: '#f27f0d', color: '#221910' }
              : { backgroundColor: 'rgba(242,127,13,0.1)', color: '#9ca3af', border: '1px solid rgba(242,127,13,0.2)' }}>
            {t.heroes.sortTierThenWR}
          </button>
          <button onClick={() => setSortMode('winrate_then_tier')}
            className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-all whitespace-nowrap"
            style={sortMode === 'winrate_then_tier'
              ? { backgroundColor: '#f27f0d', color: '#221910' }
              : { backgroundColor: 'rgba(242,127,13,0.1)', color: '#9ca3af', border: '1px solid rgba(242,127,13,0.2)' }}>
            {t.heroes.sortWRThenTier}
          </button>
          <div className="w-px h-6 self-center" style={{ backgroundColor: 'rgba(242,127,13,0.2)' }} />
          {/* Mode 選擇 */}
          <select
            className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider outline-none"
            style={{ backgroundColor: 'rgba(242,127,13,0.1)', color: '#f3f4f6', border: '1px solid rgba(242,127,13,0.2)' }}
            value={selectedMode}
            onChange={e => {
              const nextMode = e.target.value as Mode;
              setSelectedMode(nextMode);
              if (nextMode === 'Quick Play') setSelectedRank('All');
            }}
          >
            {modeOptions.map(opt => (
              <option key={opt.value} value={opt.value} style={{ color: '#111827', backgroundColor: '#ffffff' }}>
                {opt.label}
              </option>
            ))}
          </select>
          {/* Rank 選擇（Quick Play 時停用） */}
          <select
            className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider outline-none"
            style={{ backgroundColor: 'rgba(242,127,13,0.1)', color: '#f3f4f6', border: '1px solid rgba(242,127,13,0.2)' }}
            value={selectedRank}
            disabled={selectedMode === 'Quick Play'}
            onChange={e => setSelectedRank(e.target.value as CompetitiveRank)}
          >
            {rankOptions.map(rank => (
              <option key={rank.value} value={rank.value} style={{ color: '#111827', backgroundColor: '#ffffff' }}>
                {rank.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 英雄卡片格 */}
      <div className="px-4 md:px-8 pb-8">
        {/* 分組標題 */}
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>groups</span>
          <span className="text-sm font-black uppercase tracking-wider" style={{ color: '#f27f0d' }}>
            {t.heroes.allHeroes}
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded font-bold"
            style={{ backgroundColor: 'rgba(242,127,13,0.15)', color: '#f27f0d' }}>
            {filteredHeroes.length}
          </span>
          <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(242,127,13,0.2)' }} />
        </div>

        {filteredHeroes.length === 0 ? (
          <div className="text-center py-20" style={{ color: '#9ca3af' }}>
            <span className="material-symbols-outlined text-5xl block mb-3">search_off</span>
            <p>{t.heroes.noData}</p>
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2">
            {filteredHeroes.map(h => (
              <HeroCard
                key={h.id}
                hero={h}
                dataset={dataset}
                selectedMode={selectedMode}
                selectedRank={selectedRank}
                onClick={() => onSelect(h)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
