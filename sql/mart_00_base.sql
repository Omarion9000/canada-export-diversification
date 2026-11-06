-- Shared helpers for the marts.

-- Export variants used across hypotheses.
create or replace table variants as
select * from (values
    ('total', false, false),
    ('ex_gold', true, false),
    ('ex_energy', false, true),
    ('ex_gold_ex_energy', true, true)
) as t(variant, excl_gold, excl_energy);

-- Baseline weights. A baseline value is the average of each calendar month over the baseline
-- years, summed over the calendar months. Front-loading months are left out, so November and
-- December are averaged over fewer years; each calendar month still counts once.
-- weight = 1 / (number of baseline months with that calendar month).
create or replace table baseline_weights as
with b as (
    select 'primary' as baseline, month, calendar_month from dim_month where in_baseline
    union all
    select 'sensitivity', month, calendar_month from dim_month where in_sensitivity_baseline
)
select baseline, month, calendar_month,
       1.0 / count(*) over (partition by baseline, calendar_month) as weight
from b;

-- Monthly exports by variant and US / rest of world, in CAD and USD.
create or replace table export_variants as
select
    f.month,
    v.variant,
    c.is_us,
    sum(f.value_cad) as value_cad,
    sum(f.value_cad / x.usdcad) as value_usd
from fact_exports f
join dim_product d using (hs6)
join dim_country c using (country_code)
join fx x using (month)
cross join variants v
where (not v.excl_gold or not d.is_gold)
  and (not v.excl_energy or not d.is_energy)
group by all;

-- Baseline (annual equivalent) and tariff-period (latest 12 months) totals.
create or replace table period_totals as
select w.baseline as period, e.variant, e.is_us,
       sum(e.value_cad * w.weight) as value_cad,
       sum(e.value_usd * w.weight) as value_usd
from export_variants e join baseline_weights w using (month)
group by all
union all
select 'tariff', e.variant, e.is_us, sum(e.value_cad), sum(e.value_usd)
from export_variants e join dim_month m using (month)
where m.period_label = 'tariff'
group by all;
