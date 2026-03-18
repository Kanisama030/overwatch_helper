import { Link, useLocation } from 'react-router-dom';

export function Sidebar() {
  const location = useLocation();
  return (
    <aside className="w-64 flex-shrink-0 hidden md:flex flex-col border-r"
      style={{ borderColor: 'rgba(242,127,13,0.2)', backgroundColor: '#221910' }}>
      <div className="p-6 flex items-center gap-3">
        <div style={{ color: '#f27f0d' }}>
          <svg width="32" height="32" fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <path d="M13.8261 17.4264C16.7203 18.1174 20.2244 18.5217 24 18.5217C27.7756 18.5217 31.2797 18.1174 34.1739 17.4264C36.9144 16.7722 39.9967 15.2331 41.3563 14.1648L24.8486 40.6391C24.4571 41.267 23.5429 41.267 23.1514 40.6391L6.64374 14.1648C8.00331 15.2331 11.0856 16.7722 13.8261 17.4264Z" fill="currentColor"/>
          </svg>
        </div>
        <h1 className="text-xl font-bold tracking-tight text-white">OH Helper</h1>
      </div>
      <nav className="flex-1 px-4 space-y-2 mt-4">
        <Link
          to="/"
          className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm font-bold transition-all ${
            location.pathname === '/'
              ? 'text-[#221910] bg-[#f27f0d]'
              : 'text-gray-400 hover:text-[#f27f0d]'
          }`}
          style={location.pathname === '/' ? {} : {}}
        >
          <span className="material-symbols-outlined">map</span>
          Maps
        </Link>
      </nav>
    </aside>
  );
}
