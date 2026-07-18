import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, Loader2, ShieldAlert, Brain, RefreshCw, ImageOff, Image as ImageIcon, ChevronDown, ChevronRight, ListChecks, GitBranch } from 'lucide-react';
import ToolExecutionCard from './ToolExecutionCard.jsx';

/**
 * AgentTimeline — the heart of the Agent Workspace. Renders an
 * ordered list of timeline steps, each representing a planning /
 * execution / verification action by the agent team.
 *
 * Step kinds (mapped from backend events):
 *   plan        → PlanStep
 *   subtask     → SubTaskStep (contains child tool steps)
 *   tool        → ToolExecutionCard
 *   validation  → ValidationStep
 *   reflection  → ReflectionStep
 *   approval    → ApprovalCard
 *   tool_retry / tool_fallback → InfoStep
 *   (other)     → GenericStep
 */
const STEP_STATUS_STYLE = {
  running: { icon: Loader2, color: 'text-accent-warning', spin: true, label: 'Running' },
  done: { icon: CheckCircle2, color: 'text-accent-success', label: 'Done' },
  success: { icon: CheckCircle2, color: 'text-accent-success', label: 'Done' },
  failed: { icon: AlertTriangle, color: 'text-accent-danger', label: 'Failed' },
  info: { icon: RefreshCw, color: 'text-text-muted', label: 'Info' },
  awaiting: { icon: ShieldAlert, color: 'text-accent-warning', label: 'Awaiting approval' },
};

function StepHeader({ icon: Icon, color, label, title, subtitle, durationMs }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2">
      <Icon className={`w-4 h-4 mt-0.5 ${color} ${STEP_STATUS_STYLE[label?.toLowerCase()]?.spin ? 'animate-spin' : ''}`} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium leading-snug">{title}</div>
        {subtitle && <div className="text-[10px] text-text-muted leading-snug mt-0.5">{subtitle}</div>}
      </div>
      {durationMs != null && (
        <div className="text-[10px] text-text-faint font-mono">{durationMs < 1000 ? `${durationMs}ms` : `${(durationMs/1000).toFixed(2)}s`}</div>
      )}
    </div>
  );
}

