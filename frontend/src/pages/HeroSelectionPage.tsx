import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useDataset } from '../contexts/dataContextStore';
import { useLocale } from '../contexts/localeContextStore';
import {
  getMapById, filterHeroesByRole, sortHeroes,
  getBestPicksForMap, getWorstPicksForMap, getHeroWinRateByModeRank, type SortMode
} from '../data/selectors';
import { TierBadge } from '../components/common/TierBadge';
import { HeroImage } from '../components/common/HeroImage';
import type { AppDataset, CompetitiveRank, HeroSummary, Mode, Role } from '../types';

type RoleFilter = 'ALL' | Role;

function getModeLabel(locale: 'en' | 'zh-TW', t: ReturnType<typeof useLocale>['t'], mode: string) {
  if (locale !== 'zh-TW') return mode;
  return t.maps.modes[mode as keyof typeof t.maps.modes] ?? mode;
}

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

function HeroCard({
  hero,
  dataset,
  mapId,
  selectedMode,
  selectedRank,
  onClick
}: {
  hero: HeroSummary;
  dataset: AppDataset | null;
  mapId: string | null;
  selectedMode: Mode;
  selectedRank: CompetitiveRank;
  onClick: () => void
}) {
  const { locale } = useLocale();
  const mapWinRate = (mapId && dataset)
    ? getHeroWinRateByModeRank(dataset, hero.id, mapId, selectedMode, selectedRank)
    : null;
  const displayWinRate = mapWinRate ?? hero.default_win_rate;
  const heroName = locale === 'zh-TW' ? (hero.zh ?? hero.en) : hero.en;

  return (
    <div
      onClick={onClick}
      className="relative cursor-pointer rounded-lg overflow-hidden group"
      style={{ background: 'linear-gradient(135deg, #2a1f10 0%, #1a1208 100%)', border: '1px solid rgba(242,127,13,0.15)' }}
    >
      {/* Hero image (square) */}
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

      {/* Bottom info */}
      <div className="px-3 py-2.5">
        <p className="text-white font-bold text-base leading-tight truncate">{heroName}</p>
        {displayWinRate != null && (
          <p className="text-sm mt-1" style={{ color: '#f27f0d' }}>{displayWinRate.toFixed(1)}% WR</p>
        )}
      </div>

      {/* Hover border */}
      <div className="absolute inset-0 rounded-lg border-2 border-transparent group-hover:border-[#f27f0d] transition-colors" />
    </div>
  );
}

function HeroSection({ title, heroes, dataset, mapId, selectedMode, selectedRank, onSelect, accentColor = '#f27f0d', icon = 'military_tech' }:
  { title: string; heroes: HeroSummary[]; dataset: AppDataset | null; mapId: string | null; selectedMode: Mode; selectedRank: CompetitiveRank; onSelect: (h: HeroSummary) => void; accentColor?: string; icon?: string }) {
  if (heroes.length === 0) return null;
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-lg" style={{ color: accentColor }}>{icon}</span>
        <span className="text-sm font-black uppercase tracking-wider" style={{ color: accentColor }}>{title}</span>
        <span className="text-xs px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: `${accentColor}22`, color: accentColor }}>
          {heroes.length}
        </span>
        <div className="flex-1 h-px" style={{ backgroundColor: `${accentColor}22` }} />
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2">
        {heroes.map(h => (
          <HeroCard
            key={h.id}
            hero={h}
            dataset={dataset}
            mapId={mapId}
            selectedMode={selectedMode}
            selectedRank={selectedRank}
            onClick={() => onSelect(h)}
          />
        ))}
      </div>
    </div>
  );
}

