import { useEffect, useState, type ReactNode } from 'react';
import { loadAppDataset } from '../data/loader';
import type { AppDataset } from '../types';
import { DataContext } from './dataContextStore';

export function DataProvider({ children }: { children: ReactNode }) {
  const [dataset, setDataset] = useState<AppDataset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAppDataset()
      .then(setDataset)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return <DataContext.Provider value={{ dataset, loading, error }}>{children}</DataContext.Provider>;
}
