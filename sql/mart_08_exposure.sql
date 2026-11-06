-- M8: sector exposure table (descriptive).
-- Per sector group: share of Canada's exports, US dependence (US exports / sector exports),
-- baseline vs latest 12 months, change in pp, destination HHI, and tariff scope status.

create or replace table sector_country_period as
select w.baseline as period, d.sector_group, f.country_code, c.is_us,
       sum(f.value_cad * w.weight) as x
from fact_exports f
join dim_product d using (hs6)
join dim_country c using (country_code)
join baseline_weights w using (month)
group by all
union all
select 'tariff', d.sector_group, f.country_code, c.is_us, sum(f.value_cad)
from fact_exports f
join dim_product d using (hs6)
join dim_country c using (country_code)
join dim_month m using (month)
where m.period_label = 'tariff'
group by all;

create or replace table mart_exposure as
with sector as (
    select period, sector_group,
           sum(x) as x_sector,
           sum(x) filter (where is_us) as x_us,
           sum(power(x, 2)) / power(sum(x), 2) as hhi_destinations
    from sector_country_period
    group by all
),
totals as (
    select period, sum(x_sector) as x_total from sector group by 1
),
s as (
    select s.*, s.x_sector / t.x_total as share_of_exports, s.x_us / s.x_sector as us_dependence
    from sector s join totals t using (period)
),
scope_latest as (
    -- Share of the sector's latest-12-month exports by tariff scope in the latest month.
    select d.sector_group,
           coalesce(sum(f.value_cad) filter (where sc.tariff_scope = 'full'), 0) / sum(f.value_cad)
               as share_full_scope,
           coalesce(sum(f.value_cad) filter (where sc.tariff_scope = 'partial'), 0)
               / sum(f.value_cad)
               as share_partial_scope,
           coalesce(sum(f.value_cad) filter (where sc.tariff_scope = 'none'), 0) / sum(f.value_cad)
               as share_no_scope
    from fact_exports f
    join dim_product d using (hs6)
    join dim_month m using (month)
    join staging_tariff_scope_monthly sc
        on sc.hs6 = f.hs6 and sc.month = (select max(month) from dim_month)
    where m.period_label = 'tariff'
    group by 1
)
select
    b.period as baseline,
    b.sector_group,
    b.sector_group in ('steel', 'aluminum', 'copper', 'autos', 'lumber') as is_tariffed_sector,
    b.x_sector as x_sector_base,
    t.x_sector as x_sector_latest,
    b.share_of_exports as share_of_exports_base,
    t.share_of_exports as share_of_exports_latest,
    b.us_dependence as us_dependence_base,
    t.us_dependence as us_dependence_latest,
    100 * (t.us_dependence - b.us_dependence) as us_dependence_change_pp,
    b.hhi_destinations as hhi_base,
    t.hhi_destinations as hhi_latest,
    sl.share_full_scope,
    sl.share_partial_scope,
    sl.share_no_scope
from s b
join s t on t.period = 'tariff' and t.sector_group = b.sector_group
left join scope_latest sl on sl.sector_group = b.sector_group
where b.period in ('primary', 'sensitivity')
order by b.period, b.x_sector desc;
