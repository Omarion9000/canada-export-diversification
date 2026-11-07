"""Exports marts and dimensions to CSV (data/processed/csv/) for Excel and Tableau.

Only marts defined in the current sql/mart_*.sql files are exported, so a table left in the
database by an older version of the SQL is never published.
"""

import re

from src.build import connect
from src.common import CSV_OUT, SQL_DIR, PipelineError

EXTRA_TABLES = ["dim_country", "dim_product", "dim_month", "tariff_events"]

# Tableau-ready waterfall: five bars per baseline, values in % (76.2, not 0.762).
# value_pp = bar_end - bar_start for every bar. Components come from mart_waterfall.
TABLEAU_WATERFALL = """
with steps as (
    select baseline, step, effect_pp, s_total_base_pct, s_total_tariff_pct,
           case step when 1 then 'Gold' when 2 then 'Energy' when 3 then 'Everything else' end
               as label
    from mart_waterfall
    where step in (1, 2, 3)
),
moves as (
    select baseline, step + 1 as bar_order, label,
           s_total_base_pct + coalesce(sum(effect_pp) over (
               partition by baseline order by step
               rows between unbounded preceding and 1 preceding), 0) as bar_start,
           s_total_base_pct + sum(effect_pp) over (
               partition by baseline order by step rows unbounded preceding) as bar_end,
           case when effect_pp < 0 then 'decrease' else 'increase' end as kind
    from steps
),
levels as (
    select distinct baseline, 1 as bar_order, 'US share, baseline' as label,
           0.0 as bar_start, s_total_base_pct as bar_end, 'level' as kind
    from mart_waterfall
    union all
    select distinct baseline, 5, 'US share, latest 12 months', 0.0, s_total_tariff_pct, 'level'
    from mart_waterfall
)
select baseline, bar_order, label, bar_start, bar_end, bar_end - bar_start as value_pp, kind
from (select * from levels union all select * from moves)
order by baseline, bar_order
"""


def tableau_waterfall(con) -> None:
    rows = con.execute(TABLEAU_WATERFALL).fetchall()
    by = {}
    for baseline, order, *_rest in rows:
        by.setdefault(baseline, []).append(order)
    if not by or any(orders != [1, 2, 3, 4, 5] for orders in by.values()):
        raise PipelineError(f"tableau_waterfall: expected bars 1-5 per baseline, got {by}")
    # The last movement must land on the latest share.
    for baseline in by:
        ends = {r[1]: r[4] for r in rows if r[0] == baseline}
        if abs(ends[4] - ends[5]) > 1e-9:
            raise PipelineError(
                f"tableau_waterfall ({baseline}): components end at {ends[4]:.6f}%, "
                f"latest share is {ends[5]:.6f}%"
            )
    path = CSV_OUT / "tableau_waterfall.csv"
    con.execute(f"copy ({TABLEAU_WATERFALL}) to '{path}' (header, delimiter ',')")
    print(f"  {path.relative_to(CSV_OUT.parent.parent.parent)}")


def defined_marts() -> list[str]:
    names = set()
    for path in sorted(SQL_DIR.glob("mart_*.sql")):
        names.update(re.findall(r"create or replace table (mart_\w+)", path.read_text()))
    return sorted(names)


def main() -> None:
    marts = defined_marts()
    if not marts:
        raise PipelineError("No mart definitions found in sql/.")
    con = connect()
    CSV_OUT.mkdir(parents=True, exist_ok=True)
    for old in CSV_OUT.glob("*.csv"):
        old.unlink()
    for table in marts + EXTRA_TABLES:
        path = CSV_OUT / f"{table}.csv"
        con.execute(f"copy {table} to '{path}' (header, delimiter ',')")
        print(f"  {path.relative_to(CSV_OUT.parent.parent.parent)}")
    tableau_waterfall(con)
    con.close()


if __name__ == "__main__":
    main()
