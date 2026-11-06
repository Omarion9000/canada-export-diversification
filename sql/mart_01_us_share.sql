-- M1: US share of domestic exports, rolling 12-month sums, by variant.
-- Monthly levels come with year-over-year changes only (the data are not seasonally adjusted).

create or replace table mart_us_share as
with wide as (
    select
        month,
        variant,
        sum(value_cad) filter (where is_us) as x_us,
        sum(value_cad) filter (where not is_us) as x_row,
        sum(value_usd) filter (where is_us) as x_us_usd,
        sum(value_usd) filter (where not is_us) as x_row_usd
    from export_variants
    group by all
),
rolled as (
    select
        *,
        sum(x_us) over w as x_us_12m,
        sum(x_row) over w as x_row_12m,
        sum(x_us_usd) over w as x_us_12m_usd,
        sum(x_row_usd) over w as x_row_12m_usd,
        count(*) over w as n_months,
        lag(x_us, 12) over (partition by variant order by month) as x_us_prev_year,
        lag(x_row, 12) over (partition by variant order by month) as x_row_prev_year
    from wide
    window w as (partition by variant order by month rows between 11 preceding and current row)
)
select
    r.month,
    m.period_label,
    r.variant,
    r.x_us,
    r.x_row,
    r.x_us / r.x_us_prev_year - 1 as x_us_yoy,
    r.x_row / r.x_row_prev_year - 1 as x_row_yoy,
    case when r.n_months = 12 then r.x_us_12m end as x_us_12m,
    case when r.n_months = 12 then r.x_row_12m end as x_row_12m,
    case when r.n_months = 12 then r.x_us_12m / (r.x_us_12m + r.x_row_12m) end as us_share_12m,
    case when r.n_months = 12 then r.x_us_12m_usd end as x_us_12m_usd,
    case when r.n_months = 12 then r.x_row_12m_usd end as x_row_12m_usd,
    case when r.n_months = 12
         then r.x_us_12m_usd / (r.x_us_12m_usd + r.x_row_12m_usd) end as us_share_12m_usd
from rolled r
join dim_month m using (month)
order by r.variant, r.month;
