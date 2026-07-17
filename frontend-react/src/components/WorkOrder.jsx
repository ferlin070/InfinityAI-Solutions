import React, { useState, useEffect, useRef } from 'react';
import {
  Send, Bot, User, Loader2, AlertCircle, Trash2, ImageOff
} from 'lucide-react';
import { streamChat, fetchChatHistory, clearChat } from '../api';

function uid() {
  return (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
}

function AgentResultBlock({ result }) {
  return (
    <div className="space-y-2 p-3 bg-background/50 border border-card-border rounded-lg">
      <div className="flex items-center justify-between text-xs">
        <span className="font-bold flex items-center">
          <Bot className="w-3.5 h-3.5 mr-1.5 text-primary" />
          {result.agent}
        </span>
        <span className="font-mono text-[10px] text-text-muted">{result.speed}</span>
      </div>
      <p className="font-mono text-xs text-text-muted leading-relaxed whitespace-pre-wrap">
        {result.result}
      </p>
      {(result.artifacts || []).map((artifact, idx) => (
        artifact.type === 'image' && artifact.data_base64 ? (
          <img
            key={idx}
            src={`data:${artifact.mime_type || 'image/png'};base64,${artifact.data_base64}`}
            alt={artifact.caption || 'Imej dijana'}
            className="rounded-lg border border-card-border max-w-full mt-2"
          />
        ) : (
          <div key={idx} className="flex items-center text-[10px] text-text-muted space-x-1.5">
            <ImageOff className="w-3 h-3" />
            <span>Gagal papar imej.</span>
          </div>
        )
      ))}
    </div>
  );
}

function ChatBubble({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-lg p-3 text-xs space-y-2 ${
        isUser
          ? 'bg-primary/20 border border-primary/20 text-text'
          : message.isError
            ? 'bg-accent-red/10 border border-accent-red/20 text-text'
            : 'bg-card border border-card-border text-text'
      }`}>
        <div className="flex items-center space-x-1.5 text-[10px] text-text-muted">
          {isUser ? <User className="w-3 h-3 text-accent-teal" /> : <Bot className="w-3 h-3 text-primary-hover" />}
          <span className="font-semibold">{isUser ? 'Bos' : 'Claudia'}</span>
        </div>

        {isUser && <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>}

        {!isUser && message.pending && (
          <div className="flex items-center space-x-2 text-text-muted">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>{message.statusText || 'Sedang berfikir...'}</span>
          </div>
        )}

        {!isUser && !message.pending && message.isError && (
          <div className="flex items-start space-x-2">
            <AlertCircle className="w-3.5 h-3.5 text-accent-red mt-0.5 flex-shrink-0" />
            <p className="leading-relaxed text-text-muted">{message.content}</p>
          </div>
        )}

        {!isUser && !message.pending && !message.isError && message.results && (
          <div className="space-y-2">
            {message.results.map((r, idx) => <AgentResultBlock key={idx} result={r} />)}
          </div>
        )}

        {!isUser && !message.pending && !message.isError && !message.results && (
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        )}
      </div>
    </div>
  );
}

export default function WorkOrder({ t }) {
  const [messages, setMessages] = useState([]);
  const [promptText, setPromptText] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const threadEndRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const history = await fetchChatHistory();
        if (history) {
          setMessages(history.map((m) => ({
            id: uid(),
            role: m.role === 'assistant' ? 'assistant' : 'user',
            content: m.content,
          })));
        }
      } catch (e) {
        console.error('fetchChatHistory error:', e);
      } finally {
        setLoadingHistory(false);
      }
    })();
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend() {
    const prompt = promptText.trim();
    if (!prompt || sending) return;

    const assistantId = uid();
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: 'user', content: prompt },
      { id: assistantId, role: 'assistant', pending: true, statusText: 'Menghantar arahan kepada Claudia...' },
    ]);
    setPromptText('');
    setSending(true);

    const updateAssistant = (patch) => {
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, ...patch } : m)));
    };

    try {
      await streamChat(prompt, model, (eventType, payload) => {
        if (eventType === 'status') {
          updateAssistant({ statusText: payload.text });
        } else if (eventType === 'agent_start') {
          updateAssistant({ statusText: `${payload.agent} sedang bekerja...` });
        } else if (eventType === 'tool_call') {
          updateAssistant({
            statusText: payload.status === 'start'
              ? `${payload.agent} sedang guna ${payload.tool}...`
              : `${payload.agent} hampir siap...`,
          });
        } else if (eventType === 'agent_done') {
          updateAssistant({ statusText: `${payload.agent} telah selesai.` });
        } else if (eventType === 'final') {
          if (payload.status === 'success') {
            updateAssistant({ pending: false, results: payload.results || [] });
          } else {
            updateAssistant({ pending: false, content: payload.message || 'Selesai.' });
          }
        } else if (eventType === 'error') {
          updateAssistant({ pending: false, isError: true, content: payload.message || 'Ralat tidak diketahui.' });
        }
      });
    } catch (e) {
      console.error('streamChat error:', e);
      updateAssistant({ pending: false, isError: true, content: 'Sambungan ke pelayan terputus.' });
    } finally {
      setSending(false);
    }
  }

  async function handleClear() {
    if (!confirm('Kosongkan sejarah perbualan dengan Claudia?')) return;
    try {
      await clearChat();
      setMessages([]);
    } catch (e) {
      console.error('clearChat error:', e);
    }
  }

  return (
    <div className="glass-panel flex flex-col h-[75vh] overflow-hidden">
      <div className="p-4 border-b border-card-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm flex items-center">
            <Bot className="w-4 h-4 mr-2 text-primary" />
            {t('claudia-desc')}
          </h3>
          <p className="text-xs text-text-muted">{t('log-note')}</p>
        </div>
        <button
          onClick={handleClear}
          title="Kosongkan perbualan"
          className="text-text-muted hover:text-accent-red transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loadingHistory ? (
          <div className="h-full flex items-center justify-center text-xs text-text-muted">
            Memuatkan perbualan...
          </div>
        ) : messages.length > 0 ? (
          messages.map((m) => <ChatBubble key={m.id} message={m} />)
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-text-muted space-y-2 py-24">
            <Bot className="w-10 h-10 text-card-border" />
            <p className="text-xs">{t('log-empty')}</p>
          </div>
        )}
        <div ref={threadEndRef} />
      </div>

      <div className="p-4 border-t border-card-border bg-card/20 space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-[10px] font-semibold text-text-muted">{t('enjin-ai')}</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="bg-background border border-card-border focus:border-primary/50 outline-none px-2 py-1 rounded text-[10px] text-text"
          >
            <option value="gpt-4o-mini">GPT-4o mini (Recommended)</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="o3-mini">o3-mini (Reasoning)</option>
          </select>
        </div>
        <div className="flex items-end space-x-2">
          <textarea
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={2}
            placeholder={t('placeholder-arahan')}
            disabled={sending}
            className="flex-1 resize-none bg-background/50 border border-card-border focus:border-primary/50 outline-none rounded-lg p-2.5 text-xs text-text transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={sending || !promptText.trim()}
            className="p-2.5 rounded-lg bg-primary hover:bg-primary-hover text-white disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
