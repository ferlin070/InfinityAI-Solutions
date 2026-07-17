# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## AI Command Center

**STATUS: DRAFT**

| | |
| --- | --- |
| **Product Name** | AI Command Center (Sistem AI Ghazwah) |
| **Document Version** | v0.1 |
| **Prepared by** | InfinityAI Solutions (Developer) |
| **For** | Small & medium business owners in Malaysia |
| **Date** | 2026-07-17 |
| **Related Documents** | Sistem Semasa (docs/architecture/sistem-semasa.md), Proposal v2 (docs/architecture/proposal-v2.md), M1 WhatsApp Sales Funnel (docs/architecture/m1-whatsapp-sales-funnel.md), AI Execution CrewAI (docs/architecture/ai-execution-crewai.md), Dashboard Design (docs/frontend/dashboard-design.md), Business Documentation (docs/business/dokumentasi-perniagaan.md) |

---

# 1. Product Overview

Small and medium business owners in Malaysia currently juggle multiple operational roles — marketing, sales, finance, content creation, training, and IT — often relying on scattered tools (Google Drive for storage, manual WhatsApp chats for customer communication, separate platforms for ads) or hiring costly full-time staff for each function. There is no unified system that combines AI-powered task automation with direct customer-facing communication channels. Existing chatbot solutions are rigid (rule-based) and cannot handle context-aware sales conversations, lead qualification, or quotation generation.

The AI Command Center is a multi-agent AI orchestration platform that replaces fragmented manual operations with a unified "virtual office" of 8 AI specialists. The system uses a manager-worker architecture: Claudia (Chief of Staff) receives business instructions and delegates tasks to 7 specialist agents (Marketing, Sales/CRM, Finance, Content, Training, Operations, Technical). The V2 build extends this foundation into a SaaS platform with a WhatsApp Sales Funnel (M1) as the primary customer-facing channel — enabling automated inbound message handling, context-aware AI replies, lead scoring, quotation generation with PDF, and human-in-the-loop approval — all managed through a dashboard with an office-document visual identity.

# 2. Goals

- Reduce business operational costs by up to 70% by replacing multiple staff roles with AI agents working 24/7.
- Eliminate slow lead response times by providing instant, context-aware WhatsApp replies with accurate pricing and quotations.
- Centralize all customer interactions (WhatsApp conversations, leads, quotations) into a single CRM dashboard with transparent lead scoring and audit trails.
- Provide structured daily business briefings to owners so they have an up-to-date snapshot of sales, leads, pending approvals, and recommended actions every morning.
- Establish a scalable multi-tenant architecture (Supabase + RLS) from day one so onboarding new business clients requires zero schema changes.

# 3. Users & Roles

- **Owner :** Full system access including billing, organization management, member invitations, LLM cost monitoring, and subscription settings. Receives daily business briefings and quotation approval notifications.
- **Admin :** Manages WhatsApp channels (connect/disconnect numbers via QR), configures AI agent prompts and models, approves quotations before they are sent to customers, and manages staff accounts.
- **Staff :** Views open conversations and lead profiles, manually takes over conversations from AI when needed (mode switch), sends manual replies, and creates draft quotations.
- **Customer (End User) :** Interacts with the system exclusively via WhatsApp — sends messages, receives AI replies, requests pricing, and receives quotation PDFs. Has no dashboard access.

# 4. Scope

## 4.1 Included (MVP)

