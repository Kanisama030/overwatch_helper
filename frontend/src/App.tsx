import { HashRouter, Routes, Route } from 'react-router-dom';
import { DataProvider, useDataset } from './contexts/DataContext';
import { LocaleProvider } from './contexts/LocaleContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { LoadingScreen } from './components/common/LoadingScreen';
import { ErrorScreen } from './components/common/ErrorScreen';
import { MapSelectionPage } from './pages/MapSelectionPage';
import { HeroSelectionPage } from './pages/HeroSelectionPage';
import { HeroDetailPage } from './pages/HeroDetailPage';
import { useLocation } from 'react-router-dom';

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  '/': { title: 'Map Selection', subtitle: 'Step 1: Choose your battleground' },
  '/heroes': { title: 'Hero Guide', subtitle: 'Step 2: Pick your hero' },
};

function AppShell() {
  const { loading, error } = useDataset();
  const location = useLocation();

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen message={error} />;

  const isHeroDetail = location.pathname.startsWith('/hero/');
  const meta = isHeroDetail
    ? { title: 'Hero Analysis', subtitle: 'Step 3: Strategy' }
    : (PAGE_META[location.pathname] ?? { title: 'Overwatch Helper', subtitle: '' });

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#221910', color: '#f1f5f9' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header title={meta.title} subtitle={meta.subtitle} />
        <Routes>
          <Route path="/" element={<MapSelectionPage />} />
          <Route path="/heroes" element={<HeroSelectionPage />} />
          <Route path="/hero/:heroId" element={<HeroDetailPage />} />
        </Routes>
      </div>
    </div>
  );
}

function App() {
  return (
    <LocaleProvider>
      <DataProvider>
        <HashRouter>
          <AppShell />
        </HashRouter>
      </DataProvider>
    </LocaleProvider>
  );
}

export default App
