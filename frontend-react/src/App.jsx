import React, { useState, useEffect } from 'react';
import { 
  Activity, Sliders, Settings as SettingsIcon, MessageSquare, 
  TrendingUp, LogOut, Shield, Globe, Users, FileText, Building2 
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
import BusinessConfig from './components/BusinessConfig';

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
      if (data && (data.authenticated || data.status === 'success')) {
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

  // Arahan Kerja (WorkOrder/AgentWorkspace) is the one screen meant to feel
  // like a live agent session, not an office dashboard page — full
  // viewport height, no page-level scroll, minimal chrome. Every other tab
  // keeps the original padded/scrollable dashboard shell. See
  // docs/architecture/agent-workspace-ui.md's stated goal: "makes the user
  // feel like a supervisor of a team of AI employees, not a person texting
  // a chatbot" — the boxed, letterhead-topped layout worked against that.
  const isWorkspace = activeTab === 'workorder';

  return (
    <div className={
      isWorkspace
        ? 'h-screen overflow-hidden flex flex-col'
        : 'min-h-screen max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col space-y-6'
    }>
      {isWorkspace ? (
        /* Compact bar: brand + current tab + essential controls only —
           the full letterhead header would eat a third of the viewport
           for information that isn't relevant while watching a live run. */
        <div className="flex-shrink-0 flex items-center justify-between gap-3 px-4 py-2 border-b border-border bg-surface-raised/60">
          <div className="flex items-center gap-2 min-w-0 text-primary font-semibold text-xs">
            <Shield className="w-4 h-4 flex-shrink-0" />
            <span className="uppercase tracking-wider font-mono">{t('wordmark')}</span>
            <span className="text-text-faint">/</span>
            <span className="text-text-muted normal-case font-sans truncate">{t('tab-workorder')}</span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => setLang(prev => prev === 'ms' ? 'en' : 'ms')}
              className="flex items-center text-xs font-semibold text-text-muted hover:text-text border border-border px-2.5 py-1 rounded-lg transition-all hover:bg-surface-raised"
            >
              <Globe className="w-3.5 h-3.5 mr-1" />
              {lang.toUpperCase()}
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center text-xs font-semibold text-accent-danger hover:text-white hover:bg-accent-danger/20 bg-accent-danger/10 border border-accent-danger/20 px-2.5 py-1 rounded-lg transition-all"
            >
              <LogOut className="w-3.5 h-3.5 mr-1" />
              {t('log-keluar')}
            </button>
          </div>
        </div>
      ) : (
        /* Premium Header */
        <header className="glass-card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 glow-primary">
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
                className="flex items-center text-xs font-semibold text-text-muted hover:text-text border border-border px-3 py-1.5 rounded-lg transition-all hover:bg-surface-raised"
              >
                <Globe className="w-3.5 h-3.5 mr-1" />
                {lang.toUpperCase()}
              </button>

              {/* Logout button */}
              <button
                onClick={handleLogout}
                className="flex items-center text-xs font-semibold text-accent-danger hover:text-white hover:bg-accent-danger/20 bg-accent-danger/10 border border-accent-danger/20 px-3 py-1.5 rounded-lg transition-all"
              >
                <LogOut className="w-3.5 h-3.5 mr-1" />
                {t('log-keluar')}
              </button>
            </div>
            <span className="text-[10px] text-text-faint font-mono">{currentDate}</span>
          </div>
        </header>
      )}

      {/* Main Tabs Navigation */}
      <nav className={`flex-shrink-0 flex space-x-1 overflow-x-auto border-b border-border pb-0 max-w-full relative ${isWorkspace ? 'px-4' : ''}`}>
        <div className="flex space-x-1 min-w-0">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: Activity },
            { id: 'workorder', label: t('tab-workorder'), icon: FileText },
            { id: 'whatsapp', label: t('tab-whatsapp'), icon: MessageSquare },
            { id: 'agents', label: 'Agent Config', icon: Sliders },
            { id: 'business', label: t('tab-business'), icon: Building2 },
            { id: 'analytics', label: 'Analytics', icon: TrendingUp },
            { id: 'settings', label: 'Settings', icon: SettingsIcon },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-1.5 text-xs px-3.5 py-2.5 transition-all whitespace-nowrap font-medium border-b-2 -mb-px ${
                  isActive
                    ? 'text-primary border-primary'
                    : 'text-text-muted hover:text-text border-transparent hover:border-border-strong'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Content Area */}
      <main className={isWorkspace ? 'flex-1 min-h-0 flex flex-col px-4 py-3' : 'flex-1'}>
        {activeTab === 'dashboard' && <Dashboard t={t} lang={lang} />}
        {activeTab === 'workorder' && <WorkOrder t={t} />}

        {/* WhatsApp Subtabs nested page */}
        {activeTab === 'whatsapp' && (
          <div className="space-y-6">
            <div className="flex space-x-1 border-b border-border pb-0">
              {[
                { id: 'conversations', label: t('wa-conversations'), icon: MessageSquare },
                { id: 'leads', label: t('wa-leads'), icon: Users },
                { id: 'quotations', label: t('wa-quotations'), icon: FileText },
              ].map((sub) => {
                const Icon = sub.icon;
                const isActive = waSubTab === sub.id;
                return (
                  <button
                    key={sub.id}
                    onClick={() => setWaSubTab(sub.id)}
                    className={`flex items-center space-x-1.5 text-xs px-3.5 py-2.5 transition-all border-b-2 -mb-px ${
                      isActive
                        ? 'text-primary border-primary'
                        : 'text-text-muted hover:text-text border-transparent hover:border-border-strong'
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
        {activeTab === 'business' && <BusinessConfig t={t} />}
        {activeTab === 'analytics' && <Analytics />}
        {activeTab === 'settings' && <Settings t={t} />}
      </main>

      {/* Footer — omitted in workspace focus mode; every pixel of vertical
          space there belongs to the live run, not a fixed footer line. */}
      {!isWorkspace && (
        <footer className="pt-6 border-t border-border text-center text-[10px] text-text-faint font-mono flex items-center justify-between">
          <span>{t('footer-doc')}</span>
          <span>{t('footer-power')}</span>
        </footer>
      )}
    </div>
  );
}
