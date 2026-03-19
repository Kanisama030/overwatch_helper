import { Link, useLocation } from 'react-router-dom';
import { useLocale } from '../../contexts/localeContextStore';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { locale, setLocale, t } = useLocale();
  const location = useLocation();

  return (
    <header className="sticky top-0 z-10 backdrop-blur-md border-b px-4 md:px-8 py-4 flex items-center justify-between"
      style={{ borderColor: 'rgba(242,127,13,0.15)', backgroundColor: 'rgba(34,25,16,0.85)' }}>
      <div className="flex items-center gap-4">
        {/* Mobile menu icon placeholder */}
        <div className="md:hidden" style={{ color: '#f27f0d' }}>
          <span className="material-symbols-outlined text-3xl">menu</span>
        </div>
        <div>
          <h2 className="text-lg font-bold text-white">{title}</h2>
          {subtitle && <p className="text-xs" style={{ color: '#9ca3af' }}>{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-4">
        {/* Language switch */}
        <div className="flex items-center gap-1 text-xs font-bold">
          <button
            onClick={() => setLocale('en')}
            className={`px-2 py-1 rounded transition-all ${locale === 'en' ? 'text-[#f27f0d]' : 'text-gray-500'}`}
          >
            EN
          </button>
          <span className="text-gray-600">|</span>
          <button
            title={t.language.comingSoon}
            className="px-2 py-1 rounded text-gray-600 cursor-not-allowed opacity-50"
            disabled
          >
            ZH-TW
          </button>
        </div>
        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-4 text-sm font-bold">
          <Link to="/" className={location.pathname === '/' ? 'text-[#f27f0d]' : 'text-gray-400 hover:text-[#f27f0d]'}>
            <span className="material-symbols-outlined align-middle text-lg mr-1">map</span>
            Maps
          </Link>
        </nav>
      </div>
    </header>
  );
}
