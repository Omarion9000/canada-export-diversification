"""Hypothesis verdicts computed from the marts against the frozen thresholds.

Every number returned here is read from a mart; nothing is typed by hand.
"""

import duckdb

from src.common import DB_PATH, PipelineError, load_settings

BASELINES = {"primary": "2022–2024", "sensitivity": "2023–2024"}


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def records(con, sql: str, params=None) -> list[dict]:
    cur = con.execute(sql, params or [])
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def tariff_window(con) -> tuple[str, str]:
    start, end = con.execute(
        "select strftime(min(month), '%b %Y'), strftime(max(month), '%b %Y') "
        "from dim_month where period_label = 'tariff'"
    ).fetchall()[0]
    return start, end


def h1(con, baseline: str, variant: str) -> dict:
    """H1: the US share fell more because exports to the rest of the world grew than because
    exports to the US fell. Confirmed if the RoW-side contribution to the decline is larger
    than the US-side contribution (M2, using the form the residual rule selects)."""
    r = records(
        con,
        "select * from mart_decomposition where baseline = ? and variant = ?",
        [baseline, variant],
    )[0]
    form = "exact" if r["method_used"] == "exact" else "approx"
    us_side, row_side = r[f"us_side_{form}"], r[f"row_side_{form}"]
    # Contribution to the decline = minus the term (a negative term pushes the share down).
    us_contrib, row_contrib = -us_side, -row_side
    verdict = "confirmed" if row_contrib > us_contrib else "rejected"
    total = us_side + row_side
    return {
        "baseline": baseline,
        "variant": variant,
        "method": r["method_used"],
        "residual_share": r["approx_residual_share"],
        "s_base": r["s_us_base"],
        "s_tariff": r["s_us_tariff"],
        "d_share_pp": r["d_share_pp"],
        "us_side": us_side,
        "row_side": row_side,
        "row_share_of_change": row_side / total if total else None,
        "dln_x_us": r["dln_x_us"],
        "dln_x_row": r["dln_x_row"],
        "x_us_base": r["x_us_base"],
        "x_us_tariff": r["x_us_tariff"],
        "x_row_base": r["x_row_base"],
        "x_row_tariff": r["x_row_tariff"],
        "verdict": verdict,
    }


def waterfall(con, baseline: str) -> dict:
    rows = records(con, "select * from mart_waterfall where baseline = ? order by step", [baseline])
    by = {r["component"]: r for r in rows}
    return {
        "baseline": baseline,
        "s_base_pct": rows[0]["s_total_base_pct"],
        "s_tariff_pct": rows[0]["s_total_tariff_pct"],
        "total": by["Total change (headline)"]["effect_pp"],
        "gold": by["Gold"]["effect_pp"],
        "gold_range": (by["Gold"]["order_gold_first"], by["Gold"]["order_energy_first"]),
        "energy": by["Energy"]["effect_pp"],
        "energy_range": (by["Energy"]["order_gold_first"], by["Energy"]["order_energy_first"]),
        "rest": by["Everything else (ex-gold-ex-energy)"]["effect_pp"],
    }


def h2(con, baseline: str) -> dict:
    """H2: excluding gold and energy, the US share decline is much smaller than the headline.
    Confirmed if the ex-gold-ex-energy decline is at most the frozen share of the headline."""
    limit = load_settings()["thresholds"]["h2_max_share_of_headline"]
    w = waterfall(con, baseline)
    ratio = w["rest"] / w["total"]
    if w["total"] >= 0:
        verdict = "not applicable (no decline)"
    else:
        verdict = "confirmed" if ratio <= limit else "rejected"
    return {**w, "ratio": ratio, "limit": limit, "verdict": verdict}


def price_volume(con, baseline: str, commodity: str, destination: str) -> dict:
    """M4: change in export value split into price and volume effects (midpoint formula).

    dV = dP * mean(Q) + dQ * mean(P), with P the customs unit value (value / quantity).
    """
    r = records(
        con,
        "select * from mart_price_volume where baseline = ? and commodity = ? and destination = ?",
        [baseline, commodity, destination],
    )[0]
    return {
        **r,
        "price_share": r["price_effect"] / r["d_value"] if r["d_value"] else None,
        "p_growth": r["p_tariff"] / r["p_base"] - 1,
        "q_growth": r["q_tariff"] / r["q_base"] - 1,
    }


SECTORS = {
    "steel": "Steel",
    "aluminum": "Aluminum",
    "copper": "Copper",
    "autos": "Autos and parts",
    "lumber": "Softwood lumber",
}


