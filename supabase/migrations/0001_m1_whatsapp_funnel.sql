-- 0001_m1_whatsapp_funnel.sql
-- Fasa 1: WhatsApp Sales Funnel — channels, contacts, conversations,
-- messages, leads, products, quotations, quotation_items
-- Apply this AFTER 0000_foundation.sql.
-- RLS defined but inactive until multi-tenant activation (same pattern).

-- ============================================================
-- 9. CHANNELS (WhatsApp connection per phone number)
-- ============================================================
create table if not exists channels (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    type            text not null check (type in ('wa_webjs', 'wa_cloud')),
    phone_number    text not null,
    config          jsonb not null default '{}',  -- encrypted tokens (server-side only)
    status          text not null default 'pending_qr'
                    check (status in ('pending_qr', 'connected', 'disconnected')),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (org_id, phone_number)
);

-- ============================================================
-- 10. CONTACTS (WhatsApp contacts / leads sources)
-- ============================================================
create table if not exists contacts (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    phone           text not null,
    name            text,
    source          text not null default 'whatsapp'
                    check (source in ('whatsapp', 'fb_ads', 'tiktok_ads', 'manual')),
    tags            text[] not null default '{}',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (org_id, phone)
);

-- ============================================================
-- 11. CONVERSATIONS
-- ============================================================
create table if not exists conversations (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    contact_id      uuid not null references contacts(id) on delete cascade,
    channel_id      uuid not null references channels(id) on delete cascade,
    status          text not null default 'open'
                    check (status in ('open', 'pending_human', 'closed')),
    mode            text not null default 'ai'
                    check (mode in ('ai', 'human')),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- ============================================================
-- 12. MESSAGES
-- ============================================================
create table if not exists messages (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    conversation_id uuid not null references conversations(id) on delete cascade,
    direction       text not null check (direction in ('inbound', 'outbound')),
    sender          text not null check (sender in ('customer', 'ai', 'staff')),
    body            text,
    media_url       text,
    external_id     text,  -- WhatsApp message ID (dedup key)
    status          text not null default 'sent'
                    check (status in ('sent', 'delivered', 'read', 'failed')),
    created_at      timestamptz not null default now(),
    unique (channel_id, external_id)
);
-- Note: unique(channel_id, external_id) prevents duplicate webhook processing.
-- channel_id is not formally a FK on messages (it's inferable via conversation),
-- but including it in the unique constraint avoids a join for dedup checks.

-- ============================================================
-- 13. LEADS
-- ============================================================
create table if not exists leads (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    contact_id      uuid not null references contacts(id) on delete cascade unique,
    score           text not null default 'cold'
                    check (score in ('hot', 'warm', 'cold')),
    status          text not null default 'new'
                    check (status in ('new', 'qualified', 'quoted', 'won', 'lost')),
    interest_summary text,
    score_reason    text,  -- Maya's explanation — transparency guardrail
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- ============================================================
-- 14. PRODUCTS (ground truth for pricing)
-- ============================================================
create table if not exists products (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    name            text not null,
    description     text,
    unit_price      numeric(12,2) not null check (unit_price >= 0),
    stock_qty       int check (stock_qty is null or stock_qty >= 0),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- ============================================================
-- 15. QUOTATIONS
-- ============================================================
create sequence if not exists quotation_number_seq;

create table if not exists quotations (
    id              uuid primary key default gen_random_uuid(),
    org_id          uuid not null references organizations(id) on delete cascade,
    lead_id         uuid not null references leads(id) on delete cascade,
    number          text not null,
    status          text not null default 'draft'
                    check (status in ('draft', 'pending_approval', 'sent', 'accepted', 'rejected', 'expired')),
    currency        text not null default 'MYR',
    subtotal        numeric(12,2) not null default 0,
    tax             numeric(12,2) not null default 0,
    total           numeric(12,2) not null default 0,
    pdf_path        text,  -- Supabase Storage path
    valid_until     date,
    approved_by     uuid references org_members(id),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (org_id, number)
);

-- Auto-generate quotation number: Q-{org_slug}-{seq}
create or replace function generate_quotation_number(org_id uuid)
returns text as $$
declare
    org_slug text;
    seq_num  int;
begin
    select slug into org_slug from organizations where id = org_id;
    seq_num := nextval('quotation_number_seq');
    return 'Q-' || org_slug || '-' || seq_num;
end;
$$ language plpgsql;

-- ============================================================
-- 16. QUOTATION ITEMS
-- ============================================================
create table if not exists quotation_items (
    id              uuid primary key default gen_random_uuid(),
    quotation_id    uuid not null references quotations(id) on delete cascade,
    product_id      uuid references products(id),
    description     text not null,
    qty             int not null check (qty > 0),
    unit_price      numeric(12,2) not null check (unit_price >= 0),
    line_total      numeric(12,2) not null check (line_total >= 0),
    created_at      timestamptz not null default now()
);

-- ============================================================
-- INDEXES
-- ============================================================
create index idx_channels_org         on channels(org_id);
create index idx_contacts_org         on contacts(org_id);
create index idx_contacts_phone       on contacts(org_id, phone);
create index idx_conversations_org    on conversations(org_id);
create index idx_conversations_status on conversations(org_id, status) where status = 'open';
create index idx_messages_conversation on messages(conversation_id, created_at);
create index idx_messages_external     on messages(channel_id, external_id);
create index idx_leads_org             on leads(org_id);
create index idx_leads_score           on leads(org_id, score);
create index idx_products_org          on products(org_id);
create index idx_quotations_org        on quotations(org_id);
create index idx_quotations_lead       on quotations(lead_id);
create index idx_quotation_items_q     on quotation_items(quotation_id);

-- ============================================================
-- RLS POLICIES
-- ============================================================
alter table channels        enable row level security;
alter table contacts        enable row level security;
alter table conversations   enable row level security;
alter table messages        enable row level security;
alter table leads           enable row level security;
alter table products        enable row level security;
alter table quotations      enable row level security;
alter table quotation_items enable row level security;

-- Tenant isolation pattern (same as 0000_foundation.sql — commented until multi-tenant):
-- create policy tenant_isolation on {table}
--   for all using (
--     org_id in (select org_id from org_members where user_id = auth.uid())
--   );
