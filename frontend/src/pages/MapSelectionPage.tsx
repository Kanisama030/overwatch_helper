import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDataset } from '../contexts/DataContext';
import { groupMapsByMode } from '../data/selectors';
import type { GameMap } from '../types';

const MODE_ORDER = ['Assault', 'Hybrid', 'Escort', 'Control', 'Push', 'Flashpoint', 'Clash'];

const MODE_COLORS: Record<string, string> = {
  Assault: '#ef4444',
  Hybrid: '#f27f0d',
  Escort: '#3b82f6',
  Control: '#22c55e',
  Push: '#a855f7',
  Flashpoint: '#06b6d4',
  Clash: '#f59e0b',
};

function MapCard({ map, onClick }: { map: GameMap; onClick: () => void }) {
  const modeColor = MODE_COLORS[map.mode] ?? '#6b7280';
  return (
    <div
      onClick={onClick}
      className="relative cursor-pointer rounded-lg overflow-hidden group"
      style={{ aspectRatio: '16/10', background: `linear-gradient(135deg, #3d2a10 0%, #221910 100%)` }}
    >
      {/* Map image */}
      <img
        src={`./maps/${map.id}.jpg`}
        alt={map.en}
        className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity duration-300"
        onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
      />

      {/* Background gradient overlay */}
      <div className="absolute inset-0 opacity-40 group-hover:opacity-60 transition-opacity duration-300"
        style={{ background: `radial-gradient(ellipse at center, ${modeColor}44 0%, transparent 70%)` }} />
      
      {/* Map name & mode */}
      <div className="absolute inset-0 flex flex-col justify-end p-3">
        <span
          className="text-xs font-black uppercase tracking-widest px-1.5 py-0.5 rounded self-start mb-1"
          style={{ backgroundColor: `${modeColor}33`, color: modeColor, border: `1px solid ${modeColor}55` }}
        >
          {map.mode}
        </span>
        <h3 className="text-white font-bold text-lg leading-tight">{map.en}</h3>
      </div>

      {/* Hover play arrow */}
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="material-symbols-outlined text-4xl" style={{ color: '#f27f0d' }}>play_arrow</span>
      </div>

      {/* Hover border */}
      <div className="absolute inset-0 rounded-lg border-2 border-transparent group-hover:border-[#f27f0d] transition-colors duration-200" />
    </div>
  );
}

export function MapSelectionPage() {
  const { dataset } = useDataset();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [selectedMode, setSelectedMode] = useState('All');

  const maps = dataset?.maps ?? [];
  const grouped = useMemo(() => groupMapsByMode(maps), [maps]);
  const modes = ['All', ...MODE_ORDER.filter(m => grouped[m]?.length)];

  const filteredMaps = useMemo(() => {
    let result = maps;
    if (selectedMode !== 'All') {
      result = result.filter(m => m.mode === selectedMode);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(m => m.en.toLowerCase().includes(q));
    }
    return result;
  }, [maps, selectedMode, search]);

  const filteredGrouped = useMemo(() => groupMapsByMode(filteredMaps), [filteredMaps]);
  const displayModes = selectedMode === 'All'
    ? MODE_ORDER.filter(m => filteredGrouped[m]?.length)
    : (filteredGrouped[selectedMode]?.length ? [selectedMode] : []);

  return (
    <div className="flex-1 flex flex-col overflow-y-auto scrollbar-hide min-h-0">
      {/* Page header */}
      <div className="px-4 md:px-8 pt-8 pb-4">
        <div className="flex items-center gap-3 mb-1">
          <span className="w-1 h-8 rounded-full inline-block" style={{ backgroundColor: '#f27f0d' }} />
          <h1 className="text-2xl md:text-3xl font-black text-white uppercase tracking-tight italic">
            Map Selection
          </h1>
        </div>
        <p className="text-sm ml-4" style={{ color: '#9ca3af' }}>
          Choose your battleground to get hero recommendations
        </p>
      </div>

      {/* Search & Mode filter */}
      <div className="px-4 md:px-8 pb-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg"
            style={{ color: '#9ca3af' }}>search</span>
          <input
            className="w-full pl-10 pr-4 py-2 rounded-lg text-sm text-white outline-none transition-all"
            style={{ backgroundColor: 'rgba(242,127,13,0.08)', border: '1px solid rgba(242,127,13,0.25)' }}
            placeholder="Quick find map..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {modes.map(mode => (
            <button
              key={mode}
              onClick={() => setSelectedMode(mode)}
              className="px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-all"
              style={selectedMode === mode
                ? { backgroundColor: '#f27f0d', color: '#221910' }
                : { backgroundColor: 'rgba(242,127,13,0.1)', color: '#9ca3af', border: '1px solid rgba(242,127,13,0.2)' }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Map grid */}
      <div className="px-4 md:px-8 pb-8 flex-1">
        {displayModes.length === 0 ? (
          <div className="text-center py-20" style={{ color: '#9ca3af' }}>
            <span className="material-symbols-outlined text-5xl block mb-3">search_off</span>
            <p>No maps found</p>
          </div>
        ) : displayModes.map(mode => (
          <div key={mode} className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-black uppercase tracking-widest" style={{ color: MODE_COLORS[mode] ?? '#f27f0d' }}>
                {mode}
              </span>
              <div className="flex-1 h-px" style={{ backgroundColor: 'rgba(242,127,13,0.15)' }} />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {(filteredGrouped[mode] ?? []).map(map => (
                <MapCard
                  key={map.id}
                  map={map}
                  onClick={() => navigate(`/heroes?map=${map.id}`)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
