import { useState, type ReactNode } from 'react';
import { getMessages } from '../locales';
import type { Locale } from '../types';
import { LocaleContext } from './localeContextStore';

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en');
  const t = getMessages(locale);
  return (
    <LocaleContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LocaleContext.Provider>
  );
}
