import { createContext, useContext } from 'react';
import type { AppDataset } from '../types';

export interface DataContextValue {
  dataset: AppDataset | null;
  loading: boolean;
  error: string | null;
}

export const DataContext = createContext<DataContextValue>({
  dataset: null,
  loading: true,
  error: null,
});

export function useDataset() {
  return useContext(DataContext);
}
