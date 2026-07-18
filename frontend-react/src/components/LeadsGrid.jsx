import React, { useState, useEffect } from 'react';
import { Users, User, Flame, TrendingUp, Compass, Search } from 'lucide-react';
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

  return (
    <div className="space-y-4">
      {/* Header and filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card-border/10 p-4 rounded-xl border border-card-border/30">
        <div className="flex space-x-1.5 text-xs">
          {[
            { key: '', label: 'Semua' },
            { key: 'hot', label: 'Hot', color: 'text-accent-red bg-accent-red/10' },
            { key: 'warm', label: 'Warm', color: 'text-accent-purple bg-accent-purple/10' },
            { key: 'cold', label: 'Cold', color: 'text-accent-teal bg-accent-teal/10' },
          ].map((btn) => (
            <button
              key={btn.key}
              onClick={() => setFilter(btn.key)}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                filter === btn.key 
                  ? 'bg-primary text-white font-semibold' 
                  : 'bg-card hover:bg-card-border/20 border border-card-border'
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <input 
            type="text" 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari prospek..."
            className="bg-background border border-card-border focus:border-primary/50 outline-none p-2 pl-8 rounded-lg text-xs text-text w-full sm:w-64 transition-all"
          />
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-3" />
        </div>
      </div>

      {/* Grid */}
      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((l) => (
            <div key={l.id} className="glass-card p-5 space-y-3 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold text-sm">{l.name || 'Anonymous Prospect'}</h4>
                    <p className="text-[10px] text-text-muted">{l.phone}</p>
                  </div>
                  
                  {l.score === 'hot' && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-red/10 text-accent-red flex items-center">
                      <Flame className="w-3 h-3 mr-0.5" /> Hot
                    </span>
                  )}
                  {l.score === 'warm' && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-purple/10 text-accent-purple flex items-center">
                      <TrendingUp className="w-3 h-3 mr-0.5" /> Warm
                    </span>
                  )}
                  {l.score === 'cold' && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-teal/10 text-accent-teal flex items-center">
                      <Compass className="w-3 h-3 mr-0.5" /> Cold
                    </span>
                  )}
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Ringkasan Minat</span>
                  <p className="text-xs text-text-muted leading-relaxed line-clamp-3">
                    {l.interest_summary || 'Tiada maklumat minat didokumenkan.'}
                  </p>
                </div>
              </div>

              {l.score_reason && (
                <div className="pt-2 border-t border-card-border/50 text-[10px] text-text-muted italic leading-relaxed">
                  Kenapa: {l.score_reason}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-xs text-text-muted py-24 glass-panel">
          Tiada prospek ditemui.
        </div>
      )}
    </div>
  );
}
