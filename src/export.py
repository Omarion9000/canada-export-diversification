"""Exports marts and dimensions to CSV (data/processed/csv/) for Excel and Tableau."""

from src.build import connect
from src.common import CSV_OUT, PipelineError

EXTRA_TABLES = ["dim_country", "dim_product", "dim_month", "tariff_events"]


def main() -> None:
    con = connect()
    marts = [r[0] for r in con.execute(
        "select table_name from information_schema.tables "
        "where table_name like 'mart_%' order by 1").fetchall()]
    if not marts:
        raise PipelineError("No marts found. Run `make marts` first.")
    CSV_OUT.mkdir(parents=True, exist_ok=True)
    for table in marts + EXTRA_TABLES:
        path = CSV_OUT / f"{table}.csv"
        con.execute(f"copy {table} to '{path}' (header, delimiter ',')")
        print(f"  {path.relative_to(CSV_OUT.parent.parent.parent)}")
    con.close()


if __name__ == "__main__":
    main()
