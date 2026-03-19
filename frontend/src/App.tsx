import { HashRouter, Routes, Route } from 'react-router-dom';
import { DataProvider } from './contexts/DataContext';
import { LocaleProvider } from './contexts/LocaleContext';
import { SidebarProvider } from './contexts/SidebarContext';
import { useDataset } from './contexts/dataContextStore';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { LoadingScreen } from './components/common/LoadingScreen';
import { ErrorScreen } from './components/common/ErrorScreen';
import { MapSelectionPage } from './pages/MapSelectionPage';
import { HeroSelectionPage } from './pages/HeroSelectionPage';
import { HeroDetailPage } from './pages/HeroDetailPage';
import { useLocation } from 'react-router-dom';
import { useLocale } from './contexts/localeContextStore';

function AppShell() {
  const { loading, error } = useDataset();
  const location = useLocation();
  const { t } = useLocale();

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen message={error} />;

  const pageMeta: Record<string, { title: string; subtitle: string }> = {
    '/': { title: t.maps.title, subtitle: t.steps.step1 },
    '/heroes': { title: t.heroes.title, subtitle: t.steps.step2 },
  };

  const isHeroDetail = location.pathname.startsWith('/hero/');
  const meta = isHeroDetail
    ? { title: t.hero.analysisTitle, subtitle: t.steps.step3 }
    : (pageMeta[location.pathname] ?? { title: t.app.name, subtitle: '' });

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
          <SidebarProvider>
            <AppShell />
          </SidebarProvider>
        </HashRouter>
      </DataProvider>
    </LocaleProvider>
  );
}

export default App
