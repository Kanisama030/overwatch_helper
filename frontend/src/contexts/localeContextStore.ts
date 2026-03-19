import { createContext, useContext } from 'react';
import { getMessages } from '../locales';
import type { Locale } from '../types';
import type { Messages } from '../locales/en';

export interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: Messages;
}

export const LocaleContext = createContext<LocaleContextValue>({
  locale: 'en',
  setLocale: () => {},
  t: getMessages('en'),
});

export function useLocale() {
  return useContext(LocaleContext);
}
