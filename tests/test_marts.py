"""Unit tests for M2, M3, M4 and M6 on a tiny hand-built data set.

The world has 2 baseline months (Jan and Feb 2022) and 2 tariff months (Jan and Feb 2023).
Each baseline month has weight 1, so a baseline value is simply Jan + Feb 2022.

Totals (baseline -> tariff), CAD:
    US:  other 60 -> 54 (steel 30 -> 20, rest 30 -> 34), energy 20 -> 18
    RoW: other 15 -> 20 (steel 5 -> 9,  rest 10 -> 11), gold 5 -> 20
"""

import math

import duckdb
import pytest

from src.common import SQL_DIR

PRODUCTS = [
    # hs6, hs4, sector_group, is_gold, is_energy, is_crude, is_tariffed
    ("710812", "7108", "gold", True, False, False, False),
    ("270900", "2709", "energy", False, True, True, False),
    ("720610", "7206", "steel", False, False, False, True),
    ("010121", "0101", "other", False, False, False, False),
]
# (hs6, country, baseline total, tariff total, baseline qty, tariff qty); split evenly by month.
FLOWS = [
    ("720610", "US", 30, 20, 0, 0),
    ("010121", "US", 30, 34, 0, 0),
    ("270900", "US", 20, 18, 4, 3),
    ("720610", "GB", 5, 9, 0, 0),
    ("010121", "CN", 10, 11, 0, 0),
    ("710812", "GB", 5, 20, 2, 4),
]
MONTHS = [("2022-01-01", 1, "baseline"), ("2022-02-01", 2, "baseline"),
          ("2023-01-01", 1, "tariff"), ("2023-02-01", 2, "tariff")]


@pytest.fixture()
def con():
    c = duckdb.connect()
    c.execute("create table params (key varchar, value varchar)")
    c.execute("insert into params values ('m2_max_residual_share', '0.1')")
    c.execute("create macro p(k) as (select value from params where key = k)")
    c.execute("""create table dim_month (month date, calendar_month int, period_label varchar,
                 in_baseline boolean, in_sensitivity_baseline boolean)""")
    for m, cal, label in MONTHS:
        base = label == "baseline"
        c.execute("insert into dim_month values (?, ?, ?, ?, ?)", [m, cal, label, base, base])
    c.execute("""create table dim_product (hs6 varchar, hs4 varchar, sector_group varchar,
                 is_gold boolean, is_energy boolean, is_crude boolean, is_tariffed boolean)""")
    c.executemany("insert into dim_product values (?, ?, ?, ?, ?, ?, ?)", PRODUCTS)
    c.execute("create table dim_country (country_code varchar, is_us boolean)")
    c.executemany("insert into dim_country values (?, ?)",
                  [("US", True), ("GB", False), ("CN", False)])
    c.execute("""create table fact_exports (month date, country_code varchar, hs6 varchar,
                 value_cad double, quantity double, qty_unit varchar)""")
    for hs6, cty, base, tariff, qb, qt in FLOWS:
        unit = "GRM" if hs6 == "710812" else "MTQ"
        for m, _, label in MONTHS:
            v, q = (base, qb) if label == "baseline" else (tariff, qt)
            c.execute("insert into fact_exports values (?, ?, ?, ?, ?, ?)",
                      [m, cty, hs6, v / 2, q / 2, unit])
    c.execute("create table fx (month date, usdcad double)")
    c.executemany("insert into fx values (?, 1.25)", [(m,) for m, _, _ in MONTHS])
    c.execute("create table prices (month date, series varchar, value double)")
    for m, _, _ in MONTHS:
        c.execute("insert into prices values (?, 'gold_usd_per_troy_oz', 2000)", [m])
        c.execute("insert into prices values (?, 'crude_avg_usd_per_bbl', 80)", [m])
    c.execute("create table h3_sector_start (sector_group varchar, event_date date)")
    c.execute("insert into h3_sector_start values ('steel', '2023-01-01')")
    c.execute("""create table staging_tariff_scope_monthly as
                 select m.month, d.hs6,
                        case when d.is_tariffed and m.period_label = 'tariff' then 'full'
                             else 'none' end as tariff_scope
                 from dim_month m cross join dim_product d""")
    for name in ["mart_00_base.sql", "mart_02_decomposition.sql", "mart_03_waterfall.sql",
                 "mart_04_price_volume.sql", "mart_06_redirection.sql"]:
        c.execute((SQL_DIR / name).read_text())
    yield c
    c.close()


