import { en } from './en';
import type { Locale } from '../types';

const locales = { en };

export function getMessages(locale: Locale) {
  if (locale === 'zh-TW') return locales.en; // fallback to en
  return locales.en;
}

export { en };
