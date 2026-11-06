-- fact_exports: domestic exports at month x country x HS6, summed over provinces and US states.
-- HS 2710 quantities are converted from hectolitres to litres (see unit_normalization).

create or replace table fact_exports as
with rows as (
    select
        strptime(r."YearMonth/AnnéeMois", '%Y%m')::date as month,
        r."Country/Pays" as country_code,
        r.HS6 as hs6,
        r."Value/Valeur"::double as value_cad,
        r."Quantity/Quantité"::double as quantity_raw,
        r."Unit of Measure/Unité de Mesure" as unit_raw
    from raw_dom_hs6 r
),
normalized as (
    select
        r.month,
        r.country_code,
        r.hs6,
        r.value_cad,
        r.quantity_raw * coalesce(u.factor, 1) as quantity,
        coalesce(u.to_unit, r.unit_raw) as qty_unit
    from rows r
    left join unit_normalization u
        on u.hs4 = substr(r.hs6, 1, 4) and u.from_unit = r.unit_raw
)
select
    n.month,
    n.country_code,
    c.country_iso3,
    n.hs6,
    sum(n.value_cad) as value_cad,
    sum(n.quantity) as quantity,
    n.qty_unit,
    'domestic_exports' as flow,
    'StatCan CIMT' as source,
    p('cimt_vintage')::date as vintage_date
from normalized n
left join dim_country c using (country_code)
group by n.month, n.country_code, c.country_iso3, n.hs6, n.qty_unit;

-- Previous vintage (for V6). Empty when there is no earlier download.
create or replace table fact_exports_previous as
select
    strptime("YearMonth/AnnéeMois", '%Y%m')::date as month,
    "Country/Pays" as country_code,
    HS6 as hs6,
    sum("Value/Valeur"::double) as value_cad
from raw_dom_hs6_previous
group by all;

-- Total exports (domestic + re-exports) by month x country, used only for V1a.
create or replace table ref_cimt_total_exports as
select
    strptime("YearMonth/AnnéeMois", '%Y%m')::date as month,
    "Country/Pays" as country_code,
    sum("Value/Valeur"::double) as value_cad
from raw_tot_hs2
group by all;
