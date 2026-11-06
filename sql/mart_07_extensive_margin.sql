-- M7: extensive margin (H4). Rule frozen 2026-11-06 (config/settings.yaml, m7).
-- A pair (HS6 x non-US country) is new at a snapshot month when:
--   1. its rolling 12-month sum that ended 12 months earlier is below the prior threshold, and
--   2. its rolling 12-month sum is above the current threshold at the snapshot month and at
--      the (sustain - 1) month-ends before it.
-- Snapshots: the frozen baseline snapshots, plus the latest month (tariff period).

-- The 3-month sustain window below is written as "2 preceding"; stop if the setting changes.
select case when p('m7_sustain')::int <> 3
            then error('m7.sustain_month_ends changed: update the window in mart_07') end;

create or replace table pair_monthly as
select f.month, f.hs6, f.country_code, sum(f.value_cad) as value_cad
from fact_exports f
join dim_country c using (country_code)
where not c.is_us
group by all;

-- Full pair x month grid so months without exports count as zero.
create or replace table pair_rolling as
with pairs as (select distinct hs6, country_code from pair_monthly),
grid as (
    select p.hs6, p.country_code, m.month, coalesce(x.value_cad, 0) as value_cad
    from pairs p
    cross join dim_month m
    left join pair_monthly x using (hs6, country_code, month)
),
r as (
    select hs6, country_code, month,
           sum(value_cad) over w12 as r12,
           count(*) over w12 as n12
    from grid
    window w12 as (partition by hs6, country_code order by month
                   rows between 11 preceding and current row)
)
select hs6, country_code, month, r12, n12,
       lag(r12, 12) over w as prior_r12,
       lag(n12, 12) over w as prior_n12,
       min(r12) over (partition by hs6, country_code order by month
                      rows between 2 preceding and current row) as min_r12_last3,
       count(*) over (partition by hs6, country_code order by month
                      rows between 2 preceding and current row) as n_last3
from r
window w as (partition by hs6, country_code order by month);

create or replace table m7_snapshot_list as
select snapshot, role from m7_snapshots
union all
select max(month), 'tariff' from dim_month;

create or replace table mart_extensive_margin_pairs as
select
    s.snapshot, s.role, r.hs6, r.country_code, d.is_gold, d.is_energy,
    r.prior_r12, r.r12, r.min_r12_last3
from pair_rolling r
join m7_snapshot_list s on s.snapshot = r.month
join dim_product d using (hs6)
where r.n12 = 12 and r.prior_n12 = 12
  and r.prior_r12 < p('m7_prior_max')::double
  and r.n_last3 = p('m7_sustain')::int
  and r.min_r12_last3 > p('m7_current_min')::double;

create or replace table mart_extensive_margin as
with v as (
    select * from (values ('total', false, false), ('ex_gold', true, false),
                          ('ex_gold_ex_energy', true, true)) as t(variant, excl_gold, excl_energy)
)
select s.snapshot, s.role, v.variant,
       count(p.hs6) filter (where (not v.excl_gold or not p.is_gold)
                              and (not v.excl_energy or not p.is_energy)) as n_new_pairs
from m7_snapshot_list s
cross join v
left join mart_extensive_margin_pairs p on p.snapshot = s.snapshot
group by all
order by v.variant, s.snapshot;

-- Front-loading check: non-US exports Nov 2024-Feb 2025 vs Nov 2023-Feb 2024.
-- If the prior window of the latest snapshot is inflated by front-loading, fewer pairs look
-- new, which biases the H4 test toward confirmation.
create or replace table mart_frontload_check as
with v as (
    select * from (values ('total', false, false), ('ex_gold_ex_energy', true, true))
        as t(variant, excl_gold, excl_energy)
),
x as (
    select v.variant,
           case when c.is_us then 'United States' else 'Non-US' end as destination,
           sum(f.value_cad) filter (where f.month between p('frontload_start')::date
                                                       and p('frontload_end')::date) as frontload,
           sum(f.value_cad) filter (where f.month between p('frontload_start')::date
                                                           - interval 12 month
                                                       and p('frontload_end')::date
                                                           - interval 12 month) as year_before
    from fact_exports f
    join dim_product d using (hs6)
    join dim_country c using (country_code)
    cross join v
    where (not v.excl_gold or not d.is_gold) and (not v.excl_energy or not d.is_energy)
    group by all
)
select variant, destination, year_before, frontload, frontload / year_before - 1 as change_pct
from x
order by variant, destination;
