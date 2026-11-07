"""Test for the Tableau-ready waterfall table built from mart_waterfall."""

import duckdb
import pytest

from src.export import TABLEAU_WATERFALL


def test_tableau_waterfall_bars():
    con = duckdb.connect()
    con.execute(
        "create table mart_waterfall (baseline varchar, step int, component varchar, "
        "effect_pp double, s_total_base_pct double, s_total_tariff_pct double)"
    )
    # Baseline 80%, gold -5, energy +1, everything else -2 -> latest 74%.
    con.execute(
        "insert into mart_waterfall values "
        "('primary', 0, 'Total change (headline)', -6, 80, 74), "
        "('primary', 1, 'Gold', -5, 80, 74), "
        "('primary', 2, 'Energy', 1, 80, 74), "
        "('primary', 3, 'Everything else (ex-gold-ex-energy)', -2, 80, 74)"
    )
    rows = con.execute(TABLEAU_WATERFALL).fetchall()
    expected = [
        ("primary", 1, "US share, baseline", 0, 80, 80, "level"),
        ("primary", 2, "Gold", 80, 75, -5, "decrease"),
        ("primary", 3, "Energy", 75, 76, 1, "increase"),
        ("primary", 4, "Everything else", 76, 74, -2, "decrease"),
        ("primary", 5, "US share, latest 12 months", 0, 74, 74, "level"),
    ]
    assert len(rows) == len(expected)
    for got, want in zip(rows, expected, strict=True):
        assert got[:3] == want[:3] and got[6] == want[6]
        assert got[3:6] == pytest.approx(want[3:6])
