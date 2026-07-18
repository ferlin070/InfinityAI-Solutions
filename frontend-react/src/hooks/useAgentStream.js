import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * useAgentStream — SSE consumer hook for the Agent Workspace.
 *
 * The backend (api/routes.py /api/chat/stream) emits Server-Sent
 * Events. We parse them into a state machine the workspace components
 * subscribe to. Each event becomes either a `timelineStep` (visible in
 * the AgentTimeline) or a `subtaskUpdate` (mutates an existing step).
 *
 * Event types (see docs/architecture/agent-workspace-ui.md):
 *   status             → transient banner text
 *   plan               → opening timeline step
 *   subtask_start      → new subtask step
 *   subtask_done       → complete the subtask step
 *   agent_start/done   → multi-agent sidebar row state
 *   tool_call (start/done) → tool execution card state
 *   observation        → tool result (with arguments + result)
 *   final              → append a final assistant message
 *   error              → append an error step
 */

export function emptyState() {
  return {
    statusText: '',
    plan: null,                    // { intent, complexity, subtasks[] }
    steps: [],                     // ordered timeline steps
    agents: {},                    // { agent_key: { status, ... } }
    tools: {},                     // { tool_call_id: { name, status, arguments, result, ... } }
    messages: [],                  // final assistant messages
    error: null,
    pendingApproval: null,         // { tool, arguments, ... } awaiting user
    elapsedMs: 0,
    finished: false,
  };
}

