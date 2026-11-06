-- M2: log decomposition of the change in the US share (H1).
--
-- Approximation (base-period weights): d ln s_US ~ w_R * d ln X_US - w_R * d ln X_R,
--   where w_R = 1 - s_US in the baseline.
--   US-side = w_R * d ln X_US;  RoW-side = - w_R * d ln X_R.
-- Exact form (log-mean weights): the same formula with w_R replaced by the logarithmic mean
--   of the before and after rest-of-world shares, normalized. It adds up exactly.
-- The approximation is used unless its residual exceeds the frozen share of the total.

create or replace macro logmean(a, b) as
    case when abs(a - b) < 1e-12 then a else (a - b) / (ln(a) - ln(b)) end;

create or replace table mart_decomposition as
with t as (
    select
        b.period as baseline,
        b.variant,
        max(b.value_cad) filter (where b.is_us) as x_us_base,
        max(b.value_cad) filter (where not b.is_us) as x_row_base,
        max(t.value_cad) filter (where t.is_us) as x_us_tariff,
        max(t.value_cad) filter (where not t.is_us) as x_row_tariff
    from period_totals b
    join period_totals t on t.period = 'tariff' and t.variant = b.variant and t.is_us = b.is_us
    where b.period in ('primary', 'sensitivity')
    group by all
),
s as (
    select
        *,
        x_us_base / (x_us_base + x_row_base) as s_us_base,
        x_us_tariff / (x_us_tariff + x_row_tariff) as s_us_tariff,
        ln(x_us_tariff / x_us_base) as dln_x_us,
        ln(x_row_tariff / x_row_base) as dln_x_row
    from t
),
w as (
    select
        *,
        1 - s_us_base as w_row_base,
        logmean(1 - s_us_tariff, 1 - s_us_base)
            / (logmean(1 - s_us_tariff, 1 - s_us_base) + logmean(s_us_tariff, s_us_base))
            as w_row_logmean
    from s
)
select
    baseline,
    variant,
    x_us_base, x_row_base, x_us_tariff, x_row_tariff,
    s_us_base, s_us_tariff,
    100 * (s_us_tariff - s_us_base) as d_share_pp,
    dln_x_us, dln_x_row,
    ln(s_us_tariff / s_us_base) as dln_s_us,
    w_row_base,
    w_row_base * dln_x_us as us_side_approx,
    -w_row_base * dln_x_row as row_side_approx,
    w_row_base * (dln_x_us - dln_x_row) as total_approx,
    ln(s_us_tariff / s_us_base) - w_row_base * (dln_x_us - dln_x_row) as approx_residual,
    abs(ln(s_us_tariff / s_us_base) - w_row_base * (dln_x_us - dln_x_row))
        / abs(ln(s_us_tariff / s_us_base)) as approx_residual_share,
    w_row_logmean,
    w_row_logmean * dln_x_us as us_side_exact,
    -w_row_logmean * dln_x_row as row_side_exact,
    case when abs(ln(s_us_tariff / s_us_base) - w_row_base * (dln_x_us - dln_x_row))
              / abs(ln(s_us_tariff / s_us_base)) > p('m2_max_residual_share')::double
         then 'exact' else 'approximation' end as method_used
from w
order by baseline, variant;
