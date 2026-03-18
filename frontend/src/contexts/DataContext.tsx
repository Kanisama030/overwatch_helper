import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { loadAppDataset } from '../data/loader';
import type { AppDataset } from '../types';

interface DataContextValue {
  dataset: AppDataset | null;
  loading: boolean;
  error: string | null;
}

const DataContext = createContext<DataContextValue>({ dataset: null, loading: true, error: null });

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

export function useDataset() {
  return useContext(DataContext);
}
