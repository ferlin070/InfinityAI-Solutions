import React, { useState, useEffect } from 'react';
import { 
  Activity, Sliders, Settings as SettingsIcon, MessageSquare, 
  TrendingUp, LogOut, Shield, Globe, Users, FileText, SlidersHorizontal 
} from 'lucide-react';
import { translations } from './translations';
import { checkMe, logout } from './api';

// Components
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import WorkOrder from './components/WorkOrder';
import LiveChat from './components/LiveChat';
import LeadsGrid from './components/LeadsGrid';
import QuotationsList from './components/QuotationsList';
import AgentConfig from './components/AgentConfig';
import Analytics from './components/Analytics';
import Settings from './components/Settings';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [lang, setLang] = useState('ms'); // default Bahasa Melayu
  const [activeTab, setActiveTab] = useState('dashboard');
  const [waSubTab, setWaSubTab] = useState('conversations');
  const [currentDate, setCurrentDate] = useState('');

  useEffect(() => {
    // Check initial auth state
    verifyAuth();

    // Set formatted date
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const locale = lang === 'en' ? 'en-US' : 'ms-MY';
    setCurrentDate(new Date().toLocaleDateString(locale, dateOptions));
  }, [lang]);

  async function verifyAuth() {
    setCheckingAuth(true);
    try {
      const data = await checkMe();
      if (data && data.authenticated) {
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    } catch (e) {
      setIsAuthenticated(false);
    } finally {
      setCheckingAuth(false);
    }
  }

  async function handleLogout() {
    try {
      await logout();
      setIsAuthenticated(false);
      setActiveTab('dashboard');
    } catch (e) {
      console.error(e);
    }
  }

  const t = (key) => {
    return translations[lang]?.[key] || translations.ms?.[key] || key;
  };

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-text-muted">Memuatkan sistem...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="min-h-screen max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col space-y-6">
      {/* Premium Header */}
      <header className="glass-panel p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 glow-purple">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-primary font-semibold tracking-wide text-xs">
            <Shield className="w-4 h-4" />
            <span className="uppercase tracking-wider font-mono">{t('wordmark')}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text">{t('title')}</h1>
          <p className="text-xs text-text-muted">{t('sub-title')}</p>
        </div>

        <div className="flex flex-col items-end gap-2 text-right">
          <div className="flex items-center space-x-2">
            {/* Lang toggle */}
            <button 
              onClick={() => setLang(prev => prev === 'ms' ? 'en' : 'ms')}
              className="flex items-center text-xs font-semibold text-text-muted hover:text-text bg-card-border/20 border border-card-border px-3 py-1.5 rounded-lg transition-all"
            >
              <Globe className="w-3.5 h-3.5 mr-1" />
              {lang.toUpperCase()}
            </button>

            {/* Logout button */}
            <button 
              onClick={handleLogout}
              className="flex items-center text-xs font-semibold text-accent-red hover:text-white hover:bg-accent-red/20 bg-accent-red/10 border border-accent-red/20 px-3 py-1.5 rounded-lg transition-all"
            >
              <LogOut className="w-3.5 h-3.5 mr-1" />
              {t('log-keluar')}
            </button>
          </div>
          <span className="text-[10px] text-text-muted font-mono">{currentDate}</span>
        </div>
      </header>

      {/* Main Tabs Navigation */}
      <nav className="flex space-x-1.5 overflow-x-auto bg-card-border/10 p-1.5 rounded-xl border border-card-border/30 max-w-fit">
        {[
          { id: 'dashboard', label: 'Dashboard', icon: Activity },
          { id: 'workorder', label: t('tab-workorder'), icon: FileText },
          { id: 'whatsapp', label: t('tab-whatsapp'), icon: MessageSquare },
          { id: 'agents', label: 'Agent Config', icon: Sliders },
          { id: 'analytics', label: 'Analytics', icon: TrendingUp },
          { id: 'settings', label: 'Settings', icon: SettingsIcon },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-1.5 text-xs px-4 py-2.5 rounded-lg transition-all whitespace-nowrap font-medium ${
                activeTab === tab.id 
                  ? 'bg-primary text-white font-semibold' 
                  : 'text-text-muted hover:text-text hover:bg-card-border/10'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Content Area */}
      <main className="flex-1">
        {activeTab === 'dashboard' && <Dashboard t={t} lang={lang} />}
        {activeTab === 'workorder' && <WorkOrder t={t} />}
        
        {/* WhatsApp Subtabs nested page */}
        {activeTab === 'whatsapp' && (
          <div className="space-y-6">
            <div className="flex space-x-1.5 border-b border-card-border/50 pb-3">
              {[
                { id: 'conversations', label: t('wa-conversations'), icon: MessageSquare },
                { id: 'leads', label: t('wa-leads'), icon: Users },
                { id: 'quotations', label: t('wa-quotations'), icon: FileText },
              ].map((sub) => {
                const Icon = sub.icon;
                return (
                  <button
                    key={sub.id}
                    onClick={() => setWaSubTab(sub.id)}
                    className={`flex items-center space-x-1.5 text-xs px-3.5 py-2 rounded-lg transition-all ${
                      waSubTab === sub.id 
                        ? 'bg-primary/20 text-primary-hover font-semibold' 
                        : 'text-text-muted hover:text-text'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{sub.label}</span>
                  </button>
                );
              })}
            </div>

            <div>
              {waSubTab === 'conversations' && <LiveChat t={t} />}
              {waSubTab === 'leads' && <LeadsGrid />}
              {waSubTab === 'quotations' && <QuotationsList />}
            </div>
          </div>
        )}

        {activeTab === 'agents' && <AgentConfig t={t} />}
        {activeTab === 'analytics' && <Analytics />}
        {activeTab === 'settings' && <Settings t={t} />}
      </main>

      {/* Footer */}
      <footer className="pt-6 border-t border-card-border/40 text-center text-[10px] text-text-muted font-mono flex items-center justify-between">
        <span>{t('footer-doc')}</span>
        <span>{t('footer-power')}</span>
      </footer>
    </div>
  );
}
