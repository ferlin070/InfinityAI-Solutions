import React, { useState, useEffect } from 'react';
import { 
  Send, Sliders, Clipboard, RefreshCw, Zap, ShieldAlert, 
  CheckCircle, Play, AlertCircle, Bot 
} from 'lucide-react';
import { fetchExecute, fetchHistory } from '../api';

export default function WorkOrder({ t }) {
  const [promptText, setPromptText] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [executing, setExecuting] = useState(false);
  const [logLines, setLogLines] = useState([]);
  const [finalResult, setFinalResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [refNo, setRefNo] = useState('');

  useEffect(() => {
    generateRefNo();
  }, []);

  function generateRefNo() {
    const num = Math.floor(1000 + Math.random() * 9000);
    setRefNo(`WO-2026-${num}`);
  }

  async function handleSend() {
    if (!promptText.trim()) return;
    setExecuting(true);
    setErrorMsg(null);
    setFinalResult(null);
    setLogLines([
      { time: new Date().toLocaleTimeString(), text: 'Menerima arahan daripada Bos...' },
      { time: new Date().toLocaleTimeString(), text: 'Claudia sedang menganalisis tugasan...' }
    ]);

    try {
      const response = await fetchExecute(promptText, model);
      if (response && response.status === 'success') {
        const lines = [...logLines];
        // Append specialist completion logs
        if (response.results) {
          response.results.forEach(res => {
            lines.push({
              time: new Date().toLocaleTimeString(),
              text: `Ejen ${res.agent} telah menyiapkan tugasan.`
            });
          });
        }
        lines.push({
          time: new Date().toLocaleTimeString(),
          text: 'Semua arahan kerja berjaya diselesaikan!'
        });
        setLogLines(lines);
        setFinalResult(response);
      } else {
        const errMsg = response?.message || 'Claudia menolak tugasan: Ralat tidak diketahui.';
        setLogLines(prev => [
          ...prev, 
          { time: new Date().toLocaleTimeString(), text: `Ditolak: ${errMsg}`, isError: true }
        ]);
        setErrorMsg(errMsg);
      }
    } catch (err) {
      setLogLines(prev => [
        ...prev, 
        { time: new Date().toLocaleTimeString(), text: 'Sambungan terputus. Sila cuba lagi.', isError: true }
      ]);
      setErrorMsg('Sambungan ke pelayan terputus.');
    } finally {
      setExecuting(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Input panel */}
      <div className="glass-card p-5 space-y-4 h-fit">
        <div className="flex items-center justify-between border-b border-card-border pb-3">
          <div>
            <h3 className="text-base font-semibold">{t('borang-title')}</h3>
            <p className="text-xs text-text-muted">{t('borang-note')}</p>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 rounded bg-card-border/40 text-primary-hover">{refNo}</span>
        </div>

        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-text-muted">{t('enjin-ai')}</label>
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
            <label className="text-xs font-semibold text-text-muted">{t('butiran-arahan')}</label>
            <textarea
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              rows={6}
              placeholder={t('placeholder-arahan')}
              className="w-full bg-background border border-card-border focus:border-primary/50 outline-none p-3 rounded text-xs text-text leading-relaxed"
            />
          </div>

          <button
            onClick={handleSend}
            disabled={executing || !promptText.trim()}
            className="w-full flex items-center justify-center space-x-2 text-xs bg-primary hover:bg-primary-hover text-white py-3 rounded-lg font-bold transition-all disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>{executing ? t('btn-sending') : t('btn-send')}</span>
          </button>
        </div>
      </div>

      {/* Output and logs */}
      <div className="lg:col-span-2 space-y-6">
        {/* Terminal Log */}
        <div className="glass-card p-5 space-y-3 flex flex-col h-64">
          <div className="flex items-center justify-between border-b border-card-border pb-2">
            <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">{t('log-title')}</h3>
            <span className="text-[10px] text-accent-green bg-accent-green/10 px-2 py-0.5 rounded font-mono flex items-center">
              <Zap className="w-3 h-3 mr-0.5 pulse-green" /> {t('log-note')}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto font-mono text-[11px] space-y-2 pr-1">
            {logLines.length > 0 ? (
              logLines.map((line, idx) => (
                <div key={idx} className={`flex space-x-2 ${line.isError ? 'text-accent-red' : 'text-text-muted'}`}>
                  <span className="text-text-dark">[{line.time}]</span>
                  <span>{line.text}</span>
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-text-muted py-12">
                {t('log-empty')}
              </div>
            )}
          </div>
        </div>

        {/* Final output */}
        {finalResult && (
          <div className="glass-panel p-5 space-y-4 border border-accent-green/20 glow-green">
            <div className="flex items-center justify-between border-b border-card-border pb-3">
              <span className="flex items-center text-xs font-bold text-accent-green">
                <CheckCircle className="w-4.5 h-4.5 mr-1.5" />
                {t('minit-kerja')}
              </span>
              <span className="font-mono text-xs text-text-muted">{finalResult.total_speed}</span>
            </div>

            <div className="space-y-4">
              {finalResult.results && finalResult.results.map((res, idx) => (
                <div key={idx} className="space-y-2 p-3 bg-background/50 border border-card-border rounded-lg">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold flex items-center">
                      <Bot className="w-4 h-4 mr-1.5 text-primary" />
                      Ejen: {res.agent}
                    </span>
                    <span className="font-mono text-[10px] text-text-muted">{res.speed}</span>
                  </div>
                  <p className="font-mono text-xs text-text-muted leading-relaxed whitespace-pre-wrap">
                    {res.result}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {errorMsg && (
          <div className="glass-panel p-5 border border-accent-red/20 bg-accent-red/5 flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-accent-red mt-0.5 flex-shrink-0" />
            <div className="text-xs space-y-1">
              <h4 className="font-bold text-accent-red">Task Rejected by Claudia</h4>
              <p className="text-text-muted leading-relaxed">{errorMsg}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
