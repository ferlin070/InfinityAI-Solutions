-- 0000_foundation.sql
-- Fasa 0: Core schema — organizations, agents, executions, audit, jobs
-- RLS enabled but policies are placeholders; actual RLS activation requires
-- Supabase Auth to be fully configured (auth.users + org_members population).
-- Dev: apply this file first, then 0001_m1_whatsapp_funnel.sql.

-- ============================================================
-- EXTENSIONS
-- ============================================================
create extension if not exists "pgcrypto";

-- ============================================================
-- 1. ORGANIZATIONS (root tenant)
-- ============================================================
create table if not exists organizations (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    slug        text not null unique,
    plan        text not null default 'trial'
                check (plan in ('free', 'starter', 'business', 'enterprise', 'trial')),
    status      text not null default 'active'
                check (status in ('active', 'suspended', 'cancelled')),
    settings    jsonb not null default '{}',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- ============================================================
-- 2. ORG MEMBERS (junction: auth.users ↔ organizations)
-- ============================================================
create table if not exists org_members (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null references auth.users(id) on delete cascade,
    role        text not null default 'staff'
                check (role in ('owner', 'admin', 'staff')),
    created_at  timestamptz not null default now(),
    unique (org_id, user_id)
);

-- ============================================================
-- 3. AGENTS (AI agent templates & per-org overrides)
-- ============================================================
create table if not exists agents (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid references organizations(id) on delete cascade,
    name            text not null,
    role_key        text not null check (role_key in (
                        'claudia', 'zara', 'maya', 'amelia',
                        'danish', 'aiman', 'adila', 'hakim'
                    )),
    system_prompt   text not null,
    model           text not null default 'gpt-4o-mini',
    provider        text not null default 'openai',
    enabled         boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (org_id, role_key)
);
-- org_id = null → template default (fallback if no per-org override)

-- ============================================================
-- 4. AGENT RUNS (per-call LLM execution log)
-- ============================================================
create table if not exists agent_runs (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    agent_id        uuid references agents(id),
    execution_id    uuid,  -- FK to executions, set after that table exists
    trigger         text not null default 'manual'
                    check (trigger in ('webhook', 'schedule', 'manual')),
    input_summary   text,
    output_summary  text,
    tokens_in       int not null default 0,
    tokens_out      int not null default 0,
    cost_usd        numeric(12,6) not null default 0,
    duration_ms     int not null default 0,
    model           text,
    provider        text,
    status          text not null default 'done'
                    check (status in ('running', 'done', 'failed')),
    error           text,
    created_at      timestamptz not null default now()
);

-- ============================================================
-- 5. EXECUTIONS (parent grouping for agent_runs)
-- ============================================================
create table if not exists executions (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    project_id      uuid,  -- future: dashboard project grouping
    status          text not null default 'running'
                    check (status in ('running', 'done', 'failed', 'rejected', 'halted_budget')),
    input_summary   text,
    output_summary  text,
    total_tokens    int not null default 0,
    total_cost_usd  numeric(12,6) not null default 0,
    triggered_by    text not null default 'dashboard'
                    check (triggered_by in ('dashboard', 'job:process_inbound', 'job:daily_briefing', 'job:follow_up')),
    started_at      timestamptz not null default now(),
    completed_at    timestamptz
);

-- Link agent_runs to executions
alter table agent_runs add constraint fk_agent_runs_execution
    foreign key (execution_id) references executions(id) on delete set null;

-- ============================================================
-- 6. JOBS (Postgres-backed queue)
-- ============================================================
create table if not exists jobs (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    type            text not null,
    payload         jsonb not null default '{}',
    status          text not null default 'pending'
                    check (status in ('pending', 'running', 'done', 'failed', 'cancelled')),
    run_at          timestamptz not null default now(),
    attempts        int not null default 0,
    max_attempts    int not null default 3,
    last_error      text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- claim_job RPC (used by worker runner: SELECT ... FOR UPDATE SKIP LOCKED)
create or replace function claim_job(p_current_time timestamptz)
returns setof jobs
language sql
as $$
    update jobs
    set status = 'running', attempts = attempts + 1, updated_at = now()
    where id = (
        select id from jobs
        where status = 'pending'
          and run_at <= p_current_time
          and attempts < max_attempts
        order by run_at asc
        limit 1
        for update skip locked
    )
    returning *;
$$;

-- ============================================================
-- 7. AUDIT LOGS (append-only)
-- ============================================================
create table if not exists audit_logs (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    actor_type      text not null check (actor_type in ('user', 'agent', 'system')),
    actor_id        text not null,
    action          text not null,
    entity          text not null,
    entity_id       text,
    meta            jsonb not null default '{}',
    created_at      timestamptz not null default now()
);
-- enforce append-only: no update/delete policies will be granted

-- ============================================================
-- 8. REPORTS (daily briefing, weekly finance, etc.)
-- ============================================================
create table if not exists reports (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    type            text not null check (type in ('daily_briefing', 'weekly_finance')),
    period_start    date not null,
    period_end      date not null,
    content_md      text,
    delivered_via   text,
    created_at      timestamptz not null default now()
);

-- ============================================================
-- INDEXES
-- ============================================================
create index idx_org_members_user on org_members(user_id);
create index idx_org_members_org   on org_members(org_id);
create index idx_agents_org        on agents(org_id);
create index idx_agent_runs_org    on agent_runs(org_id);
create index idx_agent_runs_exec   on agent_runs(execution_id);
create index idx_executions_org    on executions(org_id);
create index idx_jobs_status       on jobs(status, run_at) where status = 'pending';
create index idx_jobs_org          on jobs(org_id);
create index idx_audit_logs_org    on audit_logs(org_id, created_at desc);
create index idx_reports_org       on reports(org_id, type, period_start desc);

-- ============================================================
-- RLS POLICIES
-- ============================================================
-- Note: RLS is defined but WON'T be truly active until:
--   (a) auth.users has real users, and
--   (b) org_members is populated.
-- For the single-tenant pilot phase, the service_role key
-- (which bypasses RLS) is used for all backend operations.
-- Enable RLS when multi-tenant goes live.

alter table organizations enable row level security;
alter table org_members    enable row level security;
alter table agents         enable row level security;
alter table agent_runs     enable row level security;
alter table executions     enable row level security;
alter table jobs           enable row level security;
alter table audit_logs     enable row level security;
alter table reports        enable row level security;

-- Tenant isolation pattern (commented out until multi-tenant activation):
-- create policy tenant_isolation on {table}
--   for all using (
--     org_id in (select org_id from org_members where user_id = auth.uid())
--   );

-- ============================================================
-- SEED DATA: default organization
-- ============================================================
insert into organizations (id, name, slug, plan, status)
values (
    '00000000-0000-0000-0000-000000000001',
    'Default',
    'default',
    'starter',
    'active'
) on conflict (id) do nothing;
