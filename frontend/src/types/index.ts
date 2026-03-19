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

export interface PerkSection {
  id: string;
  title: string;
  content?: string[];
}

export interface CounterData {
  // 新欄位
  play_as?: string[];
  play_against?: string[];
  specific_counters_81?: string[];
  specific_counters_82?: string[];
  // 保留舊欄位作 fallback
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
  perks?: {
    minor: PerkSection[];
    major: PerkSection[];
  };
}

export interface AppDataset {
  last_updated: string;
  maps: GameMap[];
  heroes: HeroSummary[];
}