export function useAgentStream(streamFactory, { onDone, onError } = {}) {
  const [state, setState] = useState(emptyState);
  const stateRef = useRef(state);
  stateRef.current = state;
  const startedAtRef = useRef(null);

  const appendStep = useCallback((step) => {
    setState((s) => ({ ...s, steps: [...s.steps, step] }));
  }, []);

  const updateLastStep = useCallback((patch) => {
    setState((s) => {
      if (s.steps.length === 0) return s;
      const next = s.steps.slice();
      next[next.length - 1] = { ...next[next.length - 1], ...patch };
      return { ...s, steps: next };
    });
  }, []);

  const updateStepById = useCallback((id, patch) => {
    setState((s) => ({
      ...s,
      steps: s.steps.map((step) => (step.id === id ? { ...step, ...patch } : step)),
    }));
  }, []);

  const handleEvent = useCallback(
    (eventType, payload) => {
      switch (eventType) {
        case 'status':
          setState((s) => ({ ...s, statusText: payload?.text || '' }));
          break;

        case 'plan':
          setState((s) => ({ ...s, plan: payload }));
          appendStep({
            id: `plan-${Date.now()}`,
            kind: 'plan',
            status: 'done',
            title: payload?.intent || 'Pelan tindakan',
            subtitle: payload?.complexity || 'simple',
            details: payload,
            startedAt: Date.now(),
            finishedAt: Date.now(),
          });
          break;

        case 'subtask_start':
          appendStep({
            id: payload?.subtask_id || `sub-${Date.now()}`,
            kind: 'subtask',
            status: 'running',
            title: payload?.description || 'Menjalankan tugasan',
            subtitle: payload?.agent_key || '',
            agent: payload?.agent_key,
            details: payload,
            startedAt: Date.now(),
          });
          setState((s) => ({
            ...s,
            agents: {
              ...s.agents,
              [payload?.agent_key]: { status: 'running', stepId: payload?.subtask_id },
            },
          }));
          break;

        case 'subtask_done':
          updateStepById(payload?.subtask_id, {
            status: payload?.status === 'success' ? 'done' : payload?.status,
            details: { ...payload },
            resultText: payload?.result_text || '',
            artifacts: payload?.artifacts || [],
            speed: payload?.speed,
            finishedAt: Date.now(),
          });
          setState((s) => ({
            ...s,
            agents: {
              ...s.agents,
              [payload?.agent_key]: { status: payload?.status || 'done' },
            },
          }));
          break;

        case 'agent_start':
          setState((s) => ({
            ...s,
            agents: {
              ...s.agents,
              [payload?.agent]: { ...(s.agents[payload?.agent] || {}), status: 'running' },
            },
          }));
          break;

        case 'agent_done':
          setState((s) => ({
            ...s,
            agents: {
              ...s.agents,
              [payload?.agent]: { ...(s.agents[payload?.agent] || {}), status: 'done' },
            },
          }));
          break;

        case 'tool_call': {
          const toolId = `${payload?.agent || '?'}::${payload?.tool}::${Date.now()}`;
          setState((s) => ({
            ...s,
            tools: {
              ...s.tools,
              [toolId]: {
                id: toolId,
                agent: payload?.agent,
                name: payload?.tool,
                status: payload?.status, // 'start' | 'done'
                startedAt: payload?.status === 'start' ? Date.now() : undefined,
                finishedAt: payload?.status === 'done' ? Date.now() : undefined,
              },
            },
          }));
          // Attach a tool step to the latest subtask.
          if (payload?.status === 'start') {
            appendStep({
              id: `tool-${toolId}`,
              kind: 'tool',
              status: 'running',
              title: `${payload?.agent} → ${payload?.tool}`,
              subtitle: 'Menjalankan...',
              tool: { id: toolId, ...payload },
              startedAt: Date.now(),
            });
          } else if (payload?.status === 'done') {
            // Mark the last 'running' tool step with this tool as done
            setState((s) => {
              const next = s.steps.slice();
              for (let i = next.length - 1; i >= 0; i--) {
                if (next[i].kind === 'tool' && next[i].tool?.tool === payload?.tool
                    && next[i].tool?.agent === payload?.agent
                    && next[i].status === 'running') {
                  next[i] = { ...next[i], status: 'done', finishedAt: Date.now() };
                  break;
                }
              }
              return { ...s, steps: next };
            });
          }
          break;
        }

        case 'observation': {
          // Attach the actual result to the most recent tool step for
          // this (agent, tool) pair that's still 'running'.
          setState((s) => {
            const next = s.steps.slice();
            for (let i = next.length - 1; i >= 0; i--) {
              if (next[i].kind === 'tool' && next[i].tool?.tool === payload?.tool
                  && next[i].tool?.agent === payload?.agent
                  && !next[i].observation) {
                next[i] = {
                  ...next[i],
                  observation: payload,
                  subtitle: payload?.success ? 'Selesai' : 'Ralat',
                };
                break;
              }
            }
            return { ...s, steps: next };
          });
          break;
        }

        case 'tool_retry':
        case 'tool_fallback':
          appendStep({
            id: `${eventType}-${Date.now()}`,
            kind: eventType,
            status: 'info',
            title: eventType === 'tool_retry' ? 'Mencuba semula tool' : 'Beralih ke tool alternatif',
            subtitle: JSON.stringify(payload),
            details: payload,
            startedAt: Date.now(),
            finishedAt: Date.now(),
          });
          break;

        case 'validation':
          appendStep({
            id: `validation-${Date.now()}`,
            kind: 'validation',
            status: payload?.passed ? 'done' : 'failed',
            title: payload?.check || 'Validasi',
            subtitle: payload?.passed ? 'Lulus' : 'Gagal',
            details: payload,
            startedAt: Date.now(),
            finishedAt: Date.now(),
          });
          break;

        case 'reflection':
          appendStep({
            id: `reflection-${Date.now()}`,
            kind: 'reflection',
            status: 'info',
            title: `Refleksi: ${payload?.decision || '?'}`,
            subtitle: payload?.reasoning || '',
            details: payload,
            startedAt: Date.now(),
            finishedAt: Date.now(),
          });
          break;

        case 'approval_required':
          setState((s) => ({ ...s, pendingApproval: payload }));
          appendStep({
            id: `approval-${Date.now()}`,
            kind: 'approval',
            status: 'awaiting',
            title: 'Memerlukan kelulusan manusia',
            subtitle: payload?.tool || payload?.reason || 'Tindakan sensitif',
            details: payload,
            startedAt: Date.now(),
          });
          break;

        case 'final':
          setState((s) => ({
            ...s,
            messages: [
              ...s.messages,
              {
                id: `msg-${Date.now()}`,
                role: 'assistant',
                kind: payload?.status === 'success' ? 'results' : 'message',
                results: payload?.results || [],
                message: payload?.message || '',
                timestamp: Date.now(),
              },
            ],
            finished: true,
          }));
          break;

        case 'error':
          setState((s) => ({ ...s, error: payload?.message || 'Unknown error', finished: true }));
          break;

        default:
          // Unknown events are logged but ignored by the UI.
          break;
      }
    },
    [appendStep, updateStepById]
  );

  const run = useCallback(async (prompt, model) => {
    if (!streamFactory) return;
    setState(emptyState());
    startedAtRef.current = Date.now();

    let timer;
    const tick = () => {
      if (startedAtRef.current) {
        setState((s) => ({ ...s, elapsedMs: Date.now() - startedAtRef.current }));
      }
    };
    timer = setInterval(tick, 500);

    try {
      await streamFactory(prompt, model, handleEvent);
    } catch (e) {
      setState((s) => ({ ...s, error: e?.message || String(e), finished: true }));
      onError?.(e);
    } finally {
      clearInterval(timer);
      setState((s) => ({ ...s, finished: true }));
      onDone?.(stateRef.current);
    }
  }, [streamFactory, handleEvent, onDone, onError]);

  // Cleanup on unmount.
  useEffect(() => () => clearInterval(stateRef.current?.__timer), []);

  return { state, run };
}
