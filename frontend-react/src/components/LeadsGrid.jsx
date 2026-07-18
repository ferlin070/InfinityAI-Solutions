import React, { useState, useEffect } from 'react';
import { Flame, TrendingUp, Compass, Search } from 'lucide-react';
import { fetchLeads } from '../api';

export default function LeadsGrid() {
  const [leads, setLeads] = useState([]);
  const [filter, setFilter] = useState(''); // '', 'hot', 'warm', 'cold'
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadLeads();
  }, [filter]);

  async function loadLeads() {
    try {
      const data = await fetchLeads(filter);
      if (data) setLeads(data);
    } catch (e) {
      console.error(e);
    }
  }

  const filtered = leads.filter(l => {
    const term = search.toLowerCase();
    const name = (l.name || '').toLowerCase();
    const phone = (l.phone || '').toLowerCase();
    const interest = (l.interest_summary || '').toLowerCase();
    return name.includes(term) || phone.includes(term) || interest.includes(term);
  });

  const scoreMeta = {
    hot: { icon: Flame, color: 'text-accent-danger', bg: 'bg-accent-danger/10', label: 'Hot' },
    warm: { icon: TrendingUp, color: 'text-accent-gold', bg: 'bg-accent-gold/10', label: 'Warm' },
    cold: { icon: Compass, color: 'text-text-muted', bg: 'bg-surface-raised', label: 'Cold' },
  };

  return (
    <div className="space-y-4">
      {/* Header and filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-4 rounded-xl border border-border">
        <div className="flex space-x-1.5 text-xs">
          {[
            { key: '', label: 'Semua' },
            { key: 'hot', label: 'Hot', color: 'text-accent-danger bg-accent-danger/10' },
            { key: 'warm', label: 'Warm', color: 'text-accent-gold bg-accent-gold/10' },
            { key: 'cold', label: 'Cold', color: 'text-text-muted bg-surface-raised' },
          ].map((btn) => (
            <button
              key={btn.key}
              onClick={() => setFilter(btn.key)}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                filter === btn.key 
                  ? 'bg-primary text-white font-semibold' 
                  : 'bg-surface hover:bg-surface-raised border border-border'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>

        <div className="relative">
          <input 
            type="text" 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari prospek..."
            className="input-field w-full sm:w-64"
          />
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-3" />
        </div>
      </div>

      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((l) => {
            const meta = scoreMeta[l.score] || scoreMeta.cold;
            const ScoreIcon = meta.icon;
            return (
              <div key={l.id} className="glass-card p-5 space-y-3 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-sm">{l.name || 'Anonymous Prospect'}</h4>
                      <p className="text-[10px] text-text-muted">{l.phone}</p>
                    </div>
                    
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${meta.bg} ${meta.color} flex items-center`}>
                      <ScoreIcon className="w-3 h-3 mr-0.5" /> {meta.label}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Ringkasan Minat</span>
                    <p className="text-xs text-text-muted leading-relaxed line-clamp-3">
                      {l.interest_summary || 'Tiada maklumat minat didokumenkan.'}
                    </p>
                  </div>
                </div>

                {l.score_reason && (
                  <div className="pt-2 border-t border-border/50 text-[10px] text-text-faint italic leading-relaxed">
                    Kenapa: {l.score_reason}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center text-xs text-text-muted py-24 glass-card flex flex-col items-center justify-center">
          <Compass className="w-8 h-8 text-border mb-2" />
          <p>Tiada prospek ditemui. Leads akan muncul selepas pelanggan mula berinteraksi di WhatsApp.</p>
        </div>
      )}
    </div>
  );
}