- **AI Agent Orchestration (v1 Foundation):** 8-agent system (Claudia + 7 specialists) using CrewAI framework with OpenAI as primary LLM provider, provider-agnostic abstraction layer, and structured JSON routing via Claudia.
- **Supabase Backend & Multi-Tenant Foundation:** Postgres database with all tables having `org_id` columns, Row-Level Security policies, Supabase Auth, and Storage for quotation PDFs. Single-tenant pilot with one seeded organization.
- **WhatsApp Sales Funnel (M1):** WhatsApp gateway service (Node.js + whatsapp-web.js) for connecting business numbers via QR code, inbound message webhook with HMAC auth and dedup, Maya agent for context-aware replies and lead scoring (hot/warm/cold), Zara agent for DB-only pricing, quotation PDF generation via ReportLab, human-in-the-loop approval workflow before sending quotations, and staff takeover capability.
- **Dashboard Interface:** Vanilla HTML/CSS/JS dashboard with "Dokumen Pejabat" design system (IBM Plex fonts, paper/ink/stamp color tokens, dark mode, i18n BM/EN), conversation list with message threads, lead grid with score filtering, quotation management with approve/reject, and WhatsApp channel connection panel with QR polling.
- **Daily Business Briefing (M1.5):** Scheduled 8 AM MYT briefing generation — Claudia summarizes yesterday's messages, new leads, pending quotations, and recommended actions, delivered via WhatsApp to the owner.
- **Agent Configuration API:** Per-agent prompt/model/provider overrides via REST API, persisted to an in-memory store with JSON file fallback, with SQL migration ready for DB-backed persistence.

## 4.2 Out of Initial Scope / Future Phases

Content & Ads pipeline (Danish content creation + TikTok/Meta Ads integration — M2), Finance & Follow-up automation (auto sales recording, weekly reports, follow-up campaigns — M3), Meta Cloud API adapter for production-grade WhatsApp (M2), multi-tenant activation beyond single pilot org (RLS already built, activation deferred), inventory management (M3), and autonomous daily operations with self-improving loops (M4). See Section 11 for details.

# 5. Assumptions & Constraints

- **LLM Provider Choice:** OpenAI (gpt-4o-mini) is the sole LLM provider for MVP. Future providers (NVIDIA NIM, Anthropic, Gemini, OpenRouter) can be added behind the existing provider-agnostic `LLMProvider` ABC without changing the orchestration layer. This is an architectural assumption by the developer.
- **WhatsApp Provider Risk:** The pilot uses `whatsapp-web.js` (an unofficial Node.js library), which carries known risks: account ban possibility, session breaks on WhatsApp updates, no green tick verification, and ~400-500MB RAM per session. The client must provide written acknowledgment before using this in production. Meta Cloud API adapter is designed but not built in MVP.
- **WhatsApp Gateway Capacity:** ~10-15 sessions per 8GB RAM VPS instance. Scaling beyond this requires additional gateway VPS instances or migration to Meta Cloud API.
- **Single-Tenant Pilot:** The MVP runs with exactly one pre-seeded organization (`00000000-0000-0000-0000-000000000001`). RLS policies exist in migration files but are not activated — data isolation only becomes enforceable when a second tenant's data enters the system. The architecture supports multi-tenancy with zero schema changes.
- **No Redis/RabbitMQ:** Job queue uses Postgres `FOR UPDATE SKIP LOCKED` on the `jobs` table instead of a dedicated message broker. This is sufficient for MVP throughput (<50 jobs/second). Re-evaluate if throughput exceeds this threshold.
- **Frontend Constraint:** The dashboard is vanilla HTML/CSS/JS with no frontend framework. There is no build step, no npm, and no CDN dependencies beyond Google Fonts. This is deliberate to keep deployment simple and avoid vendor lock-in at the UI layer.
- **Supabase Managed by Separate Developer:** All database schema changes are delivered as `.sql` migration files. A teammate who owns the live Supabase project reviews and applies them. The backend developer never applies migrations directly to production infrastructure.
- **Authentication:** Dashboard login uses a single hardcoded admin credential (`ADMIN_EMAIL`/`ADMIN_PASSWORD`) with session cookies, secure headers, timing-attack prevention, and rate limiting. Per-user Supabase Auth is deferred to when multi-tenant onboarding requires it.

# 6. Functional Requirements

## 6.1 AI Agent Orchestration

