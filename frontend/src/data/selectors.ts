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

export type SortMode = 'tier_then_winrate' | 'winrate_then_tier';

export function sortHeroesByTier(heroes: HeroSummary[]): HeroSummary[] {
  return sortHeroes(heroes, 'tier_then_winrate');
}

export function sortHeroes(heroes: HeroSummary[], mode: SortMode = 'tier_then_winrate'): HeroSummary[] {
  return [...heroes].sort((a, b) => {
    const ta = TIER_ORDER[a.tier ?? 'C'] ?? 5;
    const tb = TIER_ORDER[b.tier ?? 'C'] ?? 5;
    const wa = a.default_win_rate ?? 0;
    const wb = b.default_win_rate ?? 0;

    if (mode === 'tier_then_winrate') {
      if (ta !== tb) return ta - tb;
      return wb - wa;
    } else {
      // winrate_then_tier
      if (Math.abs(wa - wb) > 0.01) return wb - wa;
      return ta - tb;
    }
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

// 安全取值 helper：清理 section content（移除 markdown 圖片、* 前綴）
export function cleanSectionContent(content: string[] | undefined): string[] {
  if (!content) return [];
  return content.map(line => 
    line
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .trim()
  ).filter(line => line.length > 0);
}

export function toMarkdown(content: string[] | undefined): string {
  return cleanSectionContent(content).join('\n');
}

// counters 清單規範化（小寫 id / 英文名對應）
export function normalizeHeroIdentifier(identifier: string | undefined, dataset: AppDataset): string | null {
  if (!identifier) return null;
  
  const normalized = identifier.toLowerCase().trim();
  
  // 直接 id 匹配
  if (dataset.heroes.some(h => h.id === normalized)) {
    return normalized;
  }
  
  // 英文名匹配（不分大小寫）
  const byName = dataset.heroes.find(h => h.en.toLowerCase() === normalized);
  if (byName) return byName.id;
  
  // slug 格式匹配（處理 wrecking-ball 等）
  const bySlug = dataset.heroes.find(h => 
    h.en.toLowerCase().replace(/[.\s]+/g, '-') === normalized ||
    h.id === normalized
  );
  if (bySlug) return bySlug.id;
  
  return null;
}

// 從 specific_counters_82 提取英雄 id 清單
export function extractCounterHeroIds(counters82: string[] | undefined, dataset: AppDataset): string[] {
  if (!counters82 || counters82.length === 0) return [];
  
  return counters82
    .map(name => normalizeHeroIdentifier(name, dataset))
    .filter((id): id is string => id !== null);
}
