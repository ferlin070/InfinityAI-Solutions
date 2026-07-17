import React, { useState } from 'react';
import { Lock, Mail, Shield, AlertCircle } from 'lucide-react';
import { login } from '../api';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await login(email, password);
      if (res && res.status === 'ok') {
        onLoginSuccess();
      } else {
        setError(res?.message || 'E-mel atau kata laluan tidak sah.');
      }
    } catch (err) {
      setError('Sambungan ke pelayan terputus.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      {/* Decorative gradients */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-teal/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-md glass-panel p-8 space-y-6 glow-purple">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-xl bg-primary/10 border border-primary/20 text-primary-hover mb-2">
            <Shield className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-text">InfinityAI Solutions</h2>
          <p className="text-xs text-text-muted">Log masuk untuk mengakses AI Command Center & Dashboard WhatsApp</p>
        </div>

        {error && (
          <div className="p-3 bg-accent-red/10 border border-accent-red/20 rounded-lg flex items-center space-x-2 text-xs text-accent-red">
            <AlertCircle className="w-4.5 h-4.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">E-mel</label>
            <div className="relative">
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="nama@syarikat.com"
                className="w-full bg-background/50 border border-card-border focus:border-primary/50 outline-none p-3 pl-10 rounded-lg text-xs text-text transition-all"
              />
              <Mail className="w-4 h-4 text-text-muted absolute left-3 top-3.5" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">Kata Laluan</label>
            <div className="relative">
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full bg-background/50 border border-card-border focus:border-primary/50 outline-none p-3 pl-10 rounded-lg text-xs text-text transition-all"
              />
              <Lock className="w-4 h-4 text-text-muted absolute left-3 top-3.5" />
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-primary hover:bg-primary-hover text-white py-3 rounded-lg font-bold transition-all disabled:opacity-50 text-xs mt-2"
          >
            {loading ? 'Mengotentikasi...' : 'Log Masuk'}
          </button>
        </form>
      </div>
    </div>
  );
}
