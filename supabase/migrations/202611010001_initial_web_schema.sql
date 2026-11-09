create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  storage_path text not null,
  file_name text not null,
  label text not null,
  summary text not null default '',
  title_keywords text[] not null default '{}',
  description_keywords text[] not null default '{}',
  extracted_text_length integer not null default 0 check (extracted_text_length >= 0),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (user_id, storage_path),
  unique (id, user_id)
);

create table public.job_listings (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  source_job_id text not null,
  source_url text not null,
  title text not null,
  company text,
  location text,
  description text not null default '',
  company_email text,
  salary text,
  employment_type text,
  posted_at date,
  discovered_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source, source_job_id),
  unique (source, source_url)
);

create table public.search_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'partially_completed', 'cancelled', 'failed')),
  search_parameters jsonb not null default '{}'::jsonb,
  progress jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  jobs_found integer not null default 0 check (jobs_found >= 0),
  error_summary text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.job_matches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id uuid not null references public.job_listings(id) on delete cascade,
  resume_id uuid,
  search_run_id uuid references public.search_runs(id) on delete set null,
  match_score integer not null default 0,
  match_explanation text not null default '',
  matched_title_keywords text[] not null default '{}',
  matched_description_keywords text[] not null default '{}',
  status text not null default 'discovered'
    check (status in ('discovered', 'shortlisted', 'awaiting_review', 'ready_to_apply', 'applied', 'interview', 'rejected', 'withdrawn', 'failed')),
  first_seen_at timestamptz not null default timezone('utc', now()),
  last_seen_at timestamptz not null default timezone('utc', now()),
  unique (user_id, job_id),
  foreign key (resume_id, user_id) references public.resumes(id, user_id) on delete cascade
);

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id uuid not null references public.job_listings(id) on delete cascade,
  status text not null default 'awaiting_review'
    check (status in ('discovered', 'shortlisted', 'awaiting_review', 'ready_to_apply', 'sending', 'applied', 'interview', 'rejected', 'withdrawn', 'failed')),
  generated_subject text not null default '',
  generated_email text not null default '',
  cover_letter text not null default '',
  approved_at timestamptz,
  submitted_at timestamptz,
  submission_reference text not null default '',
  notes text not null default '',
  last_error text not null default '',
  idempotency_key text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, job_id),
  unique (user_id, idempotency_key)
);

create table public.bot_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null default '',
  role text not null default '',
  summary text not null default '',
  target_roles text[] not null default '{}',
  strengths text[] not null default '{}',
  preferred_locations text[] not null default '{}',
  remote_preference boolean not null default false,
  daily_apply_cap integer not null default 5 check (daily_apply_cap >= 1),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, id)
);

create table public.education (
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

create table public.work_experience (
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

create table public.answer_bank (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  question text not null,
  answer text not null,
  tags text[] not null default '{}',
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.application_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  application_id uuid references public.applications(id) on delete cascade,
  event_type text not null default 'note',
  details text not null default '',
  created_at timestamptz not null default now()
);

create table public.search_run_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  search_run_id uuid not null references public.search_runs(id) on delete cascade,
  level text not null default 'info' check (level in ('debug', 'info', 'warning', 'error')),
  message text not null,
  created_at timestamptz not null default now()
);

create table public.mailer_credentials (
  user_id uuid primary key references auth.users(id) on delete cascade,
  sender_email text not null,
  encrypted_app_password text not null,
  updated_at timestamptz not null default now()
);

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, coalesce(new.email, ''))
  on conflict (id) do update set email = excluded.email;

  insert into public.user_settings (user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_auth_user();

create index job_listings_posted_at_idx on public.job_listings (posted_at desc);
create index job_listings_discovered_at_idx on public.job_listings (discovered_at desc);
create index job_matches_user_status_idx on public.job_matches (user_id, status, last_seen_at desc);
create index job_matches_job_idx on public.job_matches (job_id);
create index applications_user_status_idx on public.applications (user_id, status, updated_at desc);
create index search_runs_user_created_idx on public.search_runs (user_id, created_at desc);
create index search_run_events_run_created_idx on public.search_run_events (search_run_id, created_at);

create trigger profiles_updated_at before update on public.profiles
for each row execute function public.set_updated_at();
create trigger user_settings_updated_at before update on public.user_settings
for each row execute function public.set_updated_at();
create trigger resumes_updated_at before update on public.resumes
for each row execute function public.set_updated_at();
create trigger job_listings_updated_at before update on public.job_listings
for each row execute function public.set_updated_at();
create trigger search_runs_updated_at before update on public.search_runs
for each row execute function public.set_updated_at();
create trigger applications_updated_at before update on public.applications
for each row execute function public.set_updated_at();
create trigger mailer_credentials_updated_at before update on public.mailer_credentials
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.user_settings enable row level security;
alter table public.resumes enable row level security;
alter table public.job_listings enable row level security;
alter table public.search_runs enable row level security;
alter table public.job_matches enable row level security;
alter table public.applications enable row level security;
alter table public.search_run_events enable row level security;
alter table public.mailer_credentials enable row level security;

create policy "Users manage their profile"
on public.profiles for all to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()));

create policy "Users manage their settings"
on public.user_settings for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "Users manage their resumes"
on public.resumes for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "Authenticated users can read listings"
on public.job_listings for select to authenticated
using (true);

create policy "Users manage their runs"
on public.search_runs for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "Users manage their matches"
on public.job_matches for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "Users manage their applications"
on public.applications for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "Users manage their run events"
on public.search_run_events for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "Users manage their mailer credentials"
on public.mailer_credentials for all to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('private-resumes', 'private-resumes', false, 10485760, array['application/pdf'])
on conflict (id) do nothing;

create policy "Users read own resumes"
on storage.objects for select to authenticated
using (bucket_id = 'private-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "Users upload own resumes"
on storage.objects for insert to authenticated
with check (bucket_id = 'private-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "Users update own resumes"
on storage.objects for update to authenticated
using (bucket_id = 'private-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text)
with check (bucket_id = 'private-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text);

create policy "Users delete own resumes"
on storage.objects for delete to authenticated
using (bucket_id = 'private-resumes' and (storage.foldername(name))[1] = (select auth.uid())::text);
