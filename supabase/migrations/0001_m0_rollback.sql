-- ==========================================================================
-- ROLLBACK 0001 — Skema M0 Multi-Tenant (InfinityAI-Solutions)
-- Sifat: DROP TABLE mengikut susunan songsang.
-- ==========================================================================

-- 5. executions ---------------------------------------------------------------
drop table if exists public.executions cascade;

-- 4. agent_runs ---------------------------------------------------------------
drop table if exists public.agent_runs cascade;

-- 3. agents -------------------------------------------------------------------
drop table if exists public.agents cascade;

-- 2. org_members --------------------------------------------------------------
drop table if exists public.org_members cascade;

-- 1. organizations -----------------------------------------------------------
drop table if exists public.organizations cascade;

-- Helper Function -------------------------------------------------------------
drop function if exists public.is_org_member(uuid);
