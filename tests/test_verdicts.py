"""Tests for the verdict rules (H3 offset ratio bands) and the H4 baseline snapshots."""

import re

import duckdb
import pytest

from src import analysis
from src.common import SQL_DIR


@pytest.mark.parametrize(
    ("ratio", "d_us", "expected"),
    [
        (0.10, -5.0, "confirmed"),
        (-0.30, -5.0, "confirmed"),
        (0.25, -5.0, "partial"),
        (0.50, -5.0, "partial"),
        (0.75, -5.0, "partial"),
        (0.80, -5.0, "rejected"),
        (None, 3.0, "not applicable (US exports did not fall)"),
    ],
)
def test_h3_verdict(ratio, d_us, expected):
    assert analysis.h3_verdict(ratio, d_us) == expected


def h4_test_table(counts: dict[str, int], tariff_count: int) -> duckdb.DuckDBPyConnection:
    """Runs the mart_extensive_margin_test SQL on hand-made snapshot counts."""
    con = duckdb.connect()
    con.execute(
        "create table params as select * from (values ('baseline_start', '2022-01-01'), "
        "('baseline_end', '2024-12-01'), ('sens_baseline_start', '2023-01-01'), "
        "('sens_baseline_end', '2024-12-01')) t(key, value)"
    )
    con.execute("create macro p(k) as (select value from params where key = k)")
    con.execute("create table m7_snapshots (snapshot date, role varchar)")
    con.execute(
        "create table mart_extensive_margin (snapshot date, role varchar, "
        "variant varchar, n_new_pairs bigint)"
    )
    for snap, n in counts.items():
        con.execute("insert into m7_snapshots values (?, 'baseline')", [snap])
        con.execute(
            "insert into mart_extensive_margin values (?, 'baseline', 'total', ?)", [snap, n]
        )
    con.execute(
        "insert into mart_extensive_margin values ('2026-09-01', 'tariff', 'total', ?)",
        [tariff_count],
    )
    sql = (SQL_DIR / "mart_07_extensive_margin.sql").read_text()
    block = re.search(r"create or replace table mart_extensive_margin_test as.*?;", sql, re.S)
    con.execute(block.group(0))
    return con


def test_h4_both_baselines_use_frozen_snapshots():
    con = h4_test_table({"2023-12-01": 100, "2024-12-01": 80}, 110)
    rows = {
        r[0]: r[1:]
        for r in con.execute(
            "select baseline, n_baseline_snapshots, baseline_mean, change_vs_baseline "
            "from mart_extensive_margin_test"
        ).fetchall()
    }
    # Frozen rule: both baselines use Dec 2023 and Dec 2024.
    for baseline in ("primary", "sensitivity"):
        assert rows[baseline][:2] == (2, 90.0)
        assert rows[baseline][2] == pytest.approx(110 / 90 - 1)
