import type { AppDataset, HeroSummary, GameMap, Role } from '../types';

export function getMapById(dataset: AppDataset, mapId: string): GameMap | undefined {
  return dataset.maps.find(m => m.id === mapId);
}

export function getHeroById(dataset: AppDataset, heroId: string): HeroSummary | undefined {
  return dataset.heroes.find(h => h.id === heroId);
}

export function filterHeroesByRole(heroes: HeroSummary[], role: Role | 'ALL'): HeroSummary[] {
  if (role === 'ALL') return heroes;
  return heroes.filter(h => h.role === role);
}

export function searchHeroes(heroes: HeroSummary[], query: string): HeroSummary[] {
  if (!query.trim()) return heroes;
  const q = query.toLowerCase();
  return heroes.filter(h => h.en.toLowerCase().includes(q));
}

const TIER_ORDER: Record<string, number> = { S: 0, A: 1, B: 2, C: 3, D: 4 };

export function sortHeroesByTier(heroes: HeroSummary[]): HeroSummary[] {
  return [...heroes].sort((a, b) => {
    const ta = TIER_ORDER[a.tier ?? 'C'] ?? 5;
    const tb = TIER_ORDER[b.tier ?? 'C'] ?? 5;
    if (ta !== tb) return ta - tb;
    return (b.default_win_rate ?? 0) - (a.default_win_rate ?? 0);
  });
}

export function getBestPicksForMap(dataset: AppDataset, mapId: string): HeroSummary[] {
  return dataset.heroes.filter(h => h.map_recommendations.best_maps.includes(mapId));
}

export function getWorstPicksForMap(dataset: AppDataset, mapId: string): HeroSummary[] {
  return dataset.heroes.filter(h => h.map_recommendations.worst_maps.includes(mapId));
}

export function groupMapsByMode(maps: GameMap[]): Record<string, GameMap[]> {
  return maps.reduce((acc, map) => {
    const mode = map.mode || 'Other';
    if (!acc[mode]) acc[mode] = [];
    acc[mode].push(map);
    return acc;
  }, {} as Record<string, GameMap[]>);
}

export function getHeroWinRateForMap(hero: HeroSummary, mapId: string): number | null {
  return hero.map_stats?.[mapId]?.win_rate ?? null;
}
