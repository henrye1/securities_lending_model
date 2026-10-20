-- Securities Lending (Share Cover) Model - initial schema.
-- Workflow tables mirror the suite siblings: documents stored as jsonb payloads.

create table if not exists batches (
  id text primary key,
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists transactions (
  id text primary key,
  batch_id text not null references batches(id) on delete cascade,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_transactions_batch on transactions(batch_id);

create table if not exists runs (
  id text primary key,
  transaction_id text not null references transactions(id) on delete cascade,
  payload jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_runs_transaction on runs(transaction_id);

-- Service-role access only (no anon policies).
alter table batches enable row level security;
alter table transactions enable row level security;
alter table runs enable row level security;
