-- M3: waterfall of the US share change in percentage points (H2).
-- Order 1 removes gold first, then energy. Order 2 removes energy first, then gold.
-- The reported effect of each item is the average of the two orders.

create or replace table mart_waterfall as
with shares as (
    select
        b.period as baseline,
        b.variant,
        max(b.value_cad) filter (where b.is_us)
            / sum(b.value_cad) as s_base,
        max(t.value_cad) filter (where t.is_us)
            / sum(t.value_cad) as s_tariff
    from period_totals b
    join period_totals t on t.period = 'tariff' and t.variant = b.variant and t.is_us = b.is_us
    where b.period in ('primary', 'sensitivity')
    group by all
),
d as (
    select baseline,
           max(100 * (s_tariff - s_base)) filter (where variant = 'total') as d_total,
           max(100 * (s_tariff - s_base)) filter (where variant = 'ex_gold') as d_ex_gold,
           max(100 * (s_tariff - s_base)) filter (where variant = 'ex_energy') as d_ex_energy,
           max(100 * (s_tariff - s_base)) filter (where variant = 'ex_gold_ex_energy') as d_ex_both,
           max(100 * s_base) filter (where variant = 'total') as s_total_base_pct,
           max(100 * s_tariff) filter (where variant = 'total') as s_total_tariff_pct
    from shares group by 1
)
select baseline, 1 as step, 'Gold' as component,
       d_total - d_ex_gold as order_gold_first,
       d_ex_energy - d_ex_both as order_energy_first,
       ((d_total - d_ex_gold) + (d_ex_energy - d_ex_both)) / 2 as effect_pp,
       s_total_base_pct, s_total_tariff_pct
from d
union all
select baseline, 2, 'Energy',
       d_ex_gold - d_ex_both,
       d_total - d_ex_energy,
       ((d_ex_gold - d_ex_both) + (d_total - d_ex_energy)) / 2,
       s_total_base_pct, s_total_tariff_pct
from d
union all
select baseline, 3, 'Everything else (ex-gold-ex-energy)',
       d_ex_both, d_ex_both, d_ex_both,
       s_total_base_pct, s_total_tariff_pct
from d
union all
select baseline, 0, 'Total change (headline)',
       d_total, d_total, d_total,
       s_total_base_pct, s_total_tariff_pct
from d
order by baseline, step;