def row(con, sql):
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    assert len(rows) == 1, f"expected one row, got {len(rows)}"
    return dict(zip(names, rows[0], strict=True))


def test_m2_decomposition(con):
    r = row(con, "select * from mart_decomposition "
                 "where baseline = 'primary' and variant = 'total'")
    # s_US: 80/100 -> 72/112. w_R = 0.2.
    assert r["s_us_base"] == pytest.approx(0.8)
    assert r["s_us_tariff"] == pytest.approx(72 / 112)
    assert r["us_side_approx"] == pytest.approx(0.2 * math.log(0.9))       # -0.0210721
    assert r["row_side_approx"] == pytest.approx(-0.2 * math.log(2))       # -0.1386294
    assert r["dln_s_us"] == pytest.approx(math.log((72 / 112) / 0.8))     # -0.2187103
    assert r["approx_residual_share"] == pytest.approx(0.26973, abs=1e-4)
    assert r["method_used"] == "exact"  # residual share 27% > 10%
    # The exact form adds up with no residual.
    assert r["us_side_exact"] + r["row_side_exact"] == pytest.approx(r["dln_s_us"])
    assert r["us_side_exact"] == pytest.approx(-0.0288553, abs=1e-6)


def test_m3_waterfall(con):
    rows = {r[0]: r[1:] for r in con.execute(
        "select component, order_gold_first, order_energy_first, effect_pp "
        "from mart_waterfall where baseline = 'primary'").fetchall()}
    # Changes in pp: total -15.7143, ex-gold -5.9497, ex-energy -17.5532, ex-both -7.0270.
    gold = rows["Gold"]
    assert gold[0] == pytest.approx(-9.7646, abs=1e-4)
    assert gold[1] == pytest.approx(-10.5262, abs=1e-4)
    assert gold[2] == pytest.approx(-10.1454, abs=1e-4)
    energy = rows["Energy"]
    assert energy[2] == pytest.approx(1.4581, abs=1e-4)
    rest = rows["Everything else (ex-gold-ex-energy)"]
    assert rest[2] == pytest.approx(-7.0270, abs=1e-4)
    total = rows["Total change (headline)"]
    assert gold[2] + energy[2] + rest[2] == pytest.approx(total[2])


def test_m4_price_volume(con):
    r = row(con, "select * from mart_price_volume where baseline = 'primary' "
                 "and commodity = 'gold' and destination = 'All destinations'")
    # V 5 -> 20, Q 2 -> 4, P 2.5 -> 5.
    assert (r["p_base"], r["p_tariff"]) == pytest.approx((2.5, 5.0))
    assert r["d_value"] == pytest.approx(15)
    assert r["price_effect"] == pytest.approx(7.5)   # (5 - 2.5) * (2 + 4) / 2
    assert r["volume_effect"] == pytest.approx(7.5)  # (4 - 2) * (2.5 + 5) / 2


def test_m4_benchmark_conversion(con):
    r = row(con, "select benchmark_cad_per_unit from mart_price_volume_monthly "
                 "where commodity = 'gold' and destination = 'All destinations' "
                 "and month = '2022-01-01'")
    assert r["benchmark_cad_per_unit"] == pytest.approx(2000 * 1.25 / 31.1034768)


def test_m6_offset_ratio(con):
    r = row(con, "select * from mart_redirection where baseline = 'primary' "
                 "and level = 'sector' and sector_group = 'steel'")
    # US 30 -> 20 (d = -10); non-US 5 -> 9 (d = +4). OR = 4 / 10.
    assert r["n_months"] == 2
    assert r["d_us"] == pytest.approx(-10)
    assert r["d_nonus"] == pytest.approx(4)
    assert r["offset_ratio"] == pytest.approx(0.4)
    assert r["d_us_pct"] == pytest.approx(-1 / 3)
    assert r["d_nonus_pct"] == pytest.approx(0.8)


def test_m6_no_sector_tariff_group(con):
    r = row(con, "select * from mart_redirection_no_sector_tariff where baseline = 'primary' "
                 "and group_variant = 'ex_gold_ex_energy'")
    # No sector-specific tariff: US 30 -> 34 (rises), non-US 10 -> 11.
    # The offset ratio is not defined when US exports rise; percent changes are reported.
    assert r["d_us"] == pytest.approx(4)
    assert r["offset_ratio"] is None
    assert r["d_us_pct"] == pytest.approx(4 / 30)
    assert r["d_nonus_pct"] == pytest.approx(0.1)
