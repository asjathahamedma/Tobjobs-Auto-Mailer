alter table public.bot_profiles
  add column if not exists headline text not null default '',
  add column if not exists include_keywords text[] not null default '{}',
  add column if not exists exclude_keywords text[] not null default '{}',
  add column if not exists seniority_level text not null default 'mid',
  add column if not exists years_experience integer not null default 0,
  add column if not exists domains text[] not null default '{}',
  add column if not exists min_match_score integer not null default 4;
alter table public.bot_profiles
  alter column seniority_level set default 'unspecified';

alter table public.resumes
  add column if not exists target_roles text[] not null default '{}',
  add column if not exists seniority_level text not null default 'unspecified',
  add column if not exists years_experience integer not null default 0,
  add column if not exists core_skills text[] not null default '{}',
  add column if not exists domains text[] not null default '{}',
  add column if not exists include_keywords text[] not null default '{}',
  add column if not exists exclude_keywords text[] not null default '{}',
  add column if not exists preferred_locations text[] not null default '{}',
  add column if not exists remote_preference boolean not null default false,
  add column if not exists min_match_score integer not null default 4,
  add column if not exists daily_apply_cap integer not null default 5,
  add column if not exists active boolean not null default true;

create table if not exists public.education (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  school text not null default '',
  degree text not null default '',
  field_of_study text not null default '',
  start_year integer,
  end_year integer,
  notes text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.work_experience (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  company text not null default '',
  role text not null default '',
  start_date text not null default '',
  end_date text not null default '',
  summary text not null default '',
  achievements text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists public.answer_bank (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  question text not null,
  answer text not null,
  tags text[] not null default '{}',
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.application_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  application_id uuid references public.applications(id) on delete cascade,
  event_type text not null default 'note',
  details text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.ai_usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  task text not null,
  provider text not null,
  model text not null,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  latency_ms integer not null default 0,
  status text not null default 'success',
  created_at timestamptz not null default now()
);

create index if not exists bot_profiles_user_created_idx on public.bot_profiles (user_id, created_at desc);
create index if not exists education_user_created_idx on public.education (user_id, created_at desc);
create index if not exists work_experience_user_created_idx on public.work_experience (user_id, created_at desc);
create index if not exists answer_bank_user_created_idx on public.answer_bank (user_id, created_at desc);
create index if not exists application_events_user_created_idx on public.application_events (user_id, created_at desc);
create index if not exists application_events_application_created_idx on public.application_events (application_id, created_at desc);
create index if not exists ai_usage_user_created_idx on public.ai_usage (user_id, created_at desc);

drop trigger if exists bot_profiles_updated_at on public.bot_profiles;
create trigger bot_profiles_updated_at before update on public.bot_profiles
for each row execute function public.set_updated_at();

drop trigger if exists answer_bank_updated_at on public.answer_bank;
create trigger answer_bank_updated_at before update on public.answer_bank
for each row execute function public.set_updated_at();

alter table public.bot_profiles enable row level security;
alter table public.education enable row level security;
alter table public.work_experience enable row level security;
alter table public.answer_bank enable row level security;
alter table public.application_events enable row level security;
alter table public.ai_usage enable row level security;

drop policy if exists "Users manage their bot profiles" on public.bot_profiles;
create policy "Users manage their bot profiles"
on public.bot_profiles for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

drop policy if exists "Users manage their education" on public.education;
create policy "Users manage their education"
on public.education for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

drop policy if exists "Users manage their work experience" on public.work_experience;
create policy "Users manage their work experience"
on public.work_experience for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

drop policy if exists "Users manage their answer bank" on public.answer_bank;
create policy "Users manage their answer bank"
on public.answer_bank for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

drop policy if exists "Users manage their application events" on public.application_events;
create policy "Users manage their application events"
on public.application_events for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

drop policy if exists "Users read their AI usage" on public.ai_usage;
create policy "Users read their AI usage"
on public.ai_usage for select to authenticated
using (user_id = (select auth.uid()));

drop policy if exists "Users record their AI usage" on public.ai_usage;
create policy "Users record their AI usage"
on public.ai_usage for insert to authenticated
with check (user_id = (select auth.uid()));