| **ID** | **Functional Requirement** | **Priority** |
| --- | --- | --- |
| **ORC-1** | Claudia (Chief of Staff) must accept a business instruction and return a structured JSON response assigning tasks to specialist agents with task descriptions. | **Wajib** |
| **ORC-2** | The system must route each assigned task to the correct specialist agent (Maya, Zara, Aiman, Danish, Amelia, Adila, Hakim) and return the agent's output to the user. | **Wajib** |
| **ORC-3** | The system must support sequential multi-agent execution when Claudia assigns tasks to multiple specialists (not parallel in MVP). | **Wajib** |
| **ORC-4** | The system must log every LLM call with tokens consumed, cost in USD, duration, and status in the `agent_runs` table for per-tenant cost tracking and budget enforcement. | **Wajib** |
| **ORC-5** | The system must support a provider-agnostic LLM abstraction layer so adding a new provider (e.g., Anthropic, Gemini) requires writing only one adapter file with zero changes to agents, flows, or orchestrators. | **Wajib** |
| **ORC-6** | The system must provide at least 3 crewai `@tool` functions (product_pricing, contact_info, conversation_history) that agents can invoke during execution — AI must never invent prices, only read from the database. | **Wajib** |
| **ORC-7** | Each agent must have configurable prompts (role, goal, backstory), model, and provider via a REST API — stored as overrides that merge with system defaults. | **Penting** |
| **ORC-8** | The system should support streaming LLM responses for real-time user feedback during manual task execution. | **Penting** |

## 6.2 WhatsApp Sales Funnel

| **ID** | **Functional Requirement** | **Priority** |
| --- | --- | --- |
| **WAS-1** | The system must provide a gateway service (Node.js) that manages whatsapp-web.js sessions — one session per connected business number — with endpoints to start a session, get QR code for scanning, check connection status, and send text/documents. | **Wajib** |
| **WAS-2** | The system must expose an internal webhook endpoint (`POST /webhooks/wa-gateway`) that accepts inbound messages from the gateway, authenticates via shared secret, saves the message to the database, enqueues a `process_inbound` job, and returns 200 OK within milliseconds. | **Wajib** |
| **WAS-3** | The webhook must be idempotent — the `messages.external_id` unique constraint must prevent duplicate messages or double-enqueued jobs from retried webhook calls. | **Wajib** |
| **WAS-4** | A background worker must poll the `jobs` table with `FOR UPDATE SKIP LOCKED`, claim `process_inbound` jobs, and invoke the inbound conversation flow. | **Wajib** |
| **WAS-5** | The Maya (Sales/CRM) agent must, upon receiving an inbound message context (last 20 messages, lead profile, product catalog), produce a structured JSON reply containing: reply text in Bahasa Malaysia, intent classification (buying/inquiry/complaint/unclear), lead score (hot/warm/cold) with a score_reason, and optionally a needs_quotation flag with requested items. | **Wajib** |
| **WAS-6** | If Maya detects low confidence or an out-of-scope request (`intent = unclear`), the system must set the conversation mode to "human" and notify staff — no AI reply is sent without human review. | **Wajib** |
| **WAS-7** | If Maya identifies a quotation need (`needs_quotation = true`), the system must enqueue a `generate_quotation` job that uses Zara (Finance) to price items from the `products` table only, generate a PDF via ReportLab, upload it to Supabase Storage, create a quotation record with status `pending_approval`, and notify the owner. | **Wajib** |
| **WAS-8** | The quotation must never move from `pending_approval` to `sent` without an explicit human approval action via the dashboard — no code path auto-sends quotations. The price in the quotation must come from the `products` table, not from the agent's output (the repository function that creates `quotation_items` looks up the price itself and ignores any price the agent may have generated). | **Wajib** |
| **WAS-9** | The dashboard must display WhatsApp channel connection status with a QR code modal that auto-polls every 3 seconds until the channel status transitions from `pending_qr` to `connected`. Users must be able to disconnect channels. | **Wajib** |
| **WAS-10** | The dashboard must display open conversations with a message thread view, allow staff to take over conversations (switching mode from `ai` to `human`), and allow staff to send manual replies via WhatsApp. Conversations must clear the compose area after sending. | **Wajib** |
| **WAS-11** | The dashboard must display leads in a grid with score-based filtering (hot/warm/cold), showing name, phone, source, tags, interest summary, and score reason. | **Wajib** |
| **WAS-12** | The dashboard must display quotations pending approval with approve/reject actions, and refresh the list automatically after a decision. | **Wajib** |
| **WAS-13** | The lead score and interest_summary in the database must be updated automatically after every inbound message processing run based on Maya's output. | **Wajib** |

