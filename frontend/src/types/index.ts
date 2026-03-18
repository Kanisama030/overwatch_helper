export type Role = 'Tank' | 'Damage' | 'Support';
export type Locale = 'en' | 'zh-TW';

export interface GameMap {
  id: string;
  en: string;
  zh: string | null;
  mode: string;
  thumbnail: string | null;
}

export interface MapStats {
  win_rate: number | null;
  pick_rate: number | null;
}

export interface MapRecommendation {
  best_maps: string[];
  worst_maps: string[];
  maps_summary: string;
}

export interface CounterData {
  play_against_summary: string[];
  countered_by_mentions: string[];
}

export interface HeroSummary {
  id: string;
  en: string;
  zh: string | null;
  role: Role;
  tier: string | null;
  default_win_rate: number | null;
  default_pick_rate: number | null;
  map_recommendations: MapRecommendation;
  counter_data: CounterData;
  map_stats: Record<string, MapStats>;
}

export interface AppDataset {
  last_updated: string;
  maps: GameMap[];
  heroes: HeroSummary[];
}
