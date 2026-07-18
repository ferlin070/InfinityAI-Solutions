# Agent Workspace UI

> **Status:** PHASE 1 IN PROGRESS. Component skeleton + event backbone.
> Further phases add rich rendering, file management, image generation
> studio, etc.

## Vision

Replace the current chatbot-style `WorkOrder` chat panel with an
**enterprise Agent Workspace** — a layout that makes the user feel
like a supervisor of a team of AI employees, not a person texting a
chatbot. Every execution step is visible, every agent is named, every
tool result is inspectable, every destructive action is gated by
human approval.

## Current vs. target

| Capability | Current `WorkOrder.jsx` | Target Agent Workspace |
|---|---|---|
| Plan visibility | None — "Claudia is thinking…" | Full Plan shown as expandable step BEFORE execution |
| Tool execution | One line: "Maya sedang guna Product Pricing…" | Collapsible card with tool name, args, full result, duration, retry count |
| Multi-agent | Implicit (only the final agent's result is rendered) | Active-agents sidebar with real-time status per agent |
| Browser automation | No view | Page-by-page log + screenshot gallery + DOM extraction status |
| Approval | None | Destructive ops show an approval card with Approve/Reject/Modify |
| Structured output | Plain text only | Tables, code, JSON, charts, Kanban, tree (renderer dispatched by content type) |
| Long-running | One status line | Progress bar, elapsed time, cancel/pause/retry buttons |
| Error UX | "Sambungan terputus." | Specific error + retry + diagnostic info |
| Memory | Hidden | Memory panel: conversation / workspace / trace — view/edit/forget |
| Conversation features | None | Edit / retry / regenerate / bookmark / branch |
| Accessibility | Basic | Keyboard nav, screen reader, dark/light mode toggle |
| Workspace context | None | Top bar: org / project / DB / current module / active browser page |

## Component tree

```
AgentWorkspace                (main container, manages layout + state)
├── WorkspaceHeader          (org, project, DB, current module, agent switcher)
├── AgentSidebar             (left rail: active agents, history, memory)
│   ├── MultiAgentPanel      (one row per active agent with live status)
│   ├── MemoryPanel          (conversation / workspace / trace)
│   └── HistoryList          (past conversations)
├── MainPanel                (the chat + execution area)
│   ├── AgentTimeline        (scrollable timeline of every step this run)
│   │   ├── PlanStep         (intent, complexity, subtasks, success criteria)
│   │   ├── SubTaskStep      (agent + tool calls + result + duration)
│   │   │   ├── ToolExecutionCard   (args, result, expandable logs)
│   │   │   ├── BrowserAutomationView
│   │   │   └── StructuredOutput
│   │   ├── ValidationStep   (check + pass/fail + rationale)
│   │   ├── ReflectionStep   (enough? need more? retry?)
│   │   └── ApprovalStep     (awaiting human)
│   ├── MessageList          (user + final agent responses, rich content)
│   └── MessageInput         (textarea, attachments, slash commands)
└── StatusBar                (elapsed time, total cost, cancel button)
```

## Event mapping (SSE → component)

| Backend event (`on_event`) | UI component | Notes |
|---|---|---|
| `status` | StatusBar / step status text | Existing — keep |
| `agent_start` | MultiAgentPanel row → running; SubTaskStep header | |
| `agent_done` | MultiAgentPanel row → done; SubTaskStep done check | |
| `tool_call` (existing) | ToolExecutionCard state change | start / done |
| `tool_call.result` (new) | ToolExecutionCard body | full result + duration |
| `tool_retry` (new) | ToolExecutionCard badge | "Retry 1/2 in 0.5s" |
| `tool_fallback` (new) | ToolExecutionCard badge | "Fell back to X" |
| `plan` (new) | PlanStep in timeline | intent, complexity, subtasks |
| `subtask_start` (new) | SubTaskStep opens | |
| `observation` (new) | ToolExecutionCard body | every tool return |
| `validation` (new) | ValidationStep | pass/fail + rationale |
| `reflection` (new) | ReflectionStep | enough/need_more/retry |
| `approval_required` (new) | ApprovalStep | pauses until user responds |
| `final` | MessageList final assistant message | structured results |
| `error` | ErrorStep + retry button | specific error |

## Phase 1 (this delivery)

Component skeleton + event backbone + minimal rendering for the most
impactful elements:

- `AgentWorkspace` layout (header + sidebar + main + status)
- `WorkspaceHeader` (org / project / DB / current module)
- `AgentTimeline` with expandable steps
- `ToolExecutionCard` (tool name, args, result, duration, status)
- `MultiAgentPanel` (active agents with live status)
- `ApprovalCard` (Approve / Reject / Modify buttons — wired to a
  follow-up POST that resumes the flow)
- `StructuredOutput` (basic: text / code / JSON / table)
- Backend: emit `plan`, `subtask_start`, `subtask_done`, `observation`,
  `validation`, `approval_required`, `tool_retry`, `tool_fallback` events
- `useAgentStream` hook consumes the SSE stream into a state machine

## Phase 2 — Rich interaction

- Message editing / retry / regenerate / branch
- File upload + preview + version history
- Image generation studio (preview / fullscreen / regenerate / variations)
- Browser automation live view (page screenshots, DOM tree)
- Long-running task progress (cancel / pause / resume)
- Notification system (toast / inline)
- Dark / light mode toggle (tokens already exist)
- Keyboard shortcuts panel

## Phase 3 — Workspace awareness

- Memory panel (conversation / workspace / long-term)
- Workspace context switcher (org / project)
- File manager (preview / rename / delete / replace)
- Approval workflow: wire `approval_required` event to a real
  user-action that resumes the flow (Phase 2 backend)
- Multi-agent parallel visualization (when SubTasks are parallelizable)

## Phase 4 — Advanced

- Voice input
- Live collaboration (multiple users)
- Remote browser session viewer
- Workflow builder (visual drag-and-drop of SubTasks)
- Custom widget registry (plugin marketplace)
- Realtime dashboards (cost / latency / agent health)

---

## Open design questions

1. **Single-pane vs. tri-pane layout?** Phase 1 uses tri-pane
   (header / sidebar / main). Phase 2 may collapse to two-pane on
   narrow viewports.
2. **Where does `MessageInput` live?** Bottom-fixed for now, with the
   `AgentTimeline` filling the main panel above it. The timeline IS the
   conversation.
3. **How is approval requested across the SSE stream?** Phase 1 shows
   the card; the actual resume mechanism (Phase 2 backend) is a
   `POST /api/chat/approval` that re-injects the user's decision into
   the paused flow.
4. **Should the plan be editable before execution?** Yes (Phase 2) —
   the user can drop subtasks or change the agent before any tool runs.
