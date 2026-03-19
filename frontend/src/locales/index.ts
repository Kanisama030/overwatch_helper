import { en } from './en';
import { zhTW } from './zhTW';
import type { Locale } from '../types';

const locales = { en, zhTW };

export function getMessages(locale: Locale) {
  if (locale === 'zh-TW') return locales.zhTW;
  return locales.en;
}

export { en, zhTW };
