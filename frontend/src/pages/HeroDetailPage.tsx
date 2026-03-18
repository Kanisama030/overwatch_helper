import { useState, useMemo } from 'react';
import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom';
import { useDataset } from '../contexts/DataContext';
import { getHeroById, getMapById, getHeroWinRateForMap, sortHeroesByTier } from '../data/selectors';
import { TierBadge } from '../components/common/TierBadge';
import { HeroImage } from '../components/common/HeroImage';
import type { HeroSummary } from '../types';

type Tab = 'strategy' | 'counter';

function StatPill({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="text-center px-3 py-1 rounded" style={{ backgroundColor: 'rgba(242,127,13,0.1)' }}>
      <p className="text-[10px] uppercase tracking-widest" style={{ color: '#9ca3af' }}>{label}</p>
      <p className="text-sm font-black" style={{ color: '#f27f0d' }}>{value ?? '—'}</p>
    </div>
  );
}

function StrategyTab({ hero, mapId }: { hero: HeroSummary; mapId: string | null }) {
  const summary = hero.map_recommendations.maps_summary;
  const guideText = hero.counter_data.play_against_summary;

  const mapWinRate = mapId ? getHeroWinRateForMap(hero, mapId) : null;

  return (
    <div className="space-y-6">
      {/* TLDR */}
      {summary && (
        <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.08)', border: '1px solid rgba(242,127,13,0.25)' }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>auto_awesome</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>TLDR</span>
          </div>
          <p className="text-sm text-white leading-relaxed">{summary}</p>
        </div>
      )}

      {/* AI Placeholder */}
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

      {/* Map Performance */}
      {mapId && mapWinRate != null && (
        <div className="rounded-lg p-4" style={{ backgroundColor: 'rgba(242,127,13,0.05)', border: '1px solid rgba(242,127,13,0.15)' }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>map</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>Map Performance</span>
          </div>
          <p className="text-sm text-white">
            Win Rate on this map: <span style={{ color: '#f27f0d' }} className="font-bold">{mapWinRate.toFixed(1)}%</span>
          </p>
          {hero.map_recommendations.maps_summary && (
            <p className="text-xs mt-2" style={{ color: '#9ca3af' }}>{hero.map_recommendations.maps_summary}</p>
          )}
        </div>
      )}

      {/* Guide Content */}
      {guideText.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>strategy</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>Tactical Notes</span>
            <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(242,127,13,0.15)' }} />
          </div>
          <div className="space-y-3">
            {guideText.slice(0, 5).map((para, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-xs font-black mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center"
                  style={{ backgroundColor: 'rgba(242,127,13,0.2)', color: '#f27f0d' }}>
                  {i + 1}
                </span>
                <p className="text-sm leading-relaxed" style={{ color: '#d1d5db' }}>{para}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CounterTab({ hero, dataset }: { hero: HeroSummary; dataset: ReturnType<typeof useDataset>['dataset'] }) {
  const [selectedThreat, setSelectedThreat] = useState<string | null>(null);
  const counterMentions = hero.counter_data.countered_by_mentions;
  const playAgainst = hero.counter_data.play_against_summary;

  // Recommended swaps: best picks on current map who aren't this hero
  const recommended = useMemo(() => {
    if (!dataset) return [];
    return sortHeroesByTier(
      dataset.heroes.filter(h => h.id !== hero.id && h.tier && ['S', 'A'].includes(h.tier))
    ).slice(0, 6);
  }, [dataset, hero.id]);

  return (
    <div className="space-y-6">
      {/* Disclaimer */}
      <div className="rounded-lg p-3" style={{ backgroundColor: 'rgba(107,114,128,0.1)', border: '1px solid rgba(107,114,128,0.2)' }}>
        <p className="text-xs" style={{ color: '#9ca3af' }}>
          ⚠️ Counter data based on guide excerpts — full counter matrix not yet available
        </p>
      </div>

      {/* Threats to You */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-lg" style={{ color: '#ef4444' }}>warning</span>
          <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#ef4444' }}>Threats to You</span>
          <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(239,68,68,0.2)' }} />
        </div>
        {counterMentions.length === 0 ? (
          <p className="text-sm" style={{ color: '#6b7280' }}>No specific counter data from guide.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {counterMentions.slice(0, 12).map(name => (
              <button
                key={name}
                onClick={() => setSelectedThreat(selectedThreat === name ? null : name)}
                className="px-3 py-1.5 rounded text-xs font-bold transition-all"
                style={selectedThreat === name
                  ? { backgroundColor: '#ef4444', color: '#fff' }
                  : { backgroundColor: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)' }}
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Play Against content */}
      {playAgainst.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#f27f0d' }}>swords</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#f27f0d' }}>How to Fight Back</span>
            <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(242,127,13,0.15)' }} />
          </div>
          <div className="space-y-3">
            {playAgainst.slice(0, 5).map((tip, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-xs font-black mt-0.5 w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center"
                  style={{ backgroundColor: 'rgba(242,127,13,0.2)', color: '#f27f0d' }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <p className="text-sm leading-relaxed" style={{ color: '#d1d5db' }}>{tip}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Swaps */}
      {recommended.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-lg" style={{ color: '#22c55e' }}>swap_horiz</span>
            <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#22c55e' }}>Recommended Swaps</span>
            <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(34,197,94,0.2)' }} />
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {recommended.map(h => (
              <div key={h.id} className="text-center">
                <div className="relative rounded-lg overflow-hidden mx-auto" style={{ aspectRatio: '1/1', maxWidth: '80px' }}>
                  <HeroImage heroId={h.id} heroName={h.en} className="w-full h-full object-cover" />
                  <div className="absolute bottom-0 inset-x-0 py-0.5" style={{ backgroundColor: 'rgba(34,25,16,0.85)' }}>
                    <TierBadge tier={h.tier} />
                  </div>
                </div>
                <p className="text-[10px] text-white font-bold mt-1 truncate">{h.en}</p>
              </div>
            ))}
          </div>
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

      {/* Hero Header */}
      <div className="px-4 md:px-8 pb-4">
        <div className="rounded-lg p-4 md:p-6 flex flex-col sm:flex-row items-start gap-4"
          style={{ background: 'linear-gradient(135deg, #3d2a10, #221910)', border: '1px solid rgba(242,127,13,0.3)' }}>
          {/* Hero portrait */}
          <div className="relative w-20 h-20 rounded-lg overflow-hidden flex-shrink-0"
            style={{ border: '2px solid rgba(242,127,13,0.5)' }}>
            <HeroImage heroId={hero.id} heroName={hero.en} className="w-full h-full object-cover" />
          </div>

          {/* Hero info */}
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <TierBadge tier={hero.tier} />
              <span className="text-xs px-2 py-0.5 rounded font-bold uppercase"
                style={{ backgroundColor: 'rgba(255,255,255,0.1)', color: '#9ca3af' }}>
                {hero.role}
              </span>
            </div>
            <h1 className="text-2xl font-black text-white uppercase tracking-tight">{hero.en}</h1>
            <div className="flex gap-3 mt-2">
              <StatPill label="Win Rate" value={displayWinRate != null ? `${displayWinRate.toFixed(1)}%` : null} />
              <StatPill label="Pick Rate" value={hero.default_pick_rate != null ? `${hero.default_pick_rate.toFixed(1)}%` : null} />
              {map && <StatPill label="Map" value={map.en} />}
            </div>
          </div>

          {/* Change hero button */}
          <button
            onClick={() => navigate(map ? `/heroes?map=${mapId}` : '/heroes')}
            className="px-3 py-2 rounded text-xs font-bold uppercase tracking-wider transition-all"
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
          <StrategyTab hero={hero} mapId={mapId} />
        ) : (
          <CounterTab hero={hero} dataset={dataset} />
        )}
      </div>
    </div>
  );
}
