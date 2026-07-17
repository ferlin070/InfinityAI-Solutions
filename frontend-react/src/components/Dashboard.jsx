import React, { useState, useEffect } from 'react';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip 
} from 'recharts';
import { 
  MessageSquare, Clock, CheckCircle, TrendingUp, Activity, 
  Wifi, WifiOff, Users, ArrowUpRight, ShieldAlert 
} from 'lucide-react';
import { fetchHistory, fetchConversations, fetchLeads, fetchQuotations, fetchChannels } from '../api';

const trendData = [
  { day: 'Mon', chats: 45, unresolved: 5 },
  { day: 'Tue', chats: 72, unresolved: 8 },
  { day: 'Wed', chats: 98, unresolved: 12 },
  { day: 'Thu', chats: 85, unresolved: 6 },
  { day: 'Fri', chats: 110, unresolved: 15 },
  { day: 'Sat', chats: 64, unresolved: 4 },
  { day: 'Sun', chats: 50, unresolved: 2 },
];

export default function Dashboard({ t, lang }) {
  const [metrics, setMetrics] = useState({
    totalChats: 0,
    activeChats: 0,
    leadsCount: 0,
    pendingQuotes: 0,
  });
  const [historyLogs, setHistoryLogs] = useState([]);
  const [channels, setChannels] = useState([]);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const history = await fetchHistory() || [];
        const convs = await fetchConversations() || [];
        const leads = await fetchLeads() || [];
        const quotes = await fetchQuotations('pending_approval') || [];
        const chs = await fetchChannels() || [];

        setHistoryLogs(history.slice(0, 10)); // Top 10 items
        setChannels(chs);

        setMetrics({
          totalChats: history.length,
          activeChats: convs.filter(c => c.status === 'open').length,
          leadsCount: leads.length,
          pendingQuotes: quotes.length
        });
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      }
    }
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  const stats = [
    { 
      label: t('total-tasks'), 
      value: metrics.totalChats, 
      change: '+12%', 
      icon: TrendingUp,
      color: 'text-primary'
    },
    { 
      label: t('wa-conversations'), 
      value: metrics.activeChats, 
      change: 'Active Now', 
      icon: MessageSquare,
      color: 'text-accent-teal'
    },
    { 
      label: t('wa-leads'), 
      value: metrics.leadsCount, 
      change: '+8 new', 
      icon: Users,
      color: 'text-accent-green'
    },
    { 
      label: t('wa-quotations'), 
      value: metrics.pendingQuotes, 
      change: 'Awaiting review', 
      icon: ShieldAlert,
      color: 'text-accent-purple'
    }
  ];

  return (
    <div className="space-y-6">
      {/* WhatsApp Connection Indicator */}
      <div className="glass-panel p-4 flex items-center justify-between glow-purple">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className={`w-3 h-3 rounded-full ${channels.length > 0 ? 'bg-accent-green pulse-green' : 'bg-accent-red'}`} />
          </div>
          <div>
            <h4 className="text-sm font-semibold">WhatsApp AI Gateway</h4>
            <p className="text-xs text-text-muted">
              {channels.length > 0 
                ? `${channels.length} ${t('wa-phone-placeholder')} connected` 
                : t('wa-no-channels')
              }
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {channels.length > 0 ? (
            <span className="flex items-center text-xs text-accent-green bg-accent-green/10 px-2.5 py-1 rounded-full font-medium">
              <Wifi className="w-3.5 h-3.5 mr-1" /> Connected
            </span>
          ) : (
            <span className="flex items-center text-xs text-accent-red bg-accent-red/10 px-2.5 py-1 rounded-full font-medium">
              <WifiOff className="w-3.5 h-3.5 mr-1" /> Offline
            </span>
          )}
        </div>
      </div>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div key={idx} className="glass-card p-5 flex flex-col justify-between">
              <div className="flex items-start justify-between">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">{s.label}</span>
                <div className={`p-2 rounded-lg bg-card-border ${s.color}`}>
                  <Icon className="w-4.5 h-4.5" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline justify-between">
                <span className="text-3xl font-bold tracking-tight">{s.value}</span>
                <span className="text-xs font-medium text-accent-green flex items-center bg-accent-green/5 px-2 py-0.5 rounded">
                  <ArrowUpRight className="w-3 h-3 mr-0.5" /> {s.change}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Charts & History section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recharts Area Chart */}
        <div className="glass-card lg:col-span-2 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold">Conversation Trends</h3>
              <p className="text-xs text-text-muted">Analysis of inbound message traffic vs unresolved leads</p>
            </div>
            <div className="flex space-x-3 text-xs">
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-primary mr-1.5" /> Total Chats</span>
              <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-accent-teal mr-1.5" /> Unresolved</span>
            </div>
          </div>
          
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorChats" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorUnresolved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" stroke="#4b5563" fontSize={11} tickLine={false} />
                <YAxis stroke="#4b5563" fontSize={11} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(10, 15, 28, 0.95)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', color: '#fff' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="chats" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorChats)" />
                <Area type="monotone" dataKey="unresolved" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorUnresolved)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Live Activity Logbook */}
        <div className="glass-card p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold">{t('buku-log')}</h3>
              <p className="text-xs text-text-muted">{t('log-update')}</p>
            </div>
            <Activity className="w-4 h-4 text-primary pulse-green" />
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-64">
            {historyLogs.length > 0 ? (
              historyLogs.map((log, idx) => (
                <div key={idx} className="flex items-start justify-between p-2.5 rounded bg-card-border/30 hover:bg-card-border/50 transition-colors text-xs">
                  <div className="space-y-1">
                    <span className="font-semibold">{log.agent}</span>
                    <span className="text-[10px] text-text-muted block">{log.timestamp}</span>
                  </div>
                  <div className="text-right space-y-1">
                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary-hover font-mono text-[10px]">{log.model}</span>
                    <span className="text-[10px] text-accent-green font-medium block">{log.speed}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-text-muted py-12">
                No recent activity.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
