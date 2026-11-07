-- Dimensions: months, countries, products.

-- dim_month: one row per month from the first month to the latest month in the data.
-- period_label: baseline | frontload | transition | tariff.
create or replace table dim_month as
with bounds as (
    select
        p('first_month')::date as first_month,
        max(strptime("YearMonth/AnnéeMois", '%Y%m'))::date as latest_month
    from raw_dom_hs6
),
months as (
    select unnest(generate_series(first_month, latest_month, interval 1 month))::date as month,
           latest_month
    from bounds
)
select
    month,
    strftime(month, '%Y-%m') as month_label,
    month(month) as calendar_month,
    case
        when month between p('frontload_start')::date and p('frontload_end')::date then 'frontload'
        when month between p('baseline_start')::date and p('baseline_end')::date then 'baseline'
        when month > latest_month - interval 12 month then 'tariff'
        else 'transition'
    end as period_label,
    (month between p('sens_baseline_start')::date and p('sens_baseline_end')::date
        and not month between p('frontload_start')::date and p('frontload_end')::date)
        as in_sensitivity_baseline,
    (month between p('baseline_start')::date and p('baseline_end')::date
        and not month between p('frontload_start')::date and p('frontload_end')::date)
        as in_baseline,
    month = latest_month as is_latest
from months;

-- dim_country: every destination code that appears in the CIMT files.
create or replace table dim_country as
with codes as (
    select distinct "Country/Pays" as country_code from raw_dom_hs6
    union
    select distinct "Country/Pays" from raw_tot_hs2
),
names as (
    -- Latest name for each code (open-ended rows end in 999912).
    select code, name
    from raw_country_desc
    qualify row_number() over (partition by code order by end_yyyymm desc, start_yyyymm desc) = 1
)
select
    c.country_code,
    m.iso3 as country_iso3,
    n.name,
    case
        when c.country_code = 'US' then 'United States'
        when eu.iso2 is not null then 'European Union'
        when c.country_code = 'GB' then 'United Kingdom'
        when c.country_code = 'CN' then 'China'
        when c.country_code = 'JP' then 'Japan'
        when c.country_code = 'MX' then 'Mexico'
        when c.country_code = 'KR' then 'South Korea'
        else 'Rest of world'
    end as ptp_group,
    c.country_code = 'US' as is_us
from codes c
left join names n on n.code = c.country_code
left join ref_country_codes m on m.iso2 = c.country_code
left join ref_eu_members eu on eu.iso2 = c.country_code;

-- HS6 codes that appear on any official list, by list sector.
create or replace table list_hs6 as
select distinct l.sector_group, l.list_id, substr(c.code, 1, 6) as hs6
from tariff_list_codes c
join tariff_lists l using (list_id);

-- dim_product: every HS6 code in the data, with sector group and flags.
create or replace table dim_product as
with codes as (
    select distinct HS6 as hs6 from raw_dom_hs6
),
descriptions as (
    select code as hs6, description, unit as default_unit
    from raw_hs6_desc
    qualify row_number() over (partition by code order by end_yyyymm desc, start_yyyymm desc) = 1
),
hs2_names as (
    -- StatCan HS2 chapter names (ODPF_5_HS2Desc), latest version of each chapter.
    select code as hs2, name as hs2_description
    from raw_hs2_desc
    qualify row_number() over (partition by code order by end_yyyymm desc, start_yyyymm desc) = 1
),
rule_hits as (
    select c.hs6, r.sector_group, r.role
    from codes c
    join hs_rules r on (
        (r.level = 6 and c.hs6 between r.lo and r.hi)
        or (r.level = 4 and substr(c.hs6, 1, 4) between r.lo and r.hi)
        or (r.level = 2 and substr(c.hs6, 1, 2) between r.lo and r.hi)
    )
),
classified as (
    select
        c.hs6,
        exists (select 1 from flag_codes f where f.flag = 'gold'
                and substr(c.hs6, 1, f.level) = f.code) as is_gold,
        exists (select 1 from flag_codes f where f.flag = 'energy'
                and substr(c.hs6, 1, f.level) = f.code) as is_energy,
        exists (select 1 from flag_codes f where f.flag = 'crude'
                and substr(c.hs6, 1, f.level) = f.code) as is_crude,
        exists (select 1 from rule_hits h where h.hs6 = c.hs6 and h.role = 'other') as forced_other,
        (select min(h.sector_group) from rule_hits h
          where h.hs6 = c.hs6 and h.role in ('primary', 'member')) as metal_sector,
        exists (select 1 from rule_hits h where h.hs6 = c.hs6 and h.sector_group = 'steel'
                and h.role = 'primary') as is_steel_primary,
        exists (select 1 from rule_hits h where h.hs6 = c.hs6 and h.sector_group = 'aluminum'
                and h.role = 'primary') as is_aluminum_primary,
        exists (select 1 from rule_hits h where h.hs6 = c.hs6 and h.role = 'candidate')
            and exists (select 1 from list_hs6 l where l.hs6 = c.hs6 and l.sector_group = 'autos')
            as is_auto,
        substr(c.hs6, 1, 2) = '44' and (
            exists (select 1 from list_hs6 l where l.hs6 = c.hs6 and l.sector_group = 'lumber')
            or (exists (select 1 from rule_hits h where h.hs6 = c.hs6 and h.role = 'softwood')
                and substr(c.hs6, 5, 1) = '1')
        ) as is_lumber,
        exists (select 1 from rule_hits h where h.hs6 = c.hs6 and h.role = 'softwood')
            and substr(c.hs6, 5, 1) = '1' as is_softwood_lumber
    from codes c
)
select
    c.hs6,
    substr(c.hs6, 1, 4) as hs4,
    substr(c.hs6, 1, 2) as hs2,
    d.description,
    n.hs2_description,
    d.default_unit,
    case
        when c.is_gold then 'gold'
        when c.is_energy then 'energy'
        when c.forced_other then 'other'
        when c.metal_sector is not null then c.metal_sector
        when c.is_auto then 'autos'
        when c.is_lumber then 'lumber'
        else 'other'
    end as sector_group,
    c.is_gold,
    c.is_energy,
    c.is_crude,
    c.is_steel_primary,
    c.is_aluminum_primary,
    c.is_softwood_lumber
from classified c
left join descriptions d using (hs6)
left join hs2_names n on n.hs2 = substr(c.hs6, 1, 2);

select case when count(*) > 0 then error('HS2 chapters without a StatCan name: '
                                         || string_agg(distinct hs2, ', ')) end
from dim_product where hs2_description is null;

alter table dim_product add column is_tariffed boolean;
update dim_product
set is_tariffed = sector_group in ('steel', 'aluminum', 'copper', 'autos', 'lumber');
