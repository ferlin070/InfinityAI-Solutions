import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Check, X, Loader2, Image as ImageIcon, FileJson } from 'lucide-react';

/**
 * ToolExecutionCard — one card per tool invocation. Shows tool name,
 * agent, status, args (collapsible), result (collapsible), duration.
 * If the result contains base64 image data, renders it inline.
 */
function formatMs(ms) {
  if (!ms || ms < 0) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function tryPrettyJson(value) {
  if (value == null) return null;
  if (typeof value === 'object') return value;
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null;
  try { return JSON.parse(trimmed); } catch { return null; }
}

export default function ToolExecutionCard({ step }) {
  const [openArgs, setOpenArgs] = useState(false);
  const [openResult, setOpenResult] = useState(true);
  const obs = step?.observation;
  const args = obs?.arguments || {};
  const result = obs?.result || '';
  const resultJson = tryPrettyJson(result);
  const isImage = resultJson?.type === 'image' && resultJson?.data_base64;
  const isImageGen = (step?.tool?.tool || '').toLowerCase().includes('image_generation');

  const status = step?.status || 'running';
  const isRunning = status === 'running';
  const isFailed = status === 'failed' || obs?.success === false;
  const duration = step?.finishedAt && step?.startedAt
    ? step.finishedAt - step.startedAt
    : null;

  return (
    <div
      className={`border rounded-lg overflow-hidden bg-surface-raised/60 ${
        isFailed ? 'border-accent-danger/30' : 'border-border'
      }`}
      data-testid="tool-execution-card"
    >
      <div className="flex items-center gap-2 px-3 py-2">
        {isRunning ? (
          <Loader2 className="w-3.5 h-3.5 text-accent-warning animate-spin" />
        ) : isFailed ? (
          <X className="w-3.5 h-3.5 text-accent-danger" />
        ) : (
          <Check className="w-3.5 h-3.5 text-accent-success" />
        )}
        <span className="text-xs font-mono font-medium">
          {step?.tool?.agent || '?'} <span className="text-text-faint">→</span> {step?.tool?.tool || '?'}
        </span>
        {duration != null && (
          <span className="text-[10px] text-text-faint ml-auto font-mono">
            {formatMs(duration)}
          </span>
        )}
      </div>

      {/* Image-generation result rendered inline */}
      {isImage && (
        <div className="px-3 pb-3">
          <img
            src={`data:${resultJson.mime_type || 'image/png'};base64,${resultJson.data_base64}`}
            alt={resultJson.caption || 'Generated image'}
            className="rounded border border-border max-w-full"
          />
          {resultJson.caption && (
            <div className="text-[10px] text-text-muted mt-1">{resultJson.caption}</div>
          )}
        </div>
      )}
      {/* Image Generation tool that didn't return structured image data */}
      {!isImage && isImageGen && result && (
        <div className="px-3 pb-2 text-[10px] text-text-muted italic">
          <ImageIcon className="w-3 h-3 inline mr-1" /> imej dijana — sedia untuk dimuat turun
        </div>
      )}

      {/* Args (collapsible) */}
      {Object.keys(args).length > 0 && (
        <div className="border-t border-border">
          <button
            type="button"
            onClick={() => setOpenArgs((v) => !v)}
            className="w-full flex items-center gap-1.5 px-3 py-1.5 text-[10px] text-text-muted hover:bg-surface"
          >
            {openArgs ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            Args ({Object.keys(args).length})
          </button>
          {openArgs && (
            <pre className="text-[10px] font-mono text-text-muted bg-surface/40 px-3 py-2 overflow-x-auto max-h-40">
              {JSON.stringify(args, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Result (collapsible) */}
      {result && (
        <div className="border-t border-border">
          <button
            type="button"
            onClick={() => setOpenResult((v) => !v)}
            className="w-full flex items-center gap-1.5 px-3 py-1.5 text-[10px] text-text-muted hover:bg-surface"
          >
            {openResult ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {resultJson ? (
              <><FileJson className="w-3 h-3" /> Result (JSON)</>
            ) : (
              <>Result</>
            )}
            <span className="text-text-faint">({result.length} chars)</span>
          </button>
          {openResult && (
            resultJson ? (
              <pre className="text-[10px] font-mono text-text-muted bg-surface/40 px-3 py-2 overflow-x-auto max-h-60">
                {JSON.stringify(resultJson, null, 2)}
              </pre>
            ) : (
              <pre className="text-[10px] font-mono text-text-muted bg-surface/40 px-3 py-2 overflow-x-auto max-h-40 whitespace-pre-wrap">
                {result}
              </pre>
            )
          )}
        </div>
      )}
    </div>
  );
}
