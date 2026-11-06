-- M4: price vs volume for gold (HS 7108) and crude oil (HS 2709).
-- Unit value P = value / quantity. Midpoint split: dV = dP * mean(Q) + dQ * mean(P).
-- Benchmarks: World Bank Pink Sheet prices converted to CAD with the Bank of Canada rate.
-- Unit constants (exact by definition): 1 troy ounce = 31.1034768 g; 1 barrel = 0.158987294928 m3.

create or replace table commodity_monthly as
select
    f.month,
    case when d.is_gold then 'gold' else 'crude' end as commodity,
    case when c.is_us then 'United States' else 'Non-US' end as destination,
    sum(f.value_cad) as value_cad,
    sum(f.quantity) as quantity,
    any_value(f.qty_unit) as qty_unit,
    count(distinct f.qty_unit) as n_units
from fact_exports f
join dim_product d using (hs6)
join dim_country c using (country_code)
where d.is_gold or d.is_crude
group by all;

-- Totals across destinations.
insert into commodity_monthly
select month, commodity, 'All destinations', sum(value_cad), sum(quantity),
       any_value(qty_unit), max(n_units)
from commodity_monthly
group by month, commodity;

create or replace table mart_price_volume_monthly as
select
    c.month,
    c.commodity,
    c.destination,
    c.value_cad,
    c.quantity,
    c.qty_unit,
    c.value_cad / nullif(c.quantity, 0) as unit_value_cad,
    case c.commodity
        when 'gold' then g.value * x.usdcad / 31.1034768
        when 'crude' then o.value * x.usdcad / 0.158987294928
    end as benchmark_cad_per_unit,
    x.usdcad
from commodity_monthly c
join fx x using (month)
left join prices g on g.month = c.month and g.series = 'gold_usd_per_troy_oz'
left join prices o on o.month = c.month and o.series = 'crude_avg_usd_per_bbl'
order by commodity, destination, month;

create or replace table mart_price_volume as
with periods as (
    select w.baseline as period, c.commodity, c.destination,
           sum(c.value_cad * w.weight) as v, sum(c.quantity * w.weight) as q
    from commodity_monthly c join baseline_weights w using (month)
    group by all
    union all
    select 'tariff', c.commodity, c.destination, sum(c.value_cad), sum(c.quantity)
    from commodity_monthly c join dim_month m using (month)
    where m.period_label = 'tariff'
    group by all
),
pairs as (
    select b.period as baseline, b.commodity, b.destination,
           b.v as v_base, b.q as q_base, b.v / b.q as p_base,
           t.v as v_tariff, t.q as q_tariff, t.v / t.q as p_tariff
    from periods b
    join periods t on t.period = 'tariff' and t.commodity = b.commodity
                  and t.destination = b.destination
    where b.period in ('primary', 'sensitivity')
)
select
    *,
    v_tariff - v_base as d_value,
    (p_tariff - p_base) * (q_tariff + q_base) / 2 as price_effect,
    (q_tariff - q_base) * (p_tariff + p_base) / 2 as volume_effect
from pairs
order by baseline, commodity, destination;
