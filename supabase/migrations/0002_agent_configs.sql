-- 0002_agent_configs.sql
-- Per-agent prompt/model overrides so orgs can tune each AI persona.
-- Populated by the API; load_agents() in the backend checks this table
-- first and falls back to src/core/constants.py defaults.

create table if not exists public.agent_configurations (
    id            uuid primary key default gen_random_uuid(),
    org_id        uuid not null references public.organizations(id) on delete cascade,
    agent_key     text not null check (agent_key in (
                      'CLAUDIA', 'MAYA', 'ZARA', 'AMELIA', 'DANISH', 'AIMAN', 'ADILA', 'HAKIM'
                  )),
    provider      text,     -- null → use org default ("openai")
    model         text,     -- null → use org default ("gpt-4o-mini")
    role          text,     -- overrides the constant's role
    goal          text,     -- overrides the constant's goal
    backstory     text,     -- overrides the constant's backstory
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),
    unique (org_id, agent_key)
);

-- Seed org (single-tenant pilot) — no overrides, just the row so the
-- unique constraint is known and the UI can show "use defaults".
insert into public.agent_configurations (org_id, agent_key)
select '00000000-0000-0000-0000-000000000001', key
from (values ('CLAUDIA'), ('MAYA'), ('ZARA'), ('AMELIA'), ('DANISH'), ('AIMAN'), ('ADILA'), ('HAKIM')) as t(key)
on conflict (org_id, agent_key) do nothing;

-- RLS: each org sees only its own rows.
alter table public.agent_configurations enable row level security;

create policy "org_select_own_agent_configs"
    on public.agent_configurations for select
    using (org_id = auth.uid());

create policy "org_insert_own_agent_configs"
    on public.agent_configurations for insert
    with check (org_id = auth.uid());

create policy "org_update_own_agent_configs"
    on public.agent_configurations for update
    using (org_id = auth.uid());
