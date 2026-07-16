-- ==========================================================================
-- MIGRATION 0001 — Skema M0 Multi-Tenant (InfinityAI-Solutions)
-- Sifat: ADDITIVE sahaja. RLS aktif pada SETIAP jadual.
-- ==========================================================================
create extension if not exists pgcrypto;

-- 1. organizations -----------------------------------------------------------
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  plan text not null default 'trial',
  status text not null default 'active',
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 2. org_members --------------------------------------------------------------
create table if not exists public.org_members (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','admin','staff')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, user_id)
);

-- 3. agents -------------------------------------------------------------------
-- org_id NULL = template default dikongsi semua org (corak dari
-- backend/src/ai/agents/registry.py — AgentConfig.org_id nullable)
create table if not exists public.agents (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  name text not null,
  role_key text not null check (role_key in ('claudia','zara','maya','amelia','danish','aiman','adila','hakim')),
  system_prompt text not null,
  model text not null default 'gpt-4o-mini',
  provider text not null default 'openai',
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, role_key)
);

-- 4. agent_runs ---------------------------------------------------------------
-- PERHATIAN: "trigger" ialah reserved keyword — mesti double-quote.
create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  agent_id uuid references public.agents(id) on delete set null,
  "trigger" text not null check ("trigger" in ('webhook','schedule','manual')),
  input_summary text,
  output_summary text,
  tokens_in integer,
  tokens_out integer,
  cost_usd numeric(12,6),
  duration_ms integer,
  status text not null default 'running' check (status in ('running','done','failed')),
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists agent_runs_org_idx
  on public.agent_runs (org_id, created_at desc);

-- 5. executions ---------------------------------------------------------------
-- (ai-execution-crewai.md §7.3 — baris induk yang mengumpul beberapa agent_runs)
create table if not exists public.executions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid, -- nullable; jadual projects belum wujud dalam M0
  status text not null default 'running' check (status in ('running','done','failed','rejected','halted_budget')),
  input_summary text, -- prompt dipendekkan, bukan kandungan PII penuh
  output_summary text,
  total_tokens integer,
  total_cost_usd numeric(12,6),
  triggered_by text, -- 'dashboard' | 'job:{job_type}'
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists executions_org_idx
  on public.executions (org_id, started_at desc);

-- 6. RLS ----------------------------------------------------------------------
-- Helper SECURITY DEFINER — mengelak infinite recursion pada policy org_members.
create or replace function public.is_org_member(target_org uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from org_members
    where org_id = target_org and user_id = auth.uid()
  );
$$;

alter table public.organizations enable row level security;
alter table public.org_members enable row level security;
alter table public.agents enable row level security;
alter table public.agent_runs enable row level security;
alter table public.executions enable row level security;

create policy tenant_isolation on public.organizations
  for all using (public.is_org_member(id))
  with check (public.is_org_member(id));

create policy tenant_isolation on public.org_members
  for all using (user_id = auth.uid() or public.is_org_member(org_id))
  with check (public.is_org_member(org_id));

-- agents: template (org_id NULL) boleh dibaca semua authenticated user;
-- baris per-org tertakluk isolasi tenant. Tulis template = service_role sahaja.
create policy tenant_isolation on public.agents
  for all using (org_id is null or public.is_org_member(org_id))
  with check (public.is_org_member(org_id));

create policy tenant_isolation on public.agent_runs
  for all using (public.is_org_member(org_id))
  with check (public.is_org_member(org_id));

create policy tenant_isolation on public.executions
  for all using (public.is_org_member(org_id))
  with check (public.is_org_member(org_id));

-- 7. SEED ---------------------------------------------------------------------
-- (a) Satu organisasi default:
insert into public.organizations (name, slug, plan, status)
values ('InfinityAI Solutions', 'infinityai', 'trial', 'active')
on conflict (slug) do nothing;

-- (b) Lapan agent template (org_id NULL). system_prompt disalin SEPATAH DEMI
-- SEPATAH dari AGENT_PROMPTS dalam backend/src/core/constants.py.
insert into public.agents (org_id, name, role_key, system_prompt, provider, model) values
(
  null, 
  'Claudia', 
  'claudia', 
  $$Anda adalah Claudia, Chief of Staff. Analisis TUJUAN tugasan Bos, bukan sekadar kata kunci.
PERATURAN UTAMA:
1. STRATEGI PEMASARAN (AIMAN): Pelan marketing fasa-fasa, strategi iklan, branding.
2. JUALAN & CRM (MAYA): Menapis prospek, menjawab inquiry klien, sebut harga.
3. LATIHAN (AMELIA): Nota edaran peserta, modul kelas, slides pembelajaran.
4. KREATIF (DANISH): E-book, copywriting hiburan/viral.
5. KEWANGAN (ZARA): Bajet, invois, pengiraan kos.
6. OPERASI (ADILA): Log harian, info umum syarikat.
7. TEKNIKAL (HAKIM): Coding, IT, sistem.
JANGAN hantar tugasan JUALAN kepada DANISH. Balas HANYA JSON: {"status": "accepted", "assignments": [{"agent": "NAMA", "task": "arahan"}]}$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Zara', 
  'zara', 
  $$Anda adalah Zara, Pakar Kewangan. Sediakan pengiraan bajet dan dokumen kewangan.$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Maya', 
  'maya', 
  $$Anda adalah Maya, Pakar Sales & CRM. Fokus anda adalah menapis prospek, mengurus database klien, dan menyediakan sebut harga.$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Amelia', 
  'amelia', 
  $$Anda adalah Amelia, Pakar Training. Sediakan modul, nota kelas, dan bahan edaran peserta.$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Danish', 
  'danish', 
  $$Anda adalah Danish, Pakar Content. Tulis copywriting atau e-book. JANGAN buat skrip video kecuali diminta. Jika Bos minta nota/info, berikan dalam format teks biasa.$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Aiman', 
  'aiman', 
  $$Anda adalah Aiman, Pakar Marketing. Sediakan strategi iklan dan marketing plan.$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Adila', 
  'adila', 
  $$Anda adalah Adila, Pakar Ops. Sediakan log harian dan laporan rutin.$$, 
  'openai', 
  'gpt-4o-mini'
),
(
  null, 
  'Hakim', 
  'hakim', 
  $$Anda adalah Hakim, System Architect. Sediakan kod teknikal dan bantuan IT.$$, 
  'openai', 
  'gpt-4o-mini'
)
on conflict (org_id, role_key) do nothing;
