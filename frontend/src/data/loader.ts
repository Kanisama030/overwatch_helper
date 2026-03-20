import type { AppDataset, ModeRankMapStats } from '../types';

let cache: AppDataset | null = null;

export async function loadAppDataset(): Promise<AppDataset> {
  if (cache) return cache;
  const [datasetRes, modeRankRes] = await Promise.all([
    fetch('./data/app_ready_dataset.json'),
    fetch('./data/mode_rank_stats.json'),
  ]);
  if (!datasetRes.ok) throw new Error('Failed to load app dataset');
  if (!modeRankRes.ok) throw new Error('Failed to load mode/rank stats');
  const [dataset, modeRankStats] = await Promise.all([
    datasetRes.json(),
    modeRankRes.json() as Promise<ModeRankMapStats>,
  ]);
  cache = {
    ...dataset,
    mode_rank_stats: modeRankStats,
  };
  return cache!;
}
