import React from 'react';
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip 
} from 'recharts';
import { 
  ThumbsUp, MessageCircle, Hourglass, Percent, Lightbulb 
} from 'lucide-react';

const topicsData = [
  { topic: 'Harga Produk', count: 145 },
  { topic: 'Cara Bayaran', count: 98 },
  { topic: 'Status Penghantaran', count: 64 },
  { topic: 'Polisi Pemulangan', count: 42 },
  { topic: 'Pertanyaan Am', count: 35 },
];

const hourlyTraffic = [
  { hour: '08:00', load: 15 },
  { hour: '10:00', load: 45 },
  { hour: '12:00', load: 60 },
  { hour: '14:00', load: 55 },
  { hour: '16:00', load: 80 },
  { hour: '18:00', load: 40 },
  { hour: '20:00', load: 25 },
];

export default function Analytics() {
  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 space-y-2">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg. Response Time</span>
            <Hourglass className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold tracking-tight">1.8s</p>
          <span className="text-[10px] text-accent-success bg-accent-success/5 px-2 py-0.5 rounded">Fast SLA compliance</span>
        </div>

        <div className="glass-card p-5 space-y-2">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-semibold uppercase tracking-wider">Resolution Rate</span>
            <Percent className="w-4 h-4 text-accent-success" />
          </div>
          <p className="text-3xl font-bold tracking-tight">88.4%</p>
          <span className="text-[10px] text-accent-success bg-accent-success/5 px-2 py-0.5 rounded">+2.1% from yesterday</span>
        </div>

        <div className="glass-card p-5 space-y-2">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-semibold uppercase tracking-wider">AI Handover Ratio</span>
            <MessageCircle className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold tracking-tight">11.6%</p>
          <span className="text-[10px] text-text-muted">Requires manual takeover</span>
        </div>

        <div className="glass-card p-5 space-y-2">
          <div className="flex items-center justify-between text-text-muted">
            <span className="text-xs font-semibold uppercase tracking-wider">Sentiment Score</span>
            <ThumbsUp className="w-4 h-4 text-accent-success" />
          </div>
          <p className="text-3xl font-bold tracking-tight">Positive (94%)</p>
          <span className="text-[10px] text-accent-success bg-accent-success/5 px-2 py-0.5 rounded">High customer confidence</span>
        </div>
      </div>

      {/* Topics & Traffic Graph Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Topics Chart */}
        <div className="glass-card p-5 space-y-4">
          <div>
            <h3 className="text-base font-semibold">Topik Hangat / Popular Topics</h3>
            <p className="text-xs text-text-muted">Kekerapan kategori pertanyaan yang diajukan oleh prospek</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topicsData} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 5 }}>
                <XAxis type="number" stroke="#5E6470" fontSize={11} tickLine={false} />
                <YAxis dataKey="topic" type="category" stroke="#5E6470" fontSize={11} tickLine={false} width={80} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#12151B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', color: '#E8E9EC' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Bar dataKey="count" fill="#6C63FF" radius={[0, 4, 4, 0]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Traffic Load Graph */}
        <div className="glass-card p-5 space-y-4">
          <div>
            <h3 className="text-base font-semibold">Trafik Waktu Puncak / Hourly Peak Traffic</h3>
            <p className="text-xs text-text-muted">Kesesakan beban perbualan mengikut jam bekerja harian</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourlyTraffic} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                <XAxis dataKey="hour" stroke="#5E6470" fontSize={11} tickLine={false} />
                <YAxis stroke="#5E6470" fontSize={11} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#12151B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', color: '#E8E9EC' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Bar dataKey="load" fill="#C9A961" radius={[4, 4, 0, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* AI Recommendations card */}
      <div className="glass-card p-5 space-y-3 border border-primary/10 glow-primary">
        <h4 className="text-xs font-bold text-primary uppercase tracking-wider flex items-center">
          <Lightbulb className="w-4 h-4 mr-2" />
          Cadangan Pintar Ejen / AI Operations Insights
        </h4>
        <ul className="text-xs space-y-2 text-text-muted list-disc list-inside leading-relaxed">
          <li>Trafik jualan dikesan meningkat sebanyak 15% pada jam <span className="font-semibold text-text">16:00 - 18:00</span>. Cadangan: Pastikan Maya (Ejen Jualan) tidak berada di luar talian.</li>
          <li>Topik <span className="font-semibold text-text">Harga Produk</span> adalah yang tertinggi. Anda boleh meningkatkan keberkesanan dengan mengemas kini katalog harga di Agent Config secara berkala.</li>
          <li>Kadar resolusi AI meningkat kepada <span className="font-semibold text-text">88.4%</span>, mengurangkan keperluan intervensi staf jualan sebanyak 5% minggu ini.</li>
        </ul>
      </div>
    </div>
  );
}