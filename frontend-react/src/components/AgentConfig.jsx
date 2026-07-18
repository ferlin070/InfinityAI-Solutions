import React, { useState, useEffect } from 'react';
import { Sliders, Save, RefreshCw, Play, Sparkles, MessageCircle, Bot } from 'lucide-react';
import { apiGet, apiPost } from '../api';

const AGENT_KEYS = [
  { key: 'CLAUDIA', name: 'Claudia', role: 'Chief of Staff' },
  { key: 'MAYA', name: 'Maya', role: 'Sales & CRM' },
  { key: 'ZARA', name: 'Zara', role: 'Kewangan / Finance' },
  { key: 'AIMAN', name: 'Aiman', role: 'Pemasaran / Marketing' },
  { key: 'DANISH', name: 'Danish', role: 'Kandungan / Content' },
  { key: 'HAKIM', name: 'Hakim', role: 'Teknikal / Systems' },
  { key: 'AMELIA', name: 'Amelia', role: 'Latihan / Training' },
  { key: 'ADILA', name: 'Adila', role: 'Operasi / Operations' },
];

export default function AgentConfig({ t }) {
  const [selectedAgent, setSelectedAgent] = useState('MAYA');
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [provider, setProvider] = useState('openai');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // Real-time Preview Simulator state
  const [simInput, setSimInput] = useState('');
  const [simOutput, setSimOutput] = useState('');
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    loadAgentConfig(selectedAgent);
  }, [selectedAgent]);

  async function loadAgentConfig(key) {
    try {
      const data = await apiGet(`/api/agents/${key}`);
      if (data) {
        setPrompt(data.system_prompt || '');
        setModel(data.model || 'gpt-4o-mini');
        setProvider(data.provider || 'openai');
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const res = await apiPost(`/api/agents/${selectedAgent}`, {
        system_prompt: prompt,
        model: model,
        provider: provider,
      });
      if (res) {
        setMessage({ type: 'success', text: 'Konfigurasi ejen berjaya disimpan!' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Gagal menyimpan konfigurasi.' });
      console.error(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleSimulate() {
    if (!simInput.trim()) return;
    setSimulating(true);
    setSimOutput('');
    try {
      // Call test executions endpoint
      const res = await apiPost('/api/executions', {
        prompt: `[Uji Ejen: ${selectedAgent}] Mesej pelanggan: "${simInput}"`,
        model: model
      });
      if (res && res.results) {
        // Find result from selected agent or fallback to total results
        const agentResult = res.results.find(r => r.agent.toUpperCase() === selectedAgent) 
          || res.results[0];
        setSimOutput(agentResult ? agentResult.result : res.message || 'Tiada respons.');
      } else {
        setSimOutput(res.message || 'Tiada respons.');
      }
    } catch (e) {
      setSimOutput('Error: Gagal menghubungkan simulasi.');
      console.error(e);
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left panel - Agent selection */}
      <div className="glass-card p-5 space-y-4 h-fit">
        <h3 className="text-base font-semibold flex items-center">
          <Bot className="w-4 h-4 mr-2 text-primary" />
          Senarai Ejen AI
        </h3>
        <p className="text-xs text-text-muted">Pilih ejen di bawah untuk mengubah suai prompt sistem atau konfigurasi parameter.</p>
        
        <div className="space-y-2">
          {AGENT_KEYS.map((a) => (
            <button
              key={a.key}
              onClick={() => setSelectedAgent(a.key)}
              className={`w-full text-left p-3 rounded-lg text-xs transition-all flex flex-col space-y-1 ${
                selectedAgent === a.key 
                  ? 'bg-primary/20 border border-primary/30 font-semibold' 
                  : 'bg-card-border/10 hover:bg-card-border/30 border border-transparent'
              }`}
            >
              <span>{a.name}</span>
              <span className="text-[10px] text-text-muted">{a.role}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Middle panel - Settings Form */}
      <div className="glass-card lg:col-span-2 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-card-border pb-3">
          <div>
            <h3 className="text-base font-semibold">Konfigurasi Ejen: {selectedAgent.charAt(0).toUpperCase() + selectedAgent.slice(1).toLowerCase()}</h3>
            <p className="text-xs text-text-muted">Edit tingkah laku, arahan personaliti dan penetapan enjin AI.</p>
          </div>
          
          <button 
            onClick={handleSave}
            disabled={saving}
            className="flex items-center text-xs bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            <Save className="w-3.5 h-3.5 mr-1.5" />
            {saving ? 'Menyimpan...' : 'Simpan Tetapan'}
          </button>
        </div>

        {message && (
          <div className={`p-3 rounded text-xs ${
            message.type === 'success' ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'
          }`}>
            {message.text}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">Enjin AI / Model</label>
            <select 
              value={model} 
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-background border border-card-border focus:border-primary/50 outline-none p-2.5 rounded text-xs text-text"
            >
              <option value="gpt-4o-mini">GPT-4o mini (Recommended)</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="o3-mini">o3-mini (Reasoning)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">Penyedia AI / Provider</label>
            <select 
              value={provider} 
              onChange={(e) => setProvider(e.target.value)}
              className="w-full bg-background border border-card-border focus:border-primary/50 outline-none p-2.5 rounded text-xs text-text"
            >
              <option value="openai">OpenAI</option>
              <option value="nvidia">NVIDIA NIM</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-text-muted">Prompt Sistem (Personality / Backstory)</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={10}
            placeholder="Masukkan prompt dasar untuk ejen..."
            className="w-full bg-background border border-card-border focus:border-primary/50 outline-none p-3 rounded text-xs font-mono leading-relaxed"
          />
        </div>

        {/* Simulator Section */}
        <div className="border-t border-card-border pt-4 mt-6 space-y-3">
          <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center">
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-primary-hover" />
            Simulator Ejen Real-Time
          </h4>
          
          <div className="flex space-x-2">
            <input 
              type="text" 
              value={simInput}
              onChange={(e) => setSimInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSimulate();
              }}
              placeholder="Taip mesej untuk menguji ejen ini..."
              className="flex-1 bg-background border border-card-border focus:border-primary/50 outline-none p-2.5 rounded text-xs text-text"
            />
            <button 
              onClick={handleSimulate}
              disabled={simulating || !simInput.trim()}
              className="flex items-center text-xs bg-primary/25 border border-primary/40 hover:bg-primary/45 text-text px-4 py-2.5 rounded font-semibold transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 mr-1.5" />
              {simulating ? 'Menjana...' : 'Test Run'}
            </button>
          </div>

          {simOutput && (
            <div className="p-3 bg-background/50 border border-card-border rounded text-xs space-y-2">
              <div className="flex items-center space-x-1.5 text-[10px] text-text-muted">
                <MessageCircle className="w-3.5 h-3.5 text-primary" />
                <span>Respons Simulasi Ejen:</span>
              </div>
              <p className="font-mono leading-relaxed whitespace-pre-wrap">{simOutput}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
