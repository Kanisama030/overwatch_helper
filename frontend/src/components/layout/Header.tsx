import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useLocale } from '../../contexts/localeContextStore';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { locale, setLocale, t } = useLocale();
  const location = useLocation();
  const navigate = useNavigate();

  const isRoot = location.pathname === '/';

  return (
    <header className="sticky top-0 z-10 backdrop-blur-md border-b px-4 md:px-8 py-4 flex items-center justify-between"
      style={{ borderColor: 'rgba(242,127,13,0.15)', backgroundColor: 'rgba(34,25,16,0.85)' }}>
      <div className="flex items-center gap-3 md:gap-4">
        {!isRoot && (
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 p-1.5 md:p-2 md:pr-4 pr-3 text-[#f27f0d] bg-[#f27f0d]/10 hover:bg-[#f27f0d]/20 border border-[#f27f0d]/20 rounded-full transition-colors"
            title={t.common.back}
          >
            <span className="material-symbols-outlined text-xl md:text-2xl">arrow_back</span>
            <span className="text-sm font-bold">{t.common.back}</span>
          </button>
        )}
        <div>
          <h2 className="text-lg font-bold text-white">{title}</h2>
          {subtitle && <p className="text-xs" style={{ color: '#9ca3af' }}>{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-4">
        {/* Language switch */}
        <div
          className="flex items-center rounded-full p-1 text-xs font-bold"
          style={{ backgroundColor: 'rgba(242,127,13,0.1)', border: '1px solid rgba(242,127,13,0.18)' }}
        >
          <button
            onClick={() => setLocale('en')}
            className={`px-2.5 py-1 rounded-full transition-all duration-300 ${
              locale === 'en' ? 'text-[#221910] -translate-y-px scale-105' : 'text-gray-400 hover:text-[#f27f0d]'
            }`}
            style={locale === 'en'
              ? { backgroundColor: '#f27f0d', boxShadow: '0 0 14px rgba(242,127,13,0.45)' }
              : undefined}
          >
            {t.language.en}
          </button>
          <button
            onClick={() => setLocale('zh-TW')}
            className={`px-2.5 py-1 rounded-full transition-all duration-300 ${
              locale === 'zh-TW' ? 'text-[#221910] -translate-y-px scale-105' : 'text-gray-400 hover:text-[#f27f0d]'
            }`}
            style={locale === 'zh-TW'
              ? { backgroundColor: '#f27f0d', boxShadow: '0 0 14px rgba(242,127,13,0.45)' }
              : undefined}
          >
            {t.language.zhTW}
          </button>
        </div>
        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-4 text-sm font-bold">
          <Link to="/" className={location.pathname === '/' ? 'text-[#f27f0d]' : 'text-gray-400 hover:text-[#f27f0d]'}>
            <span className="material-symbols-outlined align-middle text-lg mr-1">map</span>
            {t.nav.maps}
          </Link>
        </nav>
      </div>
    </header>
  );
}
