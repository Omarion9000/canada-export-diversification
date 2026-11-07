"""Exports marts and dimensions to CSV (data/processed/csv/) for Excel and Tableau.

Only marts defined in the current sql/mart_*.sql files are exported, so a table left in the
database by an older version of the SQL is never published.
"""

import re

from src.build import connect
from src.common import CSV_OUT, SQL_DIR, PipelineError

EXTRA_TABLES = ["dim_country", "dim_product", "dim_month", "tariff_events"]


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
    con.close()


if __name__ == "__main__":
    main()
