import { Link, useLocation } from 'react-router-dom';
import { useSidebar } from '../../contexts/SidebarContext';
import { useLocale } from '../../contexts/LocaleContext';

export function Sidebar() {
  const location = useLocation();
  const { isExpanded, toggleSidebar } = useSidebar();
  const { t } = useLocale();

  return (
    <aside
      className={`flex-shrink-0 hidden md:flex flex-col border-r transition-all duration-300 ${
        isExpanded ? 'w-64' : 'w-20'
      }`}
      style={{ borderColor: 'rgba(242,127,13,0.2)', backgroundColor: '#221910' }}
    >
      {/* 顶部区域 with 折叠按钮 */}
      <div className="p-6 flex items-center justify-between">
        {isExpanded && (
          <div className="flex items-center gap-3">
            <div style={{ color: '#f27f0d' }}>
              <svg width="32" height="32" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
                <path d="M13.8261 17.4264C16.7203 18.1174 20.2244 18.5217 24 18.5217C27.7756 18.5217 31.2797 18.1174 34.1739 17.4264C36.9144 16.7722 39.9967 15.2331 41.3563 14.1648L24.8486 40.6391C24.4571 41.267 23.5429 41.267 23.1514 40.6391L6.64374 14.1648C8.00331 15.2331 11.0856 16.7722 13.8261 17.4264Z" fill="currentColor"/>
              </svg>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">OW Helper</h1>
          </div>
        )}
        {!isExpanded && (
          <div style={{ color: '#f27f0d' }}>
            <svg width="32" height="32" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
              <path d="M13.8261 17.4264C16.7203 18.1174 20.2244 18.5217 24 18.5217C27.7756 18.5217 31.2797 18.1174 34.1739 17.4264C36.9144 16.7722 39.9967 15.2331 41.3563 14.1648L24.8486 40.6391C24.4571 41.267 23.5429 41.267 23.1514 40.6391L6.64374 14.1648C8.00331 15.2331 11.0856 16.7722 13.8261 17.4264Z" fill="currentColor"/>
            </svg>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded hover:bg-gray-700 transition-colors text-gray-400 hover:text-[#f27f0d]"
          title={isExpanded ? '折叠侧边栏' : '展开侧边栏'}
        >
          <span className="material-symbols-outlined text-xl">
            {isExpanded ? 'navigate_before' : 'navigate_next'}
          </span>
        </button>
      </div>

      {/* 導航區域 */}
      <nav className={`flex-1 space-y-2 transition-all duration-300 ${isExpanded ? 'px-4' : 'px-2'}`}>
        <Link
          to="/"
          className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm font-bold transition-all ${
            location.pathname === '/'
              ? 'text-[#221910] bg-[#f27f0d]'
              : 'text-gray-400 hover:text-[#f27f0d]'
          }`}
          title={t.nav.maps}
        >
          <span className="material-symbols-outlined flex-shrink-0">map</span>
          {isExpanded && <span>{t.nav.maps}</span>}
        </Link>
      </nav>
    </aside>
  );
}