def h3_verdict(offset_ratio, d_us: float) -> str:
    t = load_settings()["thresholds"]
    if d_us >= 0:
        return "not applicable (US exports did not fall)"
    if offset_ratio < t["h3_offset_ratio_confirm_below"]:
        return "confirmed"
    if offset_ratio > t["h3_offset_ratio_reject_above"]:
        return "rejected"
    return "partial"


def h3(con, baseline: str) -> list[dict]:
    """H3: tariffed sectors sold less to the US but did not redirect to other markets.

    Offset ratio = change in non-US exports / |change in US exports| (M6), sector aggregate,
    each sector over its own window. Confirmed below 0.25, rejected above 0.75, partial between.
    """
    rows = records(
        con,
        "select * from mart_redirection where baseline = ? and level = 'sector'",
        [baseline],
    )
    by = {r["sector_group"]: r for r in rows}
    return [
        {**by[key], "label": label, "verdict": h3_verdict(by[key]["offset_ratio"], by[key]["d_us"])}
        for key, label in SECTORS.items()
    ]


def h3_hs4(con, baseline: str, sector: str) -> list[dict]:
    """HS4 detail for one sector, largest US baseline value first."""
    return records(
        con,
        "select * from mart_redirection where baseline = ? and level = 'hs4' "
        "and sector_group = ? order by x_us_base desc",
        [baseline, sector],
    )


def no_sector_tariff(con, baseline: str, window_of_sector: str, group_variant: str) -> dict:
    """Comparison group: products with no sector-specific tariff, same window as the sector."""
    return records(
        con,
        "select * from mart_redirection_no_sector_tariff where baseline = ? "
        "and window_of_sector = ? and group_variant = ?",
        [baseline, window_of_sector, group_variant],
    )[0]


def h4(con, baseline: str) -> list[dict]:
    """H4: new non-US product x country pairs did not rise above the pre-tariff level.

    Confirmed if the tariff-period count is within +/- the frozen band of the baseline mean;
    rejected if it is above the band.
    """
    band = load_settings()["thresholds"]["h4_band"]
    out = []
    for r in records(
        con,
        "select * from mart_extensive_margin_test where baseline = ? order by "
        "case variant when 'total' then 1 when 'ex_gold' then 2 else 3 end",
        [baseline],
    ):
        low, high = r["baseline_mean"] * (1 - band), r["baseline_mean"] * (1 + band)
        if r["tariff_count"] > high:
            verdict = "rejected"
        elif r["tariff_count"] >= low:
            verdict = "confirmed"
        else:
            verdict = "below the band (not covered by the rule)"
        out.append({**r, "band": band, "low": low, "high": high, "verdict": verdict})
    return out


def h4_top(con, dimension: str, rank: int = 5) -> list[dict]:
    """Countries or HS2 chapters with the most new pairs at the tariff snapshot (ties kept)."""
    return records(
        con,
        "select * from mart_extensive_margin_by_group where role = 'tariff' and dimension = ? "
        "and rank_in_snapshot <= ? order by rank_in_snapshot, n_new_pairs desc, label",
        [dimension, rank],
    )


def exposure(con, baseline: str) -> list[dict]:
    """M8 sector exposure table, most US-dependent sector first (latest 12 months)."""
    return records(
        con,
        "select * from mart_exposure where baseline = ? order by us_dependence_latest desc",
        [baseline],
    )


def h4_context(con, kind: str, variant: str = "total") -> dict | None:
    """Context rows for H4 that are not verdicts: 'exploratory' or 'post_hoc'."""
    rows = records(
        con,
        "select * from mart_extensive_margin_context where kind = ? and variant = ?",
        [kind, variant],
    )
    return rows[0] if rows else None


def hs2_short(code: str) -> str:
    names = load_settings()["hs2_short_names"]
    if code not in names:
        raise PipelineError(
            f"HS2 chapter {code} has no short name: add it to hs2_short_names in "
            f"config/settings.yaml"
        )
    return names[code]


def h4_risers(con, dimension: str, n: int = 3) -> list[dict]:
    """Countries or HS2 chapters whose new-pair count rose most against their baseline mean."""
    return records(
        con,
        "select * from mart_extensive_margin_by_group where role = 'tariff' and dimension = ? "
        "order by change_vs_baseline_mean desc, n_new_pairs desc, label limit ?",
        [dimension, n],
    )
