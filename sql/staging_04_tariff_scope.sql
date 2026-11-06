-- staging_tariff_scope_monthly: tariff scope of each HS6 product in each month.
--
-- tariff_scope = full    : a product-specific US measure covers every US tariff line of the
--                          HS6 code, on the full value, with no USMCA exemption.
--              = partial : a measure covers only some lines, only part of the value
--                          (metal content, non-US content), or exempts USMCA goods.
--              = none    : no product-specific measure in force in that month.
-- A measure counts in a month if it takes effect on or before the last day of that month.
-- Across-the-board measures (IEEPA, Section 122, Section 301) hit all non-USMCA goods alike,
-- so they do not separate products with and without a sector-specific tariff; not used here.

-- 1. US HTS8 lines covered by each list. HS6-level entries cover every line under the HS6;
--    HTS10 entries cover only part of an HTS8 line.
create or replace table list_line_coverage as
with entries as (
    select l.list_id, c.code, c.level
    from tariff_list_codes c join tariff_lists l using (list_id)
)
select e.list_id, h.hs6, h.hts8, max(e.level <= 8) as line_fully_listed
from entries e
join us_hts8 h
    on (e.level = 6 and h.hs6 = e.code)
    or (e.level >= 8 and h.hts8 = substr(e.code, 1, 8))
group by e.list_id, h.hs6, h.hts8;

-- HS6 codes on a list that do not exist in the current US HTS still count as partial.
create or replace table list_hs6_coverage as
with listed as (
    select distinct list_id, substr(code, 1, 6) as hs6 from tariff_list_codes
),
lines as (
    select hs6, count(*) as n_lines from us_hts8 group by hs6
)
select
    l.list_id,
    l.hs6,
    coalesce(n.n_lines, 0) as n_us_lines,
    count(c.hts8) filter (where c.line_fully_listed) as n_lines_listed,
    coalesce(n.n_lines, 0) > 0
        and count(c.hts8) filter (where c.line_fully_listed) = n.n_lines as covers_all_lines
from listed l
left join lines n using (hs6)
left join list_line_coverage c on c.list_id = l.list_id and c.hs6 = l.hs6
group by l.list_id, l.hs6, n.n_lines;

-- 2. Lists in force in each month. "cumulative" series add lines over time;
--    "replace" series (Section 338) use only the latest list in force.
create or replace table lists_in_force as
with candidates as (
    select m.month, l.*
    from dim_month m
    join tariff_lists l on l.effective_date <= last_day(m.month)
)
select month, list_id, series, value_basis, usmca_exempt
from candidates
qualify series_mode = 'cumulative'
     or effective_date = max(effective_date) over (partition by month, series);

-- 3. Measure scope by product and month.
create or replace table tariff_scope_measures as
-- List-based measures.
select
    f.month,
    c.hs6,
    f.list_id as measure_id,
    case
        when c.covers_all_lines and f.value_basis = 'full_value' and not f.usmca_exempt
            then 'full'
        else 'partial'
    end as scope
from lists_in_force f
join list_hs6_coverage c using (list_id)
union all
-- Section 232 primary steel and aluminum (Proclamations 9704, 9705): full value, from the
-- end of Canada's exemption (event E04/E05).
select m.month, d.hs6, 'S232_PRIMARY_METAL', 'full'
from dim_month m
join dim_product d on d.is_steel_primary or d.is_aluminum_primary
where last_day(m.month) >= (select event_date from tariff_events where event_id = 'E05')
union all
-- Softwood lumber AD/CVD orders: in force before the study period; company-specific rates.
select m.month, d.hs6, 'ADCVD_SOFTWOOD_LUMBER', 'partial'
from dim_month m
join dim_product d on d.is_softwood_lumber;

-- 4. Product x month table: the widest scope of any measure in force.
create or replace table staging_tariff_scope_monthly as
with grid as (
    select d.hs6, m.month from dim_product d cross join dim_month m
),
agg as (
    select
        month,
        hs6,
        max(case scope when 'full' then 2 when 'partial' then 1 else 0 end) as rank,
        string_agg(distinct measure_id, ';' order by measure_id) as measures
    from tariff_scope_measures
    group by month, hs6
)
select
    g.month,
    g.hs6,
    case coalesce(a.rank, 0) when 2 then 'full' when 1 then 'partial' else 'none' end
        as tariff_scope,
    coalesce(a.measures, '') as measures
from grid g
left join agg a using (month, hs6);