## 6.3 Daily Business Briefing

| **ID** | **Functional Requirement** | **Priority** |
| --- | --- | --- |
| **BRF-1** | The system must schedule a daily briefing job to run at 8:00 AM Malaysia Time (MYT, UTC+8). | **Wajib** |
| **BRF-2** | The daily briefing must be generated by Claudia and summarize: messages from the previous day, new leads created, quotations pending approval, and recommended actions for the owner. | **Wajib** |
| **BRF-3** | The generated briefing must be delivered to the owner via WhatsApp text message. | **Wajib** |

## 6.4 Agent Configuration API

| **ID** | **Functional Requirement** | **Priority** |
| --- | --- | --- |
| **AGC-1** | The system must expose a `GET /api/agents` endpoint that lists all 8 agent personas with their current configuration (role, goal, backstory, provider, model), merging system defaults with any stored overrides. | **Wajib** |
| **AGC-2** | The system must expose a `PUT /api/agents/{key}` endpoint that accepts partial configuration overrides (provider, model, role, goal, backstory) — undefined fields must retain their current or default values. | **Wajib** |
| **AGC-3** | The system must expose a `DELETE /api/agents/{key}` endpoint that resets an agent's configuration to system defaults. | **Penting** |
| **AGC-4** | Agent configuration overrides must take effect immediately for all subsequent CrewAI agent executions without requiring a server restart. | **Wajib** |
| **AGC-5** | A SQL migration (`agent_configurations` table with RLS) must be provided as the path to DB-backed persistence, replacing the in-memory store when the Supabase project is ready to apply it. | **Penting** |

## 6.5 Dashboard — General

| **ID** | **Functional Requirement** | **Priority** |
| --- | --- | --- |
| **DSH-1** | The dashboard must implement the "Dokumen Pejabat" (Office Document) design system exclusively — IBM Plex font family, paper/ink/stamp/green color tokens, max 3px border-radius, no gradients or glassmorphism. | **Wajib** |
| **DSH-2** | The dashboard must support both Bahasa Malaysia (BM) and English (EN) with instant language switching via a toggle, persisting the user's preference. | **Wajib** |
| **DSH-3** | The dashboard must support dark mode via a `data-theme="dark"` attribute on the root element, respecting the user's system preference when available. | **Wajib** |
| **DSH-4** | The dashboard must have a tabbed navigation system with at least two main tabs: "Arahan Kerja" (existing task execution) and "Operasi WhatsApp" (WhatsApp sales operations). | **Wajib** |
| **DSH-5** | The Operasi WhatsApp tab must have sub-panels: Perbualan (conversations), Prospek (leads), and Sebut Harga (quotations), plus a connection panel for WhatsApp channel management. | **Wajib** |
| **DSH-6** | The dashboard must implement XSS-safe rendering — all server data must pass through `escapeHtml()` or be inserted via `textContent`/`createTextNode` (never `innerHTML` with unsanitized strings). | **Wajib** |
| **DSH-7** | The dashboard's main Arahan Kerja flow (user input via textarea → Claudia delegation → specialist execution → results display) must continue working as the v1 foundation. | **Wajib** |

# 7. Key User Flows

## 7.1 WhatsApp Inbound — Happy Path (AI Reply)

