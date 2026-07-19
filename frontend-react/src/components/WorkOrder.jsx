import React, { useState, useEffect } from 'react';
import AgentWorkspace from './workspace/AgentWorkspace.jsx';
import { fetchChatHistory, clearChat } from '../api';

/**
 * WorkOrder — the Arahan Kerja page.
 *
 * Phase 1 (agentic-v3 / agent-workspace-ui): the live execution UI
 * lives in `AgentWorkspace`, which handles the SSE stream, the rich
 * timeline, and the agent sidebar. This component just hydrates from
 * `/api/chat/history` for the initial message list and provides the
 * "clear history" action.
 */

function uid() {
  return (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
}

export default function WorkOrder({ t }) {
  const [messages, setMessages] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

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

  async function handleStream(prompt, model, onEvent, opts) {
    // Lazy import so the bundle stays small if WorkOrder isn't used.
    const { streamChat } = await import('../api');
    await streamChat(prompt, model, onEvent, opts);
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
    <AgentWorkspace
      api={{ streamChat: handleStream }}
      context={{ module: 'Arahan Kerja' }}
      initialHistory={messages}
      onHistoryChange={() => { /* AgentWorkspace manages its own in-memory history */ }}
    />
  );
}
