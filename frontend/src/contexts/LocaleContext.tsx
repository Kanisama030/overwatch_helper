import { createContext, useContext, useState, type ReactNode } from 'react';
import { getMessages } from '../locales';
import type { Locale } from '../types';
import type { Messages } from '../locales/en';

interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: Messages;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: 'en',
  setLocale: () => {},
  t: getMessages('en'),
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');
  const t = getMessages(locale);
  return (
    <LocaleContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  return useContext(LocaleContext);
}
