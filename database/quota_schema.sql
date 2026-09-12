-- Persistent, atomic limits for the public OpenAI portfolio analysis.
-- Run this file once in a dedicated Supabase project's SQL editor.

create table if not exists public.analysis_user_usage (
    user_key text primary key,
    attempt_count integer not null default 0 check (attempt_count >= 0),
    updated_at timestamptz not null default now(),
    check (user_key ~ '^[a-f0-9]{64}$')
);

create table if not exists public.analysis_daily_usage (
    usage_date date primary key,
    attempt_count integer not null default 0 check (attempt_count >= 0),
    updated_at timestamptz not null default now()
);

create table if not exists public.analysis_global_usage (
    counter_key text primary key,
    attempt_count integer not null default 0 check (attempt_count >= 0),
    updated_at timestamptz not null default now(),
    check (counter_key = 'all_time')
);

alter table public.analysis_user_usage enable row level security;
alter table public.analysis_daily_usage enable row level security;
alter table public.analysis_global_usage enable row level security;

revoke all on table public.analysis_user_usage from public, anon, authenticated;
revoke all on table public.analysis_daily_usage from public, anon, authenticated;
revoke all on table public.analysis_global_usage from public, anon, authenticated;


create or replace function public.read_public_analysis_quota(
    p_user_key text,
    p_user_limit integer,
    p_daily_limit integer,
    p_total_limit integer
)
returns table (
    allowed boolean,
    user_used integer,
    daily_used integer,
    total_used integer,
    usage_date date,
    denial_reason text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_usage_date date := (now() at time zone 'utc')::date;
    v_user_used integer := 0;
    v_daily_used integer := 0;
    v_total_used integer := 0;
    v_denial_reason text := null;
begin
    if p_user_key !~ '^[a-f0-9]{64}$' then
        raise exception 'Invalid user key';
    end if;

    if p_user_limit < 1 or p_user_limit > 10
       or p_daily_limit < 1 or p_daily_limit > 1000
       or p_total_limit < 1 or p_total_limit > 100000
       or p_user_limit > p_total_limit
       or p_daily_limit > p_total_limit then
        raise exception 'Invalid quota limits';
    end if;

    select coalesce(u.attempt_count, 0)
      into v_user_used
      from public.analysis_user_usage as u
     where u.user_key = p_user_key;

    select coalesce(d.attempt_count, 0)
      into v_daily_used
      from public.analysis_daily_usage as d
     where d.usage_date = v_usage_date;

    select coalesce(g.attempt_count, 0)
      into v_total_used
      from public.analysis_global_usage as g
     where g.counter_key = 'all_time';

    v_user_used := coalesce(v_user_used, 0);
    v_daily_used := coalesce(v_daily_used, 0);
    v_total_used := coalesce(v_total_used, 0);

    if v_total_used >= p_total_limit then
        v_denial_reason := 'total_limit';
    elsif v_daily_used >= p_daily_limit then
        v_denial_reason := 'daily_limit';
    elsif v_user_used >= p_user_limit then
        v_denial_reason := 'user_limit';
    end if;

    return query
    select
        v_denial_reason is null,
        v_user_used,
        v_daily_used,
        v_total_used,
        v_usage_date,
        v_denial_reason;
end;
$$;


create or replace function public.reserve_public_analysis(
    p_user_key text,
    p_user_limit integer,
    p_daily_limit integer,
    p_total_limit integer
)
returns table (
    allowed boolean,
    user_used integer,
    daily_used integer,
    total_used integer,
    usage_date date,
    denial_reason text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_usage_date date := (now() at time zone 'utc')::date;
    v_user_used integer;
    v_daily_used integer;
    v_total_used integer;
    v_denial_reason text := null;
begin
    if p_user_key !~ '^[a-f0-9]{64}$' then
        raise exception 'Invalid user key';
    end if;

    if p_user_limit < 1 or p_user_limit > 10
       or p_daily_limit < 1 or p_daily_limit > 1000
       or p_total_limit < 1 or p_total_limit > 100000
       or p_user_limit > p_total_limit
       or p_daily_limit > p_total_limit then
        raise exception 'Invalid quota limits';
    end if;

    -- Every caller takes locks in the same global -> daily -> user order.
    insert into public.analysis_global_usage (counter_key)
    values ('all_time')
    on conflict do nothing;

    select g.attempt_count
      into v_total_used
      from public.analysis_global_usage as g
     where g.counter_key = 'all_time'
       for update;

    insert into public.analysis_daily_usage (usage_date)
    values (v_usage_date)
    -- Do not name usage_date in the conflict target: usage_date is also an
    -- output parameter of this RETURNS TABLE function.
    on conflict do nothing;

    select d.attempt_count
      into v_daily_used
      from public.analysis_daily_usage as d
     where d.usage_date = v_usage_date
       for update;

    insert into public.analysis_user_usage (user_key)
    values (p_user_key)
    on conflict do nothing;

    select u.attempt_count
      into v_user_used
      from public.analysis_user_usage as u
     where u.user_key = p_user_key
       for update;

    if v_total_used >= p_total_limit then
        v_denial_reason := 'total_limit';
    elsif v_daily_used >= p_daily_limit then
        v_denial_reason := 'daily_limit';
    elsif v_user_used >= p_user_limit then
        v_denial_reason := 'user_limit';
    else
        update public.analysis_global_usage as g
           set attempt_count = g.attempt_count + 1,
               updated_at = now()
         where g.counter_key = 'all_time';

        update public.analysis_daily_usage as d
           set attempt_count = d.attempt_count + 1,
               updated_at = now()
         where d.usage_date = v_usage_date;

        update public.analysis_user_usage as u
           set attempt_count = u.attempt_count + 1,
               updated_at = now()
         where u.user_key = p_user_key;

        v_total_used := v_total_used + 1;
        v_daily_used := v_daily_used + 1;
        v_user_used := v_user_used + 1;
    end if;

    return query
    select
        v_denial_reason is null,
        v_user_used,
        v_daily_used,
        v_total_used,
        v_usage_date,
        v_denial_reason;
end;
$$;


revoke execute on function public.read_public_analysis_quota(
    text,
    integer,
    integer,
    integer
) from public, anon, authenticated;

revoke execute on function public.reserve_public_analysis(
    text,
    integer,
    integer,
    integer
) from public, anon, authenticated;

grant execute on function public.read_public_analysis_quota(
    text,
    integer,
    integer,
    integer
) to service_role;

grant execute on function public.reserve_public_analysis(
    text,
    integer,
    integer,
    integer
) to service_role;