export function HeroSelectionPage() {
  const { dataset } = useDataset();
  const { locale, t } = useLocale();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const mapId = searchParams.get('map');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('ALL');
  const [sortMode, setSortMode] = useState<SortMode>('tier_then_winrate');
  const [selectedMode, setSelectedMode] = useState<Mode>('Quick Play');
  const [selectedRank, setSelectedRank] = useState<CompetitiveRank>('All');

  const map = mapId && dataset ? getMapById(dataset, mapId) : null;
  const allHeroes = dataset?.heroes ?? [];

  const bestPicks = useMemo(() => mapId && dataset ? sortHeroes(
    getBestPicksForMap(dataset, mapId),
    sortMode,
    { dataset, mapId, selectedMode, selectedRank }
  ) : [], [dataset, mapId, sortMode, selectedMode, selectedRank]);
  const worstPicks = useMemo(() => mapId && dataset ? sortHeroes(
    getWorstPicksForMap(dataset, mapId),
    sortMode,
    { dataset, mapId, selectedMode, selectedRank }
  ) : [], [dataset, mapId, sortMode, selectedMode, selectedRank]);
  const bestIds = new Set(bestPicks.map(h => h.id));
  const worstIds = new Set(worstPicks.map(h => h.id));

  const filteredHeroes = useMemo(() => {
    let heroes = filterHeroesByRole(allHeroes, roleFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      heroes = heroes.filter(h => {
        const primary = locale === 'zh-TW' ? (h.zh ?? h.en) : h.en;
        return primary.toLowerCase().includes(q) || h.en.toLowerCase().includes(q);
      });
    }
    return heroes;
  }, [allHeroes, roleFilter, search, locale]);

  const filteredBest = useMemo(() => {
    const filtered = filteredHeroes.filter(h => bestIds.has(h.id));
    return sortHeroes(filtered, sortMode, { dataset, mapId, selectedMode, selectedRank });
  }, [filteredHeroes, bestIds, sortMode, dataset, mapId, selectedMode, selectedRank]);
  
  const filteredWorst = useMemo(() => {
    const filtered = filteredHeroes.filter(h => worstIds.has(h.id));
    return sortHeroes(filtered, sortMode, { dataset, mapId, selectedMode, selectedRank });
  }, [filteredHeroes, worstIds, sortMode, dataset, mapId, selectedMode, selectedRank]);
  
  const filteredOther = useMemo(() => {
    const filtered = filteredHeroes.filter(h => !bestIds.has(h.id) && !worstIds.has(h.id));
    return sortHeroes(filtered, sortMode, { dataset, mapId, selectedMode, selectedRank });
  }, [filteredHeroes, bestIds, worstIds, sortMode, dataset, mapId, selectedMode, selectedRank]);

  const onSelect = (hero: HeroSummary) => {
    const query = mapId ? `?map=${mapId}` : '';
    navigate(`/hero/${hero.id}${query}`);
  };

  const roles: { label: string; value: RoleFilter }[] = [
    { label: t.heroes.filterAll, value: 'ALL' },
    { label: t.heroes.filterTank, value: 'Tank' },
    { label: t.heroes.filterDamage, value: 'Damage' },
    { label: t.heroes.filterSupport, value: 'Support' },
  ];
  const mapName = map ? (locale === 'zh-TW' ? (map.zh ?? map.en) : map.en) : '';
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
      {/* Map banner */}
      {map && (
        <div className="px-4 md:px-8 pt-6 pb-2">
          <nav className="text-xs mb-3" style={{ color: '#6b7280' }}>
            <Link to="/" style={{ color: '#f27f0d' }}>{t.nav.maps}</Link>
            <span className="mx-2">›</span>
            <span className="text-white">{mapName}</span>
          </nav>
          <div className="relative rounded-lg overflow-hidden p-4 md:p-6"
            style={{ background: 'linear-gradient(135deg, #3d2a10, #221910)', border: '1px solid rgba(242,127,13,0.3)' }}>
            {/* Map background image */}
            <img
              src={`/data/assets/maps/${map.id}.jpg`}
              alt={map.en}
              className="absolute inset-0 w-full h-full object-cover opacity-20"
              onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
            <div className="relative flex items-center gap-3">
              <span className="material-symbols-outlined text-3xl" style={{ color: '#f27f0d' }}>map</span>
              <div>
                 <h2 className="text-xl font-black text-white uppercase tracking-tight">{mapName}</h2>
                <p className="text-xs" style={{ color: '#f27f0d' }}>{getModeLabel(locale, t, map.mode)}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Title */}
      <div className="px-4 md:px-8 pt-4 pb-2">
        <div className="flex items-center gap-3 mb-1">
          <span className="w-1 h-8 rounded-full inline-block" style={{ backgroundColor: '#f27f0d' }} />
           <h1 className="text-2xl font-black text-white uppercase tracking-tight italic">{t.heroes.title}</h1>
        </div>
      </div>

      {/* Search & Role filter & Sort mode */}
      <div className="px-4 md:px-8 pb-4 flex flex-col sm:flex-row gap-3">
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
               {modeOptions.map(option => (
                 <option key={option.value} value={option.value} style={{ color: '#111827', backgroundColor: '#ffffff' }}>
                   {option.label}
                 </option>
               ))}
             </select>
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

      {/* Hero sections */}
      <div className="px-4 md:px-8 pb-8">
        {mapId ? (
          <>
            <HeroSection title={t.heroes.bestPicks} heroes={filteredBest} dataset={dataset} mapId={mapId} selectedMode={selectedMode} selectedRank={selectedRank} onSelect={onSelect}
              accentColor="#f27f0d" icon="military_tech" />
            <HeroSection title={t.heroes.avoidPicks} heroes={filteredWorst} dataset={dataset} mapId={mapId} selectedMode={selectedMode} selectedRank={selectedRank} onSelect={onSelect}
              accentColor="#ef4444" icon="warning" />
            <HeroSection title={t.heroes.allHeroes} heroes={filteredOther} dataset={dataset} mapId={mapId} selectedMode={selectedMode} selectedRank={selectedRank} onSelect={onSelect}
              accentColor="#6b7280" icon="groups" />
          </>
        ) : (
          <HeroSection title={t.heroes.allHeroes} heroes={filteredOther} dataset={dataset} mapId={null} selectedMode={selectedMode} selectedRank={selectedRank} onSelect={onSelect}
            accentColor="#6b7280" icon="groups" />
        )}
      </div>
    </div>
  );
}
