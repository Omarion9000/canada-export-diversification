-- M5: concentration of exports across destination countries.
-- HHI = sum of squared country shares. N_eff = 1 / HHI (the "effective number" of markets).
-- HHI ex-US uses shares within non-US exports only.

create or replace table country_variant_monthly as
select f.month, v.variant, f.country_code, c.is_us, sum(f.value_cad) as value_cad
from fact_exports f
join dim_product d using (hs6)
join dim_country c using (country_code)
cross join variants v
where v.variant in ('total', 'ex_gold_ex_energy')
  and (not v.excl_gold or not d.is_gold)
  and (not v.excl_energy or not d.is_energy)
group by all;

-- Rolling 12-month country sums. A country with no exports in a month simply adds nothing.
create or replace table country_rolling as
select m.month, c.variant, c.country_code, c.is_us, sum(c.value_cad) as x12
from dim_month m
join country_variant_monthly c
    on c.month > m.month - interval 12 month and c.month <= m.month
where m.month >= (select min(month) from dim_month) + interval 11 month
group by all;

create or replace table mart_hhi as
with shares as (
    select month, variant, country_code, is_us,
           x12 / sum(x12) over (partition by month, variant) as s_all,
           case when not is_us
                then x12 / sum(x12) filter (where not is_us) over (partition by month, variant)
           end as s_ex_us
    from country_rolling
),
rolling as (
    select 'rolling_12m' as window_type, strftime(month, '%Y-%m') as window_label, month,
           variant,
           sum(s_all * s_all) as hhi,
           1 / sum(s_all * s_all) as n_eff,
           sum(s_ex_us * s_ex_us) as hhi_ex_us,
           1 / sum(s_ex_us * s_ex_us) as n_eff_ex_us,
           max(s_all) filter (where is_us) as us_share
    from shares
    group by all
),
period_country as (
    select w.baseline as period, c.variant, c.country_code, c.is_us,
           sum(c.value_cad * w.weight) as x
    from country_variant_monthly c join baseline_weights w using (month)
    group by all
    union all
    select 'tariff', c.variant, c.country_code, c.is_us, sum(c.value_cad)
    from country_variant_monthly c join dim_month m using (month)
    where m.period_label = 'tariff'
    group by all
),
period_shares as (
    select period, variant, country_code, is_us,
           x / sum(x) over (partition by period, variant) as s_all,
           case when not is_us
                then x / sum(x) filter (where not is_us) over (partition by period, variant)
           end as s_ex_us
    from period_country
),
periods as (
    select 'period' as window_type, period as window_label, null::date as month, variant,
           sum(s_all * s_all), 1 / sum(s_all * s_all),
           sum(s_ex_us * s_ex_us), 1 / sum(s_ex_us * s_ex_us),
           max(s_all) filter (where is_us)
    from period_shares
    group by all
)
select * from rolling
union all
select * from periods
order by window_type, variant, window_label;
