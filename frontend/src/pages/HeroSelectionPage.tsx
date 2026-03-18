import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useDataset } from '../contexts/DataContext';
import {
  getMapById, filterHeroesByRole, searchHeroes, sortHeroesByTier,
  getBestPicksForMap, getWorstPicksForMap, getHeroWinRateForMap
} from '../data/selectors';
import { TierBadge } from '../components/common/TierBadge';
import { HeroImage } from '../components/common/HeroImage';
import type { HeroSummary, Role } from '../types';

type RoleFilter = 'ALL' | Role;

function HeroCard({ hero, mapId, onClick }: { hero: HeroSummary; mapId: string | null; onClick: () => void }) {
  const mapWinRate = mapId ? getHeroWinRateForMap(hero, mapId) : null;
  const displayWinRate = mapWinRate ?? hero.default_win_rate;

  return (
    <div
      onClick={onClick}
      className="relative cursor-pointer rounded-lg overflow-hidden group"
      style={{ background: 'linear-gradient(135deg, #2a1f10 0%, #1a1208 100%)', border: '1px solid rgba(242,127,13,0.15)', aspectRatio: '3/4' }}
    >
      {/* Hero image */}
      <div className="absolute inset-0">
        <HeroImage
          heroId={hero.id}
          heroName={hero.en}
          className="w-full h-full object-cover object-top opacity-70 group-hover:opacity-90 transition-opacity"
        />
      </div>

      {/* Bottom overlay */}
      <div className="absolute inset-x-0 bottom-0 p-2"
        style={{ background: 'linear-gradient(to top, rgba(34,25,16,0.95) 0%, transparent 100%)' }}>
        <TierBadge tier={hero.tier} />
        <p className="text-white font-bold text-xs mt-1 truncate">{hero.en}</p>
        {displayWinRate != null && (
          <p className="text-[10px]" style={{ color: '#f27f0d' }}>{displayWinRate.toFixed(1)}% WR</p>
        )}
      </div>

      {/* Hover border */}
      <div className="absolute inset-0 rounded-lg border-2 border-transparent group-hover:border-[#f27f0d] transition-colors" />
    </div>
  );
}

function HeroSection({ title, heroes, mapId, onSelect, accentColor = '#f27f0d', icon = 'military_tech' }:
  { title: string; heroes: HeroSummary[]; mapId: string | null; onSelect: (h: HeroSummary) => void; accentColor?: string; icon?: string }) {
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
        {heroes.map(h => <HeroCard key={h.id} hero={h} mapId={mapId} onClick={() => onSelect(h)} />)}
      </div>
    </div>
  );
}

export function HeroSelectionPage() {
  const { dataset } = useDataset();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const mapId = searchParams.get('map');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('ALL');

  const map = mapId && dataset ? getMapById(dataset, mapId) : null;
  const allHeroes = dataset?.heroes ?? [];

  const bestPicks = useMemo(() => mapId && dataset ? sortHeroesByTier(getBestPicksForMap(dataset, mapId)) : [], [dataset, mapId]);
  const worstPicks = useMemo(() => mapId && dataset ? getWorstPicksForMap(dataset, mapId) : [], [dataset, mapId]);
  const bestIds = new Set(bestPicks.map(h => h.id));
  const worstIds = new Set(worstPicks.map(h => h.id));

  const filteredHeroes = useMemo(() => {
    let heroes = filterHeroesByRole(allHeroes, roleFilter);
    heroes = searchHeroes(heroes, search);
    return heroes;
  }, [allHeroes, roleFilter, search]);

  const filteredBest = filteredHeroes.filter(h => bestIds.has(h.id));
  const filteredWorst = filteredHeroes.filter(h => worstIds.has(h.id));
  const filteredOther = sortHeroesByTier(filteredHeroes.filter(h => !bestIds.has(h.id) && !worstIds.has(h.id)));

  const onSelect = (hero: HeroSummary) => {
    const query = mapId ? `?map=${mapId}` : '';
    navigate(`/hero/${hero.id}${query}`);
  };

  const roles: { label: string; value: RoleFilter }[] = [
    { label: 'ALL', value: 'ALL' },
    { label: 'TANK', value: 'Tank' },
    { label: 'DAMAGE', value: 'Damage' },
    { label: 'SUPPORT', value: 'Support' },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide min-h-0">
      {/* Map banner */}
      {map && (
        <div className="px-4 md:px-8 pt-6 pb-2">
          <nav className="text-xs mb-3" style={{ color: '#6b7280' }}>
            <Link to="/" style={{ color: '#f27f0d' }}>Maps</Link>
            <span className="mx-2">›</span>
            <span className="text-white">{map.en}</span>
          </nav>
          <div className="relative rounded-lg overflow-hidden p-4 md:p-6"
            style={{ background: 'linear-gradient(135deg, #3d2a10, #221910)', border: '1px solid rgba(242,127,13,0.3)' }}>
            {/* Map background image */}
            <img
              src={`./maps/${map.id}.jpg`}
              alt={map.en}
              className="absolute inset-0 w-full h-full object-cover opacity-20"
              onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
            <div className="relative flex items-center gap-3">
              <span className="material-symbols-outlined text-3xl" style={{ color: '#f27f0d' }}>map</span>
              <div>
                <h2 className="text-xl font-black text-white uppercase tracking-tight">{map.en}</h2>
                <p className="text-xs" style={{ color: '#f27f0d' }}>{map.mode}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Title */}
      <div className="px-4 md:px-8 pt-4 pb-2">
        <div className="flex items-center gap-3 mb-1">
          <span className="w-1 h-8 rounded-full inline-block" style={{ backgroundColor: '#f27f0d' }} />
          <h1 className="text-2xl font-black text-white uppercase tracking-tight italic">Hero Guide</h1>
        </div>
      </div>

      {/* Search & Role filter */}
      <div className="px-4 md:px-8 pb-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg"
            style={{ color: '#9ca3af' }}>search</span>
          <input
            className="w-full pl-10 pr-4 py-2 rounded-lg text-sm text-white outline-none"
            style={{ backgroundColor: 'rgba(242,127,13,0.08)', border: '1px solid rgba(242,127,13,0.25)' }}
            placeholder="Search heroes..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          {roles.map(r => (
            <button key={r.value} onClick={() => setRoleFilter(r.value)}
              className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-all"
              style={roleFilter === r.value
                ? { backgroundColor: '#f27f0d', color: '#221910' }
                : { backgroundColor: 'rgba(242,127,13,0.1)', color: '#9ca3af', border: '1px solid rgba(242,127,13,0.2)' }}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Hero sections */}
      <div className="px-4 md:px-8 pb-8">
        {mapId ? (
          <>
            <HeroSection title="Best Picks" heroes={filteredBest} mapId={mapId} onSelect={onSelect}
              accentColor="#f27f0d" icon="military_tech" />
            <HeroSection title="Avoid Picks" heroes={filteredWorst} mapId={mapId} onSelect={onSelect}
              accentColor="#ef4444" icon="warning" />
            <HeroSection title="All Heroes" heroes={filteredOther} mapId={mapId} onSelect={onSelect}
              accentColor="#6b7280" icon="groups" />
          </>
        ) : (
          <HeroSection title="All Heroes" heroes={filteredOther} mapId={null} onSelect={onSelect}
            accentColor="#6b7280" icon="groups" />
        )}
      </div>
    </div>
  );
}
