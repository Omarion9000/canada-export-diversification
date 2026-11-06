-- M6: redirection test for tariffed sectors (H3).
-- Offset ratio OR = change in non-US exports / |change in US exports|, only when US exports fell.
--
-- Each sector's tariff window starts at the first full month on or after its own first event.
-- If at least 12 months are available, the window is the latest 12 months; otherwise it is
-- every month from the start (lumber). The baseline for a window is the baseline average of
-- the same calendar months (see baseline_weights), so seasons match.
-- Comparison group "no sector-specific tariff": products outside the five tariffed sectors
-- whose tariff scope is "none" in that month (staging_tariff_scope_monthly), built month by
-- month. Non-USMCA goods in this group still paid across-the-board duties (IEEPA, March 2025
-- to February 2026; later Section 122 and Section 301), which tariff_scope does not track.
-- Percent changes toward the US and the rest of the world are reported next to the ratios.

create or replace table sector_windows as
with starts as (
    select sector_group,
           case when day(event_date) = 1 then event_date
                else date_trunc('month', event_date) + interval 1 month end::date as start_month
    from h3_sector_start
),
latest as (select max(month) as latest_month from dim_month)
select s.sector_group, s.start_month,
       case when datediff('month', s.start_month, l.latest_month) + 1 >= 12
            then (l.latest_month - interval 11 month)::date
            else s.start_month end as window_start,
       l.latest_month as window_end
from starts s, latest l;

create or replace table window_months as
select w.sector_group, m.month, m.calendar_month
from sector_windows w
join dim_month m on m.month between w.window_start and w.window_end;

-- Baseline equivalent of a window: for each window month, the weighted baseline months with
-- the same calendar month.
create or replace table window_baseline_weights as
select wm.sector_group, bw.baseline, bw.month, bw.weight
from window_months wm
join baseline_weights bw on bw.calendar_month = wm.calendar_month;

create or replace table sector_flows as
select f.month, d.sector_group, d.hs4, d.hs6, c.is_us, sum(f.value_cad) as value_cad
from fact_exports f
join dim_product d using (hs6)
join dim_country c using (country_code)
where d.is_tariffed
group by all;

create or replace table mart_redirection as
with levels as (
    select 'sector' as level, sector_group, sector_group as code, month, is_us, value_cad
    from sector_flows
    union all
    select 'hs4', sector_group, hs4, month, is_us, value_cad from sector_flows
    union all
    select 'hs6', sector_group, hs6, month, is_us, value_cad from sector_flows
),
tariff as (
    select l.level, l.sector_group, l.code,
           sum(l.value_cad) filter (where l.is_us) as x_us_tariff,
           sum(l.value_cad) filter (where not l.is_us) as x_nonus_tariff
    from levels l
    join window_months wm on wm.sector_group = l.sector_group and wm.month = l.month
    group by all
),
base as (
    select w.baseline, l.level, l.sector_group, l.code,
           sum(l.value_cad * w.weight) filter (where l.is_us) as x_us_base,
           sum(l.value_cad * w.weight) filter (where not l.is_us) as x_nonus_base
    from levels l
    join window_baseline_weights w on w.sector_group = l.sector_group and w.month = l.month
    group by all
),
joined as (
    select b.baseline, b.level, b.sector_group, b.code,
           coalesce(b.x_us_base, 0) as x_us_base,
           coalesce(t.x_us_tariff, 0) as x_us_tariff,
           coalesce(b.x_nonus_base, 0) as x_nonus_base,
           coalesce(t.x_nonus_tariff, 0) as x_nonus_tariff
    from base b
    left join tariff t using (level, sector_group, code)
)
select
    j.baseline, j.level, j.sector_group, j.code, w.window_start, w.window_end,
    datediff('month', w.window_start, w.window_end) + 1 as n_months,
    j.x_us_base, j.x_us_tariff, j.x_nonus_base, j.x_nonus_tariff,
    j.x_us_tariff - j.x_us_base as d_us,
    j.x_nonus_tariff - j.x_nonus_base as d_nonus,
    j.x_us_tariff / nullif(j.x_us_base, 0) - 1 as d_us_pct,
    j.x_nonus_tariff / nullif(j.x_nonus_base, 0) - 1 as d_nonus_pct,
    case when j.x_us_tariff - j.x_us_base < 0
         then (j.x_nonus_tariff - j.x_nonus_base) / abs(j.x_us_tariff - j.x_us_base)
    end as offset_ratio
from joined j
join sector_windows w using (sector_group)
order by baseline, level, sector_group, code;

-- Comparison group for each sector window: no sector-specific tariff, month by month.
create or replace table mart_redirection_no_sector_tariff as
with eligible as (
    -- Product-months with no product-specific measure, outside the five sectors.
    select s.month, s.hs6
    from staging_tariff_scope_monthly s
    join dim_product d using (hs6)
    where s.tariff_scope = 'none' and not d.is_tariffed
),
flows as (
    select f.month, f.hs6, d.is_gold, d.is_energy, c.is_us, sum(f.value_cad) as value_cad
    from fact_exports f
    join dim_product d using (hs6)
    join dim_country c using (country_code)
    where not d.is_tariffed
    group by all
),
variants_b as (
    select * from (values ('all', false), ('ex_gold_ex_energy', true))
        as t(group_variant, excl_gold_energy)
),
tariff as (
    select wm.sector_group, v.group_variant,
           sum(f.value_cad) filter (where f.is_us) as x_us_tariff,
           sum(f.value_cad) filter (where not f.is_us) as x_nonus_tariff
    from window_months wm
    join eligible e on e.month = wm.month
    join flows f on f.month = wm.month and f.hs6 = e.hs6
    cross join variants_b v
    where not v.excl_gold_energy or not (f.is_gold or f.is_energy)
    group by all
),
base as (
    -- Same eligible products as in each window month, valued at the baseline average of
    -- that calendar month.
    select wm.sector_group, bw.baseline, v.group_variant,
           sum(f.value_cad * bw.weight) filter (where f.is_us) as x_us_base,
           sum(f.value_cad * bw.weight) filter (where not f.is_us) as x_nonus_base
    from window_months wm
    join eligible e on e.month = wm.month
    join baseline_weights bw on bw.calendar_month = wm.calendar_month
    join flows f on f.month = bw.month and f.hs6 = e.hs6
    cross join variants_b v
    where not v.excl_gold_energy or not (f.is_gold or f.is_energy)
    group by all
)
select
    b.baseline, b.sector_group as window_of_sector, b.group_variant,
    w.window_start, w.window_end,
    b.x_us_base, t.x_us_tariff, b.x_nonus_base, t.x_nonus_tariff,
    t.x_us_tariff - b.x_us_base as d_us,
    t.x_nonus_tariff - b.x_nonus_base as d_nonus,
    t.x_us_tariff / b.x_us_base - 1 as d_us_pct,
    t.x_nonus_tariff / b.x_nonus_base - 1 as d_nonus_pct,
    case when t.x_us_tariff - b.x_us_base < 0
         then (t.x_nonus_tariff - b.x_nonus_base) / abs(t.x_us_tariff - b.x_us_base)
    end as offset_ratio
from base b
join tariff t using (sector_group, group_variant)
join sector_windows w using (sector_group)
order by b.baseline, b.sector_group, b.group_variant;
