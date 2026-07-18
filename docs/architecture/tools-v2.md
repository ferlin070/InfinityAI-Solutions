# Tools & Provider Bridges v2

> **Status:** IMPLEMENTED (M2 — tooling expansion). No breaking changes to the existing `agents.provider` / `agents.model` / `InfinityLLMAdapter` contract.

## Scope

This document covers three additions to the AI execution layer:

1. **AI provider bridges** — new concrete providers behind the existing `LLMProvider` ABC.
2. **Tooling expansion** — Playwright browser tools, DB tools, workflow tools, MCP client.
3. **Per-agent tool assignment** — single-source-of-truth in `tool_mappings.py`.

These do not change agent personas (roles/goals/backstories), routing logic, or the CrewAI Flow pattern. They only widen the surface an agent can act on.

---

## 1. Provider bridges

Every provider implements `LLMProvider` (`src/ai/providers/base.py`). The host application is provider-unaware — only `InfinityLLMAdapter` and `resolve_provider()` know the difference.

| Provider    | Env var(s)                                | Optional pip dep   | Notes                                |
|-------------|--------------------------------------------|--------------------|--------------------------------------|
| `openai`    | `OPENAI_API_KEY`                           | (already required) | MVP default                          |
| `anthropic` | `ANTHROPIC_API_KEY`                        | `anthropic>=0.40`  | Claude Sonnet/Opus/Haiku             |
| `gemini`    | `GEMINI_API_KEY` *or* `GOOGLE_API_KEY`     | `google-genai>=1`  | Uses new unified SDK                 |
| `openrouter`| `OPENROUTER_API_KEY`                       | (uses `openai` SDK)| Multi-model proxy, OpenAI-compatible|
| `ollama`    | `OLLAMA_API_KEY` (any), `OLLAMA_BASE_URL`  | (uses `openai` SDK)| Local, free at runtime               |
| `azure`     | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL` | (uses `openai` SDK) | Azure-hosted OpenAI deployments |

### Tool-calling compatibility

All providers support tool/function-calling. `LLMResult.tool_calls` is normalised to the OpenAI shape:

```python
{"id": str, "function": {"name": str, "arguments": str-JSON}}
```

So the existing tool loop in `InfinityLLMAdapter.call()` works without per-provider branches — we translate to/from the vendor's native format in the provider module and the adapter consumes a uniform shape.

`InfinityLLMAdapter` was also fixed to group all `tool_calls` of one turn into a single assistant message (previously it emitted one assistant message per call, which broke providers that require one message per turn).

### Adding another provider

1. Create `src/ai/providers/foo_provider.py` with a class implementing `LLMProvider`.
2. Add an entry to `resolve_provider()` in `src/ai/providers/registry.py`.
3. Add pricing to `_PRICING_PER_1K_TOKENS` so `cost_usd` is recorded.

Zero changes to agents, flows, or factory call-sites.

---

## 2. Tooling expansion

### 2.1 Browser tools (Playwright / Chromium)

- Module: `src/ai/browser/`
- Singleton session manager keeps one Chromium process with one isolated `BrowserContext` per `session_id`. Idle sessions are reaped after `BROWSER_IDLE_TTL_SECONDS` (default 300s).
- Default browser: headless Chromium, viewport 1280×800. Toggle with `BROWSER_HEADLESS=false`.
- All tools return strings and are pure-sync (CrewAI `@tool` decorator) — they call the sync Playwright API.

| Tool                          | Purpose                                                                                     |
|-------------------------------|---------------------------------------------------------------------------------------------|
| `Browser Navigate`            | Open a URL, return final URL + title.                                                       |
| `Browser Get UI State`        | Dump a flat list of interactive elements (selector, label, options) for the LLM to choose from. |
| `Browser Click`               | Click by CSS selector.                                                                      |
| `Browser Type`                | Fill an input/textarea (clears first by default, optional `press_enter`).                   |
| `Browser Select Dropdown`     | Pick an option in a `<select>` by `value`, `label`, or `index`.                             |
| `Browser Screenshot`          | Save PNG to `BROWSER_SCREENSHOT_DIR`, return the path.                                      |
| `Browser Scroll`              | Scroll in 4 directions.                                                                     |
| `Browser Wait For`            | Wait for an element to reach a state (`visible`/`hidden`/`attached`/`detached`).            |
| `Browser Extract Text`        | Pull inner text of one or many elements.                                                    |
| `Browser Close Session`       | Tear down a session explicitly.                                                             |

If Playwright is not installed (`pip install playwright && playwright install chromium`), browser tools are silently absent from agents — the rest of the system still works.

### 2.2 Database tools

`src/ai/tools/db_tools.py` — thin wrappers around `src/db/repositories/*` so agents can do more than read. Each tool returns a compact JSON string (truncated at 4 KB) and follows the existing `@tool` pattern.

| Tool                          | Repo             | R/W |
|-------------------------------|------------------|-----|
| `DB List Contacts`            | `ContactRepo`    | R   |
| `DB Upsert Contact`           | `ContactRepo`    | W   |
| `DB Update Contact Tags`      | `ContactRepo`    | W   |
| `DB List Leads`               | `LeadRepo`       | R   |
| `DB Upsert Lead`              | `LeadRepo`       | W   |
| `DB List Products`            | `ProductRepo`    | R   |
| `DB Search Products`          | `ProductRepo`    | R   |
| `DB Create Product`           | `ProductRepo`    | W   |
| `DB Create Quotation`         | `QuotationRepo`  | W   |
| `DB Approve Quotation`        | `QuotationRepo`  | W   |
| `DB List Pending Quotations`  | `QuotationRepo`  | R   |
| `DB Enqueue Job`              | `JobRepo`        | W   |
| `DB List Open Conversations`  | `ConversationRepo` | R |
| `DB Create Conversation`      | `ConversationRepo` | W |
| `DB Save Message`             | `MessageRepo`    | W   |
| `DB List Channels`            | `ChannelRepo`    | R   |

The pre-existing narrow tools (`Contact Info`, `Product Pricing`, `Conversation History`) are unchanged and continue to be the preferred single-record lookups.

### 2.3 Workflow tools

`src/ai/tools/workflow_tools.py` — multi-step business operations built on the jobs queue + repos. Each tool is one function call from the LLM's perspective.

| Tool                                  | What it does                                                                                          |
|---------------------------------------|-------------------------------------------------------------------------------------------------------|
| `Workflow Trigger Inbound Reply`      | Upsert contact → open conversation → enqueue `process_inbound` job. Returns the conversation + job ids. |
| `Workflow Generate Quotation`         | Resolve items → compute totals → insert `quotations` row → enqueue `generate_quotation` (PDF) job.   |
| `Workflow Trigger Daily Briefing`     | Enqueue `daily_briefing` (optionally delayed via `run_at`).                                           |
| `Workflow Lead Pipeline Summary`      | Counts by score + top 5 hot + 5 most recent.                                                          |
| `Workflow Schedule Job`               | Generic scheduler for any job type.                                                                   |

### 2.4 MCP client

`src/ai/mcp/` — load tools from external Model Context Protocol servers and present them as first-class CrewAI tools.

- Optional dep: `pip install mcp`.
- Config: `MCP_SERVERS` env var, JSON array of `{name, transport, command|url, env, headers}`.
- Transports: `stdio` (subprocess), `http`/`streamable_http`/`sse` (HTTP).
- Each client owns a dedicated background event loop so the transport stays connected across many tool invocations.
- Loaded tools are merged into every agent's tool list (`get_all_tools_for_agent` in `tool_mappings.py`).

---

## 3. Per-agent tool assignment

Single source of truth: `src/ai/agents/tool_mappings.py`.

| Agent   | Tools                                                                              |
|---------|------------------------------------------------------------------------------------|
| CLAUDIA | *(none — router only)*                                                             |
| MAYA    | pricing, contact info, conversation history, DB search/upsert (contact, lead), generate-quotation workflow |
| HAKIM   | system docs, DB list (products, channels), **all browser tools**                    |
| ZARA    | DB list products, DB list/approve quotations                                       |
| DANISH  | DB list/search products, browser (navigate, extract, UI state, screenshot)         |
| AIMAN   | DB list leads/contacts, browser (navigate, extract, screenshot)                    |
| AMELIA  | browser (navigate, extract)                                                        |
| ADILA   | workflow (pipeline, daily briefing, schedule), DB list conversations/leads        |

Adding/removing a tool is a one-line edit in `TOOL_MAPPINGS`; `build_crewai_agent()` reads it via `get_all_tools_for_agent()`.

---

## 4. Operational notes

- **All optional deps degrade gracefully.** Missing `anthropic`, `google-genai`, `playwright`, or `mcp` packages do not break imports — the corresponding tool/provider is silently absent until installed.
- **Pricing maps are incomplete-by-design.** Unknown model ids log a warning and record `cost_usd=0.0`. The same fail-open behaviour applies to all new providers.
- **Browser resource lifecycle.** A session is created on first use, reaped on idle. To force a clean slate, call `Browser Close Session` or set `BROWSER_IDLE_TTL_SECONDS=0`.
- **MCP security.** MCP tool calls run in the agent's process. Only configure servers you trust. The `MCP_SERVERS` env var is the only entry point — there is no DB or UI editing of MCP config in MVP.
