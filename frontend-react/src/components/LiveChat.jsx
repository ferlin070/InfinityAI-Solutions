import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, User, Bot, Send, ShieldAlert, CheckCircle, 
  HelpCircle, UserCheck, RefreshCw 
} from 'lucide-react';
import { 
  fetchConversations, fetchConversationMessages, fetchSendMessage, fetchTakeover 
} from '../api';

export default function LiveChat({ t }) {
  const [conversations, setConversations] = useState([]);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [replyText, setReplyText] = useState('');
  const [loading, setLoading] = useState(false);
  const threadEndRef = useRef(null);

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeConv) {
      loadMessages(activeConv.id);
    }
  }, [activeConv]);

  useEffect(() => {
    // Scroll to bottom of message thread
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function loadConversations() {
    try {
      const data = await fetchConversations();
      if (data) {
        setConversations(data);
        // Sync active conversation
        if (activeConv) {
          const updated = data.find(c => c.id === activeConv.id);
          if (updated) setActiveConv(updated);
        }
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function loadMessages(convId) {
    try {
      const data = await fetchConversationMessages(convId);
      if (data) setMessages(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleSend() {
    if (!replyText.trim() || !activeConv) return;
    setLoading(true);
    try {
      // Find recipient details
      const phone = activeConv.contacts?.phone || '';
      const channelId = activeConv.channel_id;

      await fetchSendMessage(activeConv.id, replyText, channelId, phone);
      setReplyText('');
      // Reload messages
      await loadMessages(activeConv.id);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleTakeover() {
    if (!activeConv) return;
    try {
      const res = await fetchTakeover(activeConv.id);
      if (res && res.status === 'ok') {
        // Toggle conversation mode locally
        setActiveConv(prev => ({ ...prev, mode: 'human' }));
        loadConversations();
      }
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="glass-panel overflow-hidden grid grid-cols-1 md:grid-cols-3 h-[600px]">
      {/* Sidebar List */}
      <div className="border-r border-card-border flex flex-col h-full bg-card/20">
        <div className="p-4 border-b border-card-border flex items-center justify-between">
          <h3 className="font-semibold text-sm flex items-center">
            <MessageSquare className="w-4 h-4 mr-2 text-primary" />
            {t('wa-conv-title')}
          </h3>
          <button onClick={loadConversations} className="text-text-muted hover:text-text">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-card-border/40">
          {conversations.length > 0 ? (
            conversations.map((c) => (
              <div 
                key={c.id} 
                onClick={() => setActiveConv(c)}
                className={`p-4 cursor-pointer transition-colors flex flex-col space-y-1.5 ${
                  activeConv && activeConv.id === c.id 
                    ? 'bg-primary/10 border-l-2 border-primary' 
                    : 'hover:bg-card-border/20'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-text truncate">
                    {c.contacts?.name || c.contacts?.phone || 'Unknown Client'}
                  </span>
                  <span className="text-[10px] text-text-muted">
                    {c.updated_at ? c.updated_at.split('T')[1]?.slice(0, 5) : ''}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-text-muted truncate max-w-[150px]">
                    {c.contacts?.phone}
                  </span>
                  <div className="flex items-center space-x-1.5">
                    {c.mode === 'ai' ? (
                      <span className="px-1.5 py-0.5 rounded bg-accent-teal/10 text-accent-teal font-medium flex items-center">
                        <Bot className="w-2.5 h-2.5 mr-0.5" /> AI
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded bg-accent-purple/10 text-accent-purple font-medium flex items-center">
                        <User className="w-2.5 h-2.5 mr-0.5" /> Staff
                      </span>
                    )}
                    <span className={`w-1.5 h-1.5 rounded-full ${c.status === 'open' ? 'bg-accent-green' : 'bg-text-dark'}`} />
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-text-muted py-24">
              No conversations active.
            </div>
          )}
        </div>
      </div>

      {/* Message Area */}
      <div className="md:col-span-2 flex flex-col h-full bg-card/5">
        {activeConv ? (
          <>
            {/* Header info */}
            <div className="p-4 border-b border-card-border flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-sm">
                  {activeConv.contacts?.name || activeConv.contacts?.phone || 'WhatsApp Client'}
                </h4>
                <p className="text-xs text-text-muted">Status: {activeConv.status} | Mode: {activeConv.mode.toUpperCase()}</p>
              </div>

              {activeConv.mode === 'ai' && (
                <button 
                  onClick={handleTakeover}
                  className="flex items-center text-[10px] font-semibold text-accent-purple bg-accent-purple/10 border border-accent-purple/20 hover:bg-accent-purple/20 px-3 py-1.5 rounded transition-all"
                >
                  <UserCheck className="w-3.5 h-3.5 mr-1" />
                  {t('wa-takeover')}
                </button>
              )}
            </div>

            {/* Thread scroll */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length > 0 ? (
                messages.map((m) => {
                  const isOut = m.direction === 'outbound';
                  return (
                    <div 
                      key={m.id} 
                      className={`flex ${isOut ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-[75%] rounded-lg p-3 text-xs space-y-1 ${
                        isOut 
                          ? m.sender === 'ai' 
                            ? 'bg-primary/20 border border-primary/20 text-text' 
                            : 'bg-card border border-card-border text-text' 
                          : 'bg-card-border/30 text-text'
                      }`}>
                        <div className="flex items-center space-x-1.5 text-[10px] text-text-muted mb-0.5">
                          {m.sender === 'ai' && <Bot className="w-3 h-3 text-primary-hover" />}
                          {m.sender === 'staff' && <User className="w-3 h-3 text-accent-teal" />}
                          <span className="capitalize font-semibold">{m.sender}</span>
                          <span>•</span>
                          <span>{m.created_at ? m.created_at.split('T')[1]?.slice(0, 5) : ''}</span>
                        </div>
                        <p className="leading-relaxed whitespace-pre-wrap">{m.body}</p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-text-muted py-24">
                  No messages in thread.
                </div>
              )}
              <div ref={threadEndRef} />
            </div>

            {/* Input form */}
            <div className="p-4 border-t border-card-border bg-card/20 flex items-center space-x-2">
              <textarea 
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                disabled={loading}
                rows={1}
                placeholder={t('wa-reply-placeholder')}
                className="flex-1 resize-none bg-background/50 border border-card-border focus:border-primary/50 outline-none rounded-lg p-2.5 text-xs text-text transition-colors"
              />
              <button 
                onClick={handleSend}
                disabled={loading || !replyText.trim()}
                className="p-2.5 rounded-lg bg-primary hover:bg-primary-hover text-white disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-text-muted py-24 space-y-2">
            <MessageSquare className="w-12 h-12 text-card-border" />
            <p className="text-xs">{t('wa-select-conv')}</p>
          </div>
        )}
      </div>
    </div>
  );
}
