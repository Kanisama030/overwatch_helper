import type { AppDataset } from '../types';

let cache: AppDataset | null = null;

export async function loadAppDataset(): Promise<AppDataset> {
  if (cache) return cache;
  const res = await fetch('./data/app_ready_dataset.json');
  if (!res.ok) throw new Error('Failed to load app dataset');
  cache = await res.json();
  return cache!;
}
