import React, { useState, useEffect } from 'react';
import { FileText, Check, Calendar, CheckCircle } from 'lucide-react';
import { fetchQuotations, fetchApproveQuotation } from '../api';

export default function QuotationsList() {
  const [quotes, setQuotes] = useState([]);
  const [loadingId, setLoadingId] = useState(null);

  useEffect(() => {
    loadQuotations();
  }, []);

  async function loadQuotations() {
    try {
      const data = await fetchQuotations('pending_approval') || [];
      setQuotes(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleApprove(id) {
    setLoadingId(id);
    try {
      const res = await fetchApproveQuotation(id);
      if (res && res.status === 'ok') {
        setQuotes(prev => prev.filter(q => q.id !== id));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div className="space-y-4">
      {quotes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quotes.map((q) => (
            <div key={q.id} className="glass-card p-5 space-y-4 border border-primary/10 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-start justify-between border-b border-border pb-2.5">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-primary" />
                    <div>
                      <h4 className="font-semibold text-xs text-text">Sebut Harga #{q.id.slice(0, 8).toUpperCase()}</h4>
                      <span className="text-[10px] text-text-faint flex items-center mt-0.5">
                        <Calendar className="w-3.5 h-3.5 mr-1" />
                        {q.created_at ? q.created_at.split('T')[0] : ''}
                      </span>
                    </div>
                  </div>
                  
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-gold/10 text-accent-gold">
                    Awaiting Approval
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Pelanggan:</span>
                    <span className="font-semibold">{q.contacts?.name || q.contacts?.phone || 'WhatsApp Prospect'}</span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider block">Butiran Item</span>
                    <div className="divide-y divide-border/30 bg-surface-raised rounded p-2">
                      {q.items && q.items.map((it, idx) => (
                        <div key={idx} className="flex justify-between py-1 text-[11px]">
                          <span className="text-text-muted">{it.name} (x{it.qty || 1})</span>
                          <span className="font-mono text-text">RM{(it.price || 0).toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex justify-between border-t border-border/50 pt-2 text-sm">
                    <span className="font-semibold text-text-muted">Jumlah Keseluruhan:</span>
                    <span className="font-bold text-accent-success font-mono">RM{(q.total_amount || 0).toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  onClick={() => handleApprove(q.id)}
                  disabled={loadingId === q.id}
                  className="btn-primary flex-1 justify-center"
                >
                  <Check className="w-4 h-4 mr-1.5" />
                  <span>{loadingId === q.id ? 'Meluluskan...' : 'Luluskan & Hantar'}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-xs text-text-muted py-24 glass-card flex flex-col items-center justify-center space-y-2">
          <CheckCircle className="w-10 h-10 text-accent-success/60" />
          <p>Tiada sebut harga menunggu kelulusan buat masa ini.</p>
        </div>
      )}
    </div>
  );
}