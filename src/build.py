"""Runs the SQL files in sql/ in order against data/processed/trade.duckdb.

`python -m src.build staging` runs sql/staging_*.sql; `python -m src.build marts` runs
sql/mart_*.sql. Settings from config/settings.yaml are loaded into small parameter tables
first, so the SQL never hard-codes a period or threshold.
"""

import sys
from pathlib import Path

import duckdb

from src.common import CONFIG, DB_PATH, LANDING, SQL_DIR, PipelineError, load_settings


def month(value: str) -> str:
    return f"{value}-01"


def load_params(con: duckdb.DuckDBPyConnection, settings: dict) -> None:
    p = settings["periods"]
    t = settings["thresholds"]
    m7 = settings["m7"]
    params = {
        "landing_dir": str(LANDING),
        "config_dir": str(CONFIG),
        "first_month": month(settings["data"]["first_month"]),
        "baseline_start": month(p["baseline_primary"]["start"]),
        "baseline_end": month(p["baseline_primary"]["end"]),
        "sens_baseline_start": month(p["baseline_sensitivity"]["start"]),
        "sens_baseline_end": month(p["baseline_sensitivity"]["end"]),
        "frontload_start": month(p["frontload"]["start"]),
        "frontload_end": month(p["frontload"]["end"]),
        "tariff_earliest_start": month(p["tariff_period_earliest_start"]),
        "m7_prior_max": m7["prior_12m_max_cad"],
        "m7_current_min": m7["current_12m_min_cad"],
        "m7_sustain": m7["sustain_month_ends"],
        "m2_max_residual_share": t["m2_max_residual_share"],
    }
    con.execute("create or replace table params (key varchar primary key, value varchar)")
    con.executemany("insert into params values (?, ?)", [(k, str(v)) for k, v in params.items()])
    con.execute("create or replace macro p(k) as (select value from params where key = k)")

    con.execute("create or replace table m7_snapshots (snapshot date, role varchar)")
    con.executemany(
        "insert into m7_snapshots values (?, 'baseline')",
        [(month(s),) for s in m7["baseline_snapshots"]],
    )

    con.execute("create or replace table h3_sector_start (sector_group varchar, event_date date)")
    con.executemany(
        "insert into h3_sector_start values (?, ?)", list(settings["h3_sector_start"].items())
    )

    con.execute(
        "create or replace table unit_normalization "
        "(hs4 varchar, from_unit varchar, to_unit varchar, factor double)"
    )
    con.executemany(
        "insert into unit_normalization values (?, ?, ?, ?)",
        [(u["hs4"], u["from_unit"], u["to_unit"], u["factor"])
         for u in settings["unit_normalization"]],
    )

    # HS rules: (sector_group, role, level, lo, hi). role = primary | member | other.
    s = settings["sectors"]
    rules = []
    rules += [("steel", "primary", 6, lo, hi) for lo, hi in s["steel"]["full_hs6_ranges"]]
    rules += [("steel", "member", 4, lo, hi) for lo, hi in s["steel"]["partial_hs4_ranges"]]
    rules += [("steel", "other", 4, lo, hi) for lo, hi in s["steel"]["other_hs4_ranges"]]
    rules += [("aluminum", "primary", 4, c, c) for c in s["aluminum"]["full_hs4"]]
    rules += [("aluminum", "member", 4, c, c) for c in s["aluminum"]["partial_hs4"]]
    rules += [("aluminum", "other", 4, c, c) for c in s["aluminum"]["other_hs4"]]
    rules += [("copper", "member", 4, c, c) for c in s["copper"]["sector_hs4"]]
    rules += [("copper", "other", 4, lo, hi) for lo, hi in s["copper"]["other_hs4_ranges"]]
    rules += [("autos", "candidate", 2, c, c) for c in s["autos"]["sector_hs2"]]
    rules += [("lumber", "softwood", 4, c, c) for c in s["lumber"]["full_hs4"]]
    con.execute(
        "create or replace table hs_rules "
        "(sector_group varchar, role varchar, level int, lo varchar, hi varchar)"
    )
    con.executemany("insert into hs_rules values (?, ?, ?, ?, ?)", rules)

    con.execute("create or replace table flag_codes (flag varchar, level int, code varchar)")
    flags = [("gold", 4, c) for c in settings["gold"]["hs4"]]
    flags += [("energy", 2, c) for c in settings["energy"]["hs2"]]
    flags += [("crude", 4, c) for c in settings["energy"]["crude_hs4"]]
    con.executemany("insert into flag_codes values (?, ?, ?)", flags)


def landing_views(con: duckdb.DuckDBPyConnection) -> None:
    """One raw_* view per landing or config file. All columns are read as text."""

    def view(name: str, path: Path) -> None:
        if not list(path.parent.glob(path.name)):
            raise PipelineError(f"Missing landing file {path}. Run `make ingest`.")
        con.execute(
            f"create or replace view {name} as select * from "
            f"read_csv('{path}', header = true, all_varchar = true)"
        )

    cimt = LANDING / "cimt"
    view("raw_dom_hs6", cimt / "dom_hs6_*.csv")
    view("raw_tot_hs2", cimt / "tot_hs2_*.csv")
    view("raw_hs6_desc", cimt / "hs6_desc.csv")
    view("raw_country_desc", cimt / "country_desc.csv")
    view("raw_wds_0011", LANDING / "statcan_12100011.csv")
    view("raw_wds_0171", LANDING / "statcan_12100171.csv")
    view("raw_wds_0168", LANDING / "statcan_12100168.csv")
    view("raw_wds_0182", LANDING / "statcan_12100182.csv")
    view("raw_prices", LANDING / "prices.csv")
    view("raw_fx", LANDING / "fx.csv")
    view("raw_sccai", LANDING / "sccai.csv")
    view("raw_tariff_list_codes", LANDING / "tariff_list_codes.csv")
    view("raw_us_hts8", LANDING / "us_hts8.csv")
    view("raw_tariff_events", CONFIG / "tariff_events.csv")
    view("raw_tariff_lists", CONFIG / "tariff_lists.csv")
    view("raw_eu_members", CONFIG / "eu_members.csv")

    previous = LANDING / "cimt_previous"
    if (previous / "VINTAGE").exists():
        view("raw_dom_hs6_previous", previous / "dom_hs6_*.csv")
        prev_vintage = (previous / "VINTAGE").read_text().strip()
    else:
        con.execute(
            "create or replace view raw_dom_hs6_previous as "
            "select * from raw_dom_hs6 where false"
        )
        prev_vintage = ""
    vintage = (cimt / "VINTAGE").read_text().strip()
    con.executemany(
        "insert or replace into params values (?, ?)",
        [("cimt_vintage", vintage), ("cimt_previous_vintage", prev_vintage)],
    )


def run_sql_files(con: duckdb.DuckDBPyConnection, prefix: str) -> None:
    files = sorted(SQL_DIR.glob(f"{prefix}_*.sql"))
    if not files:
        raise PipelineError(f"No SQL files with prefix {prefix}")
    for path in files:
        print(f"  running {path.name}")
        con.execute(Path(path).read_text())


def connect() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def main(stage: str) -> None:
    if stage not in ("staging", "mart"):
        raise PipelineError("Usage: python -m src.build [staging|mart]")
    con = connect()
    if stage == "staging":
        load_params(con, load_settings())
        landing_views(con)
    run_sql_files(con, stage)
    con.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