1. Customer sends a WhatsApp message to the business number.
2. WA Gateway (Node.js) receives the message event and POSTs it to `FastAPI /webhooks/wa-gateway` with a shared secret header.
3. FastAPI webhook deduplicates via `messages.external_id`, saves the message to the database, enqueues a `process_inbound` job, and returns `200 OK` within milliseconds.
4. Worker claims the job (`FOR UPDATE SKIP LOCKED`), loads the last 20 messages + lead profile + product catalog, and invokes `InboundConversationFlow`.
5. Maya (Sales/CRM Agent) receives the context and produces a structured JSON reply with `reply` text (BM), `intent`, `lead_score`, `score_reason`, and optionally `needs_quotation`.
6. If Maya's intent is `unclear`, conversation mode is set to `"human"`, staff is notified, and no AI reply is sent.
7. Otherwise, Maya's reply is sent back to the customer via the gateway, lead score is updated in the database, and an `agent_runs` record is created.

## 7.2 WhatsApp Inbound — Quotation Flow (Human-in-the-Loop)

1. Continuing from Step 5 above, if `needs_quotation = true` with requested items:
2. A `generate_quotation` job is enqueued.
3. Worker processes the job: Zara (Finance Agent) prices each item from the `products` table only (guardrail — ignores any price from the agent's output).
4. A ReportLab PDF is generated with line items, subtotal, tax, and total.
5. PDF is uploaded to Supabase Storage under `{org_id}/quotations/{quotation_number}.pdf`.
6. Quotation record is created in the database with status `pending_approval`.
7. Maya's reply (acknowledging the request) is sent to the customer via WhatsApp.
8. Owner is notified (dashboard badge) that a quotation awaits approval.
9. Owner reviews and clicks "Approve" on the dashboard → quotation status changes to `sent`, PDF is delivered to the customer via WhatsApp.
10. An `agent_runs` record is created for Zara's execution.

## 7.3 Staff Takeover (Human Escalation)

1. Staff opens the Operasi WhatsApp → Perbualan tab on the dashboard.
2. Staff sees a conversation with mode `ai` or `pending_human` and reviews the message thread.
3. Staff clicks "Take Over" — system sets `conversations.mode = "human"`, AI stops replying to this conversation.
4. Staff types a reply and clicks "Send" — message is saved to the database and sent via the gateway to the customer's WhatsApp number.
5. The compose area clears after sending.
6. Staff can return control to AI by setting mode back to `ai` (future phase).

## 7.4 Daily Business Briefing

1. APScheduler triggers the `daily_briefing` job at 8:00 AM MYT every day.
2. Worker claims the job and invokes the daily briefing handler.
3. Claudia (Chief of Staff) receives a system prompt with yesterday's data: message count, new leads (with scores), quotations pending approval, and a template for recommended actions.
4. Claudia generates a structured briefing in natural Bahasa Malaysia.
5. The briefing is sent as a WhatsApp message to the owner's registered number.
6. The briefing content is also stored in the `reports` table for audit/reference.

## 7.5 Agent Configuration Update

1. Admin opens the dashboard's agent configuration section (or uses a REST client).
2. Admin selects an agent (e.g., "Maya") and modifies fields such as `model` (changing from `gpt-4o-mini` to `gpt-4o`) or `backstory` (customizing the prompt).
3. Admin sends a `PUT /api/agents/maya` request with only the fields to override.
4. System stores the overrides in the in-memory config store (persisted to JSON file).
5. System returns the full merged configuration (defaults + overrides) to confirm.
6. All subsequent CrewAI executions for Maya use the new configuration immediately — no restart needed.

# 8. Data Model (High-Level)

| **Entity** | **Key Fields** | **Description** |
| --- | --- | --- |
| **organizations** | id, name, slug, plan, status, settings (jsonb) | Tenant root — every row in every table belongs to one org via `org_id` |
| **org_members** | org_id, user_id, role (owner/admin/staff) | Junction table linking Supabase Auth users to organizations |
| **channels** | id, org_id, type (wa_webjs / wa_cloud), phone_number, config (jsonb, encrypted), status (pending_qr / connected / disconnected) | WhatsApp number connections — one channel per phone number |
| **contacts** | id, org_id, phone, name, source (whatsapp / fb_ads / tiktok_ads / manual), tags (text[]) | Customer contacts — unique per (org_id, phone) |
| **conversations** | id, org_id, contact_id, channel_id, status (open / pending_human / closed), mode (ai / human) | Message threads — `mode=human` means AI stops replying |
| **messages** | id, org_id, conversation_id, direction (inbound / outbound), sender (customer / ai / staff), body, media_url, external_id, status | Individual WhatsApp messages — `external_id` deduplicates webhook retries |
| **leads** | id, org_id, contact_id, score (hot / warm / cold), status (new / qualified / quoted / won / lost), interest_summary, score_reason | Sales leads scored by Maya — `score_reason` provides transparency |
| **products** | id, org_id, name, description, unit_price, stock_qty (nullable) | Product catalog — sole source of truth for pricing (guardrail: AI never invents prices) |
| **quotations** | id, org_id, lead_id, number (auto: Q-{org}-{seq}), status (draft / pending_approval / sent / accepted / rejected / expired), subtotal, tax, total, pdf_path, approved_by | Sales quotations — human approval required before `sent` |
| **quotation_items** | id, org_id, quotation_id, description, qty, unit_price, line_total | Line items within a quotation |
| **agent_configurations** | id, org_id, agent_key, provider (nullable), model (nullable), [role, goal, backstory] (nullable) | Per-agent per-org overrides — null fields fall back to system defaults |
| **agents** | id, org_id (nullable), name, role_key, system_prompt, model, provider, enabled | Agent persona templates — `org_id=NULL` = system default |
| **agent_runs** | id, org_id, agent_id, trigger (webhook / schedule / manual), input_summary, output_summary, tokens_in, tokens_out, cost_usd, duration_ms, status, error | LLM execution audit log — basis for per-tenant cost tracking and billing |
| **executions** | id, org_id, prompt, status, model, results (jsonb), [assignments, rejection_reason, error] | Dashboard task execution records — links Claudia classifications to specialist results |
| **jobs** | id, org_id, type, payload (jsonb), status (pending / running / done / failed), run_at, attempts, max_attempts, last_error | Postgres-based job queue — `FOR UPDATE SKIP LOCKED` for worker coordination |
| **reports** | id, org_id, type (daily_briefing / weekly_finance), period_start, period_end, content_md, delivered_via | Generated reports — daily briefing stored here |
| **audit_logs** | id, org_id, actor_type (user / agent / system), actor_id, action, entity, entity_id, meta (jsonb) | Append-only audit trail — no UPDATE/DELETE policies |

**Note:** Fields in [brackets] denote inherited or system-managed fields. The `agent_configurations` table is the Fase Lanjutan replacement for the current in-memory config store.

# 9. Non-Functional Requirements

- **Performance & Responsiveness:** The inbound message webhook must return `200 OK` within 1 second — it does no LLM work, only saves to DB and enqueues a job. All LLM processing (5-30 seconds) happens asynchronously in the worker process. The dashboard must load and render within 2 seconds on modern browsers under normal network conditions.
- **Security & Access Control:** All database access must have dual-layer protection — Row-Level Security (RLS) at the database level plus explicit `org_id` filtering in every repository query. Webhook endpoints must authenticate via shared secret or HMAC signature. The Supabase `service_role` key must never be exposed to the frontend. All user-facing data rendered in the dashboard must be sanitized via `escapeHtml()` or `textContent` to prevent XSS.
- **Data Isolation (Multi-Tenancy):** Every table must have an `org_id` column referencing `organizations(id)`. RLS policies must enforce that a user can only see rows belonging to organizations they are a member of. Automated tenant isolation tests must be included in CI. Currently single-tenant pilot — RLS activation is a configuration change, not a schema migration.
- **LLM Cost Control:** Every LLM call must be logged to `agent_runs` with input/output tokens, cost in USD, and duration from day one. A per-org budget guard must be implementable via `organizations.settings` without code changes (configuration only). AI execution must halt when the daily token budget is exceeded, and the owner must be notified.
- **Reliability & Resilience:** Failed jobs must retry up to 3 times with exponential backoff before being marked `failed` with the last error recorded. The Postgres job queue must use `FOR UPDATE SKIP LOCKED` so multiple worker instances can run concurrently without double-processing. Gateway sessions must survive restarts via LocalAuth persistence in Docker volumes.
- **Auditability:** Every agent action that triggers a business impact (creating a quotation, sending a message, changing a lead score) must be recorded in the `audit_logs` table with `actor_type = agent`, agent identity, entity affected, action taken, and metadata. The audit log must be append-only — no UPDATE or DELETE RLS policies.
- **Internationalization (i18n):** The dashboard UI must support Bahasa Malaysia (default) and English with instant client-side switching. Language preference must persist across sessions. All agent prompts and AI replies are in Bahasa Malaysia (business language of the target market).

# 10. Third-Party Integrations

| **Service** | **Function** | **Notes** |
| --- | --- | --- |
| **OpenAI API** | Primary LLM provider — all AI agent execution (Claudia, Maya, Zara, etc.) | MVP uses `gpt-4o-mini` (cost-efficient). Provider-agnostic abstraction layer allows swapping without code changes beyond a new adapter file. |
| **Supabase** | Postgres database (all tables + RLS), Authentication (JWT), Storage (quotation PDFs) | Managed cloud service with automatic backups. The Supabase project is owned and applied by a separate developer — only SQL migration files are produced in this repo. |
| **whatsapp-web.js** | Unofficial WhatsApp Web protocol implementation — session management, QR pairing, send/receive messages | Pilot phase only. Known risks: account ban, session breakage on WA updates, ~400-500MB RAM per session. Production clients must migrate to Meta Cloud API (adapter designed but not built — Phase 2). |
| **Google Drive (via GAS)** | Current v1 document storage (legacy) | Being replaced by Supabase Storage. Can remain as an optional export destination for clients who prefer Drive, but is no longer the primary storage. |
| **[Meta Cloud API] — Future Phase** | Production-grade WhatsApp Business API with green tick, high throughput, official support | Adapter interface (`channels/wa_cloud.py`) is designed and shares the same `WhatsAppProvider` ABC as the webjs adapter. Implementation deferred to M2. |
| **[TikTok Ads API] — Future Phase** | Read ad metrics, suggest creative optimization, automate campaign management | Integrated at M2 — Danish (Content) creates ad scripts, Aiman (Marketing) suggests budget allocation. |
| **[Meta Ads API] — Future Phase** | Read ad performance, A/B test suggestions, audience targeting recommendations | Integrated at M2 — Aiman analyzes product type and recommends Facebook Ads interests and demographics. |

# 11. Proposed Features / Future Phases

- **M2 — Content & Ads Pipeline.** Danish (Content Creator) generates TikTok video scripts and ad copy. Aiman (Marketing) analyzes trends and recommends budget allocation. Integration with TikTok Ads API and Meta Ads API for reading metrics and suggesting optimizations. Meta Cloud API adapter built and deployed for production-grade WhatsApp.
- **M3 — Finance & Follow-up.** Automated sales recording from accepted quotations. Weekly financial reports generated by Zara. Automated follow-up campaigns for abandoned carts / unpaid quotations. Inventory alerts when stock runs low.
- **M4 — Autonomous Daily Operations.** Self-improving loop where AI learns from owner feedback to improve output quality. Competitor monitoring via web research. Full autonomous daily ops with minimal human intervention. (Not promised to clients — re-evaluated after M3 based on real data.)
- **Multi-Tenant Onboarding.** Activate RLS policies, implement org registration flow (register → create org → invite members), per-tenant billing/subscription management, and per-tenant LLM cost tracking with budget alerts. Infrastructure already supports this with zero schema changes.
- **Dashboard Analytics & Real-Time Views.** Graphical charts for agent performance (response speed, tasks completed), real-time conversation feeds (WebSocket), and live financial tracking. Requires upgrading from vanilla JS to a lightweight reactive framework.
- **WhatsApp Template Messages & Rich Media.** Send interactive list messages, button templates, and rich media (images, video, audio) via the Meta Cloud API adapter. Requires Meta Business Verification.
- **Google Drive as Optional Export.** Clients who prefer Google Drive over Supabase Storage can keep GAS as an export destination for completed quotations and reports.

# 12. Open Questions / TBD

- **Brand Name:** Final product brand name for client-facing materials — "AI Command Center" vs "Sistem AI Ghazwah" vs a new name to be decided with the client.
- **Pricing Model:** Per-tenant subscription pricing structure (monthly flat fee vs per-LLM-token vs hybrid) has not been discussed with the client.
- **Timeline Commitment:** Specific delivery dates for M2/M3/M4 milestones have not been agreed — only M1 is currently committed with an urgent presentation deadline.
- **Meta Cloud API Enrollment:** Whether/when the client will complete Meta Business Verification to qualify for the Cloud API (required for production-grade WhatsApp with green tick) is undecided.
- **Owner WhatsApp Number for Briefings:** The specific WhatsApp number that the daily briefing should be delivered to has not been provided — currently assumed to be the first connected channel number.
- **Backup & Disaster Recovery:** RPO/RTO requirements and backup retention policies for customer data have not been discussed.
- **PDPA Compliance:** Specific data retention, export, and deletion policies per Malaysian Personal Data Protection Act requirements need client input.
- **Google Drive Transition:** Whether existing users who rely on Google Drive storage should be migrated to Supabase Storage or offered a dual-storage option during the transition period.

# 13. Glossary

- **Agent (AI Agent):** An autonomous AI persona with a defined role, goal, and backstory — Claudia (Chief of Staff), Maya (Sales/CRM), Zara (Finance), etc.
- **Claudia:** The Chief of Staff agent — receives business instructions and delegates tasks to specialist agents via structured JSON routing.
- **Maya:** The Sales & CRM agent — handles WhatsApp conversations, scores leads, and identifies quotation needs.
- **Zara:** The Finance agent — calculates pricing from the products table only (guardrail), generates quotation PDFs.
- **CrewAI:** The Python framework used for agent orchestration — replaces the earlier custom orchestrator with explicit Flow-based control.
- **InfinityLLMAdapter:** Custom bridge class (`BaseLLM` subclass) that connects CrewAI to the provider-agnostic LLM abstraction layer — the only code that CrewAI uses to call LLMs.
- **`whatsapp-web.js`:** Unofficial Node.js library that implements the WhatsApp Web protocol — used for the pilot WhatsApp gateway before migrating to Meta Cloud API.
- **WhatsApp Gateway (WA Gateway):** A separate Node.js service (`gateway/`) that manages whatsapp-web.js sessions and provides HTTP endpoints for QR pairing, sending messages, and forwarding inbound messages.
- **RLS (Row-Level Security):** PostgreSQL feature that restricts which rows a user can query or modify based on a policy — used for tenant data isolation.
- **Human-in-the-Loop:** A guardrail requiring explicit human approval before a system action is executed — applied to quotation sending and low-confidence AI replies.
- **Lead Score:** A classification (hot/warm/cold) assigned by Maya to each lead based on conversation analysis, with a written `score_reason` for transparency.
- **SKIP LOCKED:** PostgreSQL row-level locking feature used by the job queue so multiple worker instances can claim different jobs without conflict.
- **Service Role Key:** A Supabase API key with full database access (bypasses RLS) — used server-side only (worker, gateway), never exposed to the frontend.
- **Dokumen Pejabat (Office Document):** The dashboard's visual design system — IBM Plex fonts, paper/ink/stamp color tokens, office-document-inspired layout components.

---

*This document is a draft and may change as discussions with the client progress.*
