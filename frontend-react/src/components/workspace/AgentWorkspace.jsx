import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Square, RefreshCw, Trash2, Bot, User, Clock, Zap } from 'lucide-react';
import WorkspaceHeader from './WorkspaceHeader.jsx';
import MultiAgentPanel from './MultiAgentPanel.jsx';
import AgentTimeline from './AgentTimeline.jsx';
import { useAgentStream } from '../../hooks/useAgentStream.js';
import { streamChatFactory } from '../../utils/streamChat.js';

/**
 * AgentWorkspace — the main Agent Workspace container.
 *
 * Replaces the chat-panel-only `WorkOrder` UI with a tri-pane layout:
 *   [ WorkspaceHeader ]
 *   [ MultiAgentPanel | Main: AgentTimeline + MessageInput        ]
 *   [                | StatusBar (elapsed, status text)            ]
 *
 * Phase 1: the workspace reads from the existing /api/chat/stream SSE
 * endpoint and renders the rich event types we now emit. The API URL
 * is supplied via prop (api.js sets it up) so the same component can
 * be used in tests.
 */
const DEFAULT_STREAM_URL = '/api/chat/stream';

export default function AgentWorkspace({
  api,                  // { streamChat } injected so tests can stub
  context = {},
  initialHistory = [],
  onHistoryChange,
}) {
  const [prompt, setPrompt] = useState('');
  const [history, setHistory] = useState(initialHistory);
  const streamFactory = useRef(streamChatFactory({
    url: DEFAULT_STREAM_URL,
    getSessionToken: () => {
      // Cookies travel automatically via credentials:'include'.
      // No token to pass.
      return null;
    },
  })).current;

  // Use a wrapper so tests can pass a stub.
  const factory = api?.streamChat ? (prompt, model, onEvent) => api.streamChat(prompt, model, onEvent) : streamFactory;

  const { state, run } = useAgentStream(factory);

  const handleSend = async () => {
    const p = prompt.trim();
    if (!p || !state.finished === false) return; // allow re-send after finish
    setPrompt('');
    const newHistory = [...history, { role: 'user', content: p }];
    setHistory(newHistory);
    onHistoryChange?.(newHistory);
    await run(p, 'gpt-4o-mini');
  };

  const handleClear = () => {
    setHistory([]);
    onHistoryChange?.([]);
  };

  const elapsed = formatElapsed(state.elapsedMs);
  const statusText = state.statusText || (state.finished ? 'Selesai' : 'Menunggu arahan...');

  return (
    <div className="flex flex-col h-[78vh] bg-surface rounded-xl border border-border overflow-hidden" data-testid="agent-workspace">
      <WorkspaceHeader context={context} />

      <div className="flex flex-1 min-h-0">
        <MultiAgentPanel agents={state.agents} />

        <main className="flex-1 flex flex-col min-w-0">
          {/* Scrollable timeline */}
          <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
            {state.steps.length === 0 && state.messages.length === 0 ? (
              <div className="text-[11px] text-text-muted text-center py-12">
                Hantar arahan untuk mula. Claude akan rancang, ejen akan jalankan, anda nampak setiap langkah.
              </div>
            ) : (
              <>
                <AgentTimeline steps={state.steps} />
                {state.messages.map((m) => (
                  <article key={m.id} className="border border-border rounded-lg bg-surface-raised/40 p-3">
                    <div className="flex items-center gap-1.5 text-[10px] text-text-muted mb-1">
                      <Bot className="w-3 h-3 text-primary" />
                      <span className="font-semibold">Claudia</span>
                      <span>·</span>
                      <span className="font-mono">{new Date(m.timestamp).toLocaleTimeString()}</span>
                    </div>
                    {m.kind === 'results' && m.results && m.results.length > 0 ? (
                      <div className="space-y-2">
                        {m.results.map((r, i) => (
                          <div key={i} className="border border-border rounded-md p-2">
                            <div className="flex items-center gap-1.5 text-[10px] text-text-muted mb-1">
                              <Bot className="w-3 h-3 text-primary" />
                              <span className="font-semibold">{r.agent}</span>
                              <span>·</span>
                              <span className="font-mono">{r.speed}</span>
                            </div>
                            <p className="text-xs whitespace-pre-wrap font-mono leading-relaxed">{r.result}</p>
                            {(r.artifacts || []).map((a, j) => (
                              a.type === 'image' && a.data_base64 ? (
                                <img
                                  key={j}
                                  src={`data:${a.mime_type || 'image/png'};base64,${a.data_base64}`}
                                  alt={a.caption || 'image'}
                                  className="rounded border border-border max-w-full mt-2"
                                />
                              ) : null
                            ))}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs whitespace-pre-wrap leading-relaxed">{m.message}</p>
                    )}
                  </article>
                ))}
              </>
            )}
            {state.error && (
              <div className="border-2 border-accent-danger/40 rounded-lg bg-accent-danger/5 p-3">
                <div className="text-xs font-semibold text-accent-danger">Ralat</div>
                <div className="text-[11px] text-text-muted mt-1">{state.error}</div>
                <button
                  type="button"
                  onClick={handleSend}
                  className="mt-2 text-[11px] px-2 py-1 rounded-md bg-accent-warning text-white"
                >
                  Cuba semula
                </button>
              </div>
            )}
          </div>

          {/* Status bar */}
          <div className="border-t border-border bg-surface-raised/40 px-3 py-1.5 flex items-center gap-2 text-[10px] text-text-muted">
            <span className="flex items-center gap-1">
              {state.finished ? <Zap className="w-3 h-3 text-accent-success" /> : <Loader2 className="w-3 h-3 animate-spin text-accent-warning" />}
              {statusText}
            </span>
            <span className="text-text-faint">·</span>
            <span className="flex items-center gap-1 font-mono"><Clock className="w-3 h-3" /> {elapsed}</span>
            <span className="text-text-faint">·</span>
            <span>{state.steps.length} langkah</span>
            <span className="text-text-faint">·</span>
            <span>{Object.keys(state.agents).filter((k) => state.agents[k].status !== 'idle').length} ejen aktif</span>
            <button
              type="button"
              onClick={handleClear}
              title="Kosongkan perbualan"
              className="ml-auto text-text-muted hover:text-accent-danger"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Input */}
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="border-t border-border bg-surface-raised/40 px-3 py-2.5 flex items-end gap-2"
          >
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Hantar arahan kepada Claudia..."
              rows={2}
              className="flex-1 resize-none text-xs px-3 py-2 rounded-md bg-surface border border-border focus:outline-none focus:border-primary"
              data-testid="prompt-input"
            />
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="text-xs px-3 py-2 rounded-md bg-primary text-primary-foreground disabled:opacity-50 flex items-center gap-1.5"
              data-testid="send-button"
            >
              <Send className="w-3.5 h-3.5" />
              Hantar
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

function formatElapsed(ms) {
  if (!ms) return '0s';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms/1000).toFixed(1)}s`;
  return `${Math.floor(ms/60000)}m ${Math.floor((ms%60000)/1000)}s`;
}
