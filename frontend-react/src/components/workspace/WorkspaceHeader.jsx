import React from 'react';
import { Building2, Database, FileText, Globe, ChevronDown } from 'lucide-react';

/**
 * WorkspaceHeader — top bar of the Agent Workspace.
 *
 * Surfaces the user's current operating context: org, project, DB,
 * current module / page. In Phase 1 these are static placeholders read
 * from env (VITE_*). Phase 3 adds a real org / project switcher and
 * live DB / browser context.
 */
export default function WorkspaceHeader({ context = {} }) {
  const {
    org = 'InfinityAI Solutions',
    project = 'AI Command Center',
    database = import.meta.env?.VITE_DATABASE_LABEL || 'demo',
    module = context.module || 'Arahan Kerja',
    browserPage = context.browserPage || null,
  } = context;

  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-30">
      <div className="flex items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-md bg-primary-subtle flex items-center justify-center text-primary font-bold text-sm">
            IA
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold truncate">{org}</div>
            <div className="text-[10px] text-text-muted truncate flex items-center gap-1">
              <span>{project}</span>
              <span className="text-text-faint">·</span>
              <span className="flex items-center gap-1">
                <FileText className="w-3 h-3" /> {module}
              </span>
              {browserPage && (
                <>
                  <span className="text-text-faint">·</span>
                  <span className="flex items-center gap-1">
                    <Globe className="w-3 h-3" /> {browserPage}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[10px] text-text-muted">
          <span className="flex items-center gap-1 px-2 py-1 rounded-md bg-surface-raised border border-border">
            <Database className="w-3 h-3" /> {database}
          </span>
          <span className="flex items-center gap-1 px-2 py-1 rounded-md bg-surface-raised border border-border">
            <Building2 className="w-3 h-3" /> {org}
          </span>
          <button
            type="button"
            title="Tukar workspace (Phase 3)"
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-surface-raised border border-border hover:border-border-strong"
          >
            <ChevronDown className="w-3 h-3" />
          </button>
        </div>
      </div>
    </header>
  );
}