function PlanStep({ step }) {
  const plan = step.details || {};
  const subtasks = plan.subtasks || [];
  return (
    <div className="border border-border rounded-lg bg-primary-subtle/30">
      <StepHeader
        icon={ListChecks}
        color="text-primary"
        label="done"
        title={plan.intent || step.title || 'Pelan tindakan'}
        subtitle={`Complexity: ${plan.complexity || 'simple'} · ${subtasks.length} subtask(s)`}
      />
      {subtasks.length > 0 && (
        <div className="px-3 pb-2 pl-9 space-y-1">
          {subtasks.map((st, i) => (
            <div key={st.id || i} className="text-[10px] text-text-muted flex items-start gap-1.5">
              <GitBranch className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="font-mono text-text-faint">{st.id}:</span>{' '}
                <span className="text-text">{st.agent_key}</span> —{' '}
                <span className="truncate">{st.description}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SubTaskStep({ step, children }) {
  const a = step.agent || step.subtitle || '?';
  return (
    <div className="border border-border rounded-lg bg-surface-raised/40">
      <StepHeader
        icon={STEP_STATUS_STYLE[step.status]?.icon || Loader2}
        color={STEP_STATUS_STYLE[step.status]?.color || 'text-text-muted'}
        label={step.status}
        title={`${a}: ${step.title || ''}`}
        subtitle={step.resultText ? step.resultText.slice(0, 200) : ''}
        durationMs={step.finishedAt && step.startedAt ? step.finishedAt - step.startedAt : null}
      />
      {step.artifacts && step.artifacts.length > 0 && (
        <div className="px-3 pb-2 pl-9 flex flex-wrap gap-1.5">
          {step.artifacts.map((a, i) => (
            a.type === 'image' && a.data_base64 ? (
              <img
                key={i}
                src={`data:${a.mime_type || 'image/png'};base64,${a.data_base64}`}
                alt={a.caption || 'Imej dijana'}
                className="rounded border border-border max-h-32"
              />
            ) : (
              <span key={i} className="text-[10px] text-text-muted flex items-center gap-1">
                <ImageOff className="w-3 h-3" /> Gagal papar
              </span>
            )
          ))}
        </div>
      )}
      {children && <div className="px-3 pb-2 pl-9 space-y-1.5">{children}</div>}
    </div>
  );
}

function ValidationStep({ step }) {
  const passed = step.status === 'done';
  return (
    <div className={`border rounded-lg ${passed ? 'border-accent-success/30 bg-accent-success/5' : 'border-accent-danger/30 bg-accent-danger/5'}`}>
      <StepHeader
        icon={passed ? CheckCircle2 : AlertTriangle}
        color={passed ? 'text-accent-success' : 'text-accent-danger'}
        label={step.status}
        title={step.title}
        subtitle={step.subtitle}
      />
    </div>
  );
}

function ReflectionStep({ step }) {
  return (
    <div className="border border-border rounded-lg bg-surface-raised/40">
      <StepHeader
        icon={Brain}
        color="text-text-muted"
        label="info"
        title={step.title}
        subtitle={step.subtitle}
      />
    </div>
  );
}

function ApprovalStep({ step, onApprove, onReject }) {
  const details = step.details || {};
  return (
    <div className="border-2 border-accent-warning/40 rounded-lg bg-accent-warning/5">
      <div className="flex items-center gap-2 px-3 py-2">
        <ShieldAlert className="w-4 h-4 text-accent-warning" />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold">Memerlukan kelulusan manusia</div>
          <div className="text-[10px] text-text-muted mt-0.5">
            Tool: <span className="font-mono">{details.tool || step.subtitle}</span>
          </div>
        </div>
      </div>
      <div className="px-3 pb-3 flex gap-2">
        <button
          type="button"
          onClick={() => onApprove?.(details)}
          className="text-xs px-3 py-1.5 rounded-md bg-accent-success text-white hover:opacity-90"
        >
          Approve
        </button>
        <button
          type="button"
          onClick={() => onReject?.(details)}
          className="text-xs px-3 py-1.5 rounded-md bg-surface border border-border text-text hover:border-border-strong"
        >
          Reject
        </button>
      </div>
    </div>
  );
}

function GenericStep({ step }) {
  return (
    <div className="border border-border rounded-lg bg-surface-raised/30">
      <StepHeader
        icon={STEP_STATUS_STYLE[step.status]?.icon || RefreshCw}
        color={STEP_STATUS_STYLE[step.status]?.color || 'text-text-muted'}
        label={step.status}
        title={step.title}
        subtitle={step.subtitle}
      />
    </div>
  );
}

export default function AgentTimeline({ steps = [] }) {
  if (!steps.length) {
    return (
      <div className="text-[11px] text-text-muted text-center py-12">
        Pelan tindakan akan dipaparkan di sini selepas Claudia menganalisis permintaan.
      </div>
    );
  }
  // Group consecutive tool steps under their parent subtask step for
  // visual hierarchy. A subtask step immediately followed by tool
  // steps is the parent; we attach the children to the most recent
  // subtask.
  const groups = [];
  let current = null;
  for (const s of steps) {
    if (s.kind === 'subtask') {
      if (current) groups.push(current);
      current = { subtask: s, tools: [] };
    } else if (s.kind === 'tool' && current) {
      current.tools.push(s);
    } else {
      if (current) groups.push(current);
      current = null;
      groups.push({ standalone: s });
    }
  }
  if (current) groups.push(current);

  return (
    <div className="space-y-1.5" data-testid="agent-timeline">
      {groups.map((g, i) => {
        if (g.standalone) {
          const s = g.standalone;
          return (
            <div key={s.id || i}>
              {s.kind === 'plan' && <PlanStep step={s} />}
              {s.kind === 'validation' && <ValidationStep step={s} />}
              {s.kind === 'reflection' && <ReflectionStep step={s} />}
              {s.kind === 'approval' && <ApprovalStep step={s} />}
              {s.kind === 'tool_retry' && <GenericStep step={s} />}
              {s.kind === 'tool_fallback' && <GenericStep step={s} />}
              {!['plan', 'validation', 'reflection', 'approval', 'tool_retry', 'tool_fallback'].includes(s.kind) && (
                <GenericStep step={s} />
              )}
            </div>
          );
        }
        return (
          <SubTaskStep key={g.subtask.id || i} step={g.subtask}>
            {g.tools.map((t, j) => (
              <ToolExecutionCard key={t.id || j} step={t} />
            ))}
          </SubTaskStep>
        );
      })}
    </div>
  );
}
