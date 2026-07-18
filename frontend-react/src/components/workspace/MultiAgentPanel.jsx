import React from 'react';
import { Bot, Loader2, Check, X, AlertCircle } from 'lucide-react';

/**
 * MultiAgentPanel — left-rail panel showing the active agent workforce.
 *
 * Each agent has a status row (idle / running / done / failed) that
 * updates live as the backend emits agent_start / agent_done events.
 * Phase 1 uses a fixed agent roster; Phase 3 can pull a dynamic
 * roster from the ToolRegistry.
 */
const AGENT_ROSTER = [
  { key: 'CLAUDIA', name: 'Claudia', role: 'Ketua Turus' },
  { key: 'PLANNER', name: 'Planner', role: 'Perancang' },
  { key: 'MAYA', name: 'Maya', role: 'Jualan & CRM' },
  { key: 'HAKIM', name: 'Hakim', role: 'Arkitek Sistem' },
  { key: 'ZARA', name: 'Zara', role: 'Kewangan' },
  { key: 'DANISH', name: 'Danish', role: 'Kreatif' },
  { key: 'AIMAN', name: 'Aiman', role: 'Pemasaran' },
  { key: 'AMELIA', name: 'Amelia', role: 'Latihan' },
  { key: 'ADILA', name: 'Adila', role: 'Operasi' },
  { key: 'NEXUS', name: 'Nexus', role: 'Generalist' },
];

const STATUS_STYLE = {
  idle: { dot: 'bg-text-faint', icon: null, label: 'Idle' },
  running: { dot: 'bg-accent-warning animate-pulse', icon: Loader2, label: 'Running' },
  done: { dot: 'bg-accent-success', icon: Check, label: 'Done' },
  failed: { dot: 'bg-accent-danger', icon: AlertCircle, label: 'Failed' },
};

export default function MultiAgentPanel({ agents = {} }) {
  return (
    <aside className="border-r border-border bg-surface/50 flex flex-col w-64 min-w-[16rem]">
      <div className="px-3 py-2 border-b border-border flex items-center gap-1.5">
        <Bot className="w-3.5 h-3.5 text-primary" />
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
          Agent Workforce
        </h3>
      </div>
      <ul className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {AGENT_ROSTER.map((a) => {
          const status = agents[a.key]?.status || 'idle';
          const style = STATUS_STYLE[status] || STATUS_STYLE.idle;
          const Icon = style.icon;
          return (
            <li
              key={a.key}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-md transition-colors ${
                status === 'running' ? 'bg-accent-warning/5' : 'hover:bg-surface-raised'
              }`}
              data-status={status}
            >
              <span className={`w-2 h-2 rounded-full ${style.dot}`} aria-label={style.label} />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">{a.name}</div>
                <div className="text-[10px] text-text-muted truncate">{a.role}</div>
              </div>
              {Icon && (
                <Icon
                  className={`w-3.5 h-3.5 ${
                    status === 'running'
                      ? 'text-accent-warning animate-spin'
                      : status === 'failed'
                      ? 'text-accent-danger'
                      : 'text-accent-success'
                  }`}
                />
              )}
            </li>
          );
        })}
      </ul>
      <div className="px-3 py-2 border-t border-border text-[10px] text-text-faint">
        Status kemas kini secara langsung.
      </div>
    </aside>
  );
}
