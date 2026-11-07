"""Writes README.md and docs/one_pager.md from templates, filling every number from the marts.

Templates live in docs/templates/. Run after the marts and figures (`make report`).
"""

import re

from src import analysis
from src.common import DOCS, ROOT
from src.figures import signed
from src.validate.checks import v2

TEMPLATES = DOCS / "templates"


def pp(x: float) -> str:
    return f"{abs(x):.1f}"


def values(con) -> dict:
    start, end = analysis.tariff_window(con)
    first, last = con.execute(
        "select strftime(min(month), '%B %Y'), strftime(max(month), '%B %Y') from dim_month"
    ).fetchall()[0]
    vintage = con.execute("select p('cimt_vintage')").fetchall()[0][0]
    n_events = con.execute("select count(*) from tariff_events").fetchall()[0][0]
    n_hs6 = con.execute("select count(distinct hs6) from fact_exports").fetchall()[0][0]
    n_countries = con.execute("select count(distinct country_code) from fact_exports").fetchall()[
        0
    ][0]

    h2p, h2s = analysis.h2(con, "primary"), analysis.h2(con, "sensitivity")
    h1p, h1s = analysis.h1(con, "primary", "total"), analysis.h1(con, "sensitivity", "total")
    h1p_x = analysis.h1(con, "primary", "ex_gold_ex_energy")
    h1s_x = analysis.h1(con, "sensitivity", "ex_gold_ex_energy")
    h1p_g = analysis.h1(con, "primary", "ex_gold")
    row_change = h1p["x_row_tariff"] - h1p["x_row_base"]
    gold_row_change = row_change - (h1p_g["x_row_tariff"] - h1p_g["x_row_base"])
    v2_gap = v2(con).details["gap_pp"].abs().max()

    def growth(a, b):
        return 100 * (b / a - 1)

    v = {
        "first_month": first,
        "last_month": last,
        "tariff_start": start,
        "tariff_end": end,
        "vintage": vintage,
        "n_events": n_events,
        "n_hs6": f"{n_hs6:,}",
        "n_countries": n_countries,
        # H2 / waterfall, primary
        "s_base": f"{h2p['s_base_pct']:.1f}",
        "s_latest": f"{h2p['s_tariff_pct']:.1f}",
        "d_total": pp(h2p["total"]),
        "d_gold": pp(h2p["gold"]),
        "d_energy": pp(h2p["energy"]),
        "energy_sign": "lowered" if h2p["energy"] < 0 else "raised",
        "d_rest": pp(h2p["rest"]),
        "gold_share": f"{h2p['gold'] / h2p['total']:.0%}",
        "rest_share": f"{h2p['rest'] / h2p['total']:.0%}",
        "gold_lo": pp(max(h2p["gold_range"])),
        "gold_hi": pp(min(h2p["gold_range"])),
        "energy_lo": f"{min(h2p['energy_range']):+.1f}",
        "energy_hi": f"{max(h2p['energy_range']):+.1f}",
        "h2_ratio": f"{h2p['ratio']:.1%}",
        "h2_limit": f"{h2p['limit']:.0%}",
        "h2_verdict": h2p["verdict"],
        # H2 sensitivity
        "s_base_sens": f"{h2s['s_base_pct']:.1f}",
        "d_total_sens": pp(h2s["total"]),
        "d_gold_sens": pp(h2s["gold"]),
        "d_energy_sens": f"{h2s['energy']:+.1f}",
        "d_rest_sens": pp(h2s["rest"]),
        "h2_ratio_sens": f"{h2s['ratio']:.1%}",
        "h2_verdict_sens": h2s["verdict"],
        "h2_same": "the same" if h2p["verdict"] == h2s["verdict"] else "different",
        # H1, primary, all goods
        "x_us_base": f"{h1p['x_us_base'] / 1e9:.1f}",
        "x_us_latest": f"{h1p['x_us_tariff'] / 1e9:.1f}",
        "x_row_base": f"{h1p['x_row_base'] / 1e9:.1f}",
        "x_row_latest": f"{h1p['x_row_tariff'] / 1e9:.1f}",
        "us_growth": f"{growth(h1p['x_us_base'], h1p['x_us_tariff']):+.1f}",
        "row_growth": f"{growth(h1p['x_row_base'], h1p['x_row_tariff']):+.1f}",
        "h1_row_share": f"{h1p['row_share_of_change']:.0%}",
        "h1_row_side": f"{-100 * h1p['row_side']:.1f}",
        "h1_us_side": f"{-100 * h1p['us_side']:.1f}",
        "h1_method": h1p["method"],
        "h1_verdict": h1p["verdict"],
        # H1 without gold and energy
        "x_row_base_x": f"{h1p_x['x_row_base'] / 1e9:.1f}",
        "x_row_latest_x": f"{h1p_x['x_row_tariff'] / 1e9:.1f}",
        "row_growth_x": f"{growth(h1p_x['x_row_base'], h1p_x['x_row_tariff']):+.1f}",
        "us_growth_x": f"{growth(h1p_x['x_us_base'], h1p_x['x_us_tariff']):+.1f}",
        "h1_row_share_x": f"{h1p_x['row_share_of_change']:.0%}",
        "h1_verdict_x": h1p_x["verdict"],
        # H1 sensitivity
        "h1_row_share_sens": f"{h1s['row_share_of_change']:.0%}",
        "h1_verdict_sens": h1s["verdict"],
        "h1_row_share_x_sens": f"{h1s_x['row_share_of_change']:.0%}",
        "h1_verdict_x_sens": h1s_x["verdict"],
        "h1_same": "the same"
        if len({h1p["verdict"], h1s["verdict"], h1p_x["verdict"], h1s_x["verdict"]}) == 1
        else "different",
    }
    v["gold_row_growth_share"] = f"{gold_row_change / row_change:.0%}"
    v["row_change_bn"] = f"{row_change / 1e9:.1f}"
    v["gold_row_change_bn"] = f"{gold_row_change / 1e9:.1f}"
    v["v2_gap"] = f"{v2_gap:.2f}"
    v["gold_part"] = "more than half" if h2p["gold"] / h2p["total"] > 0.5 else v["gold_share"]
    # M4: price vs volume, baseline 2022-2024.
    for key, commodity, destination in [
        ("g_row", "gold", "Non-US"),
        ("g_us", "gold", "United States"),
        ("c_row", "crude", "Non-US"),
        ("c_us", "crude", "United States"),
    ]:
        r = analysis.price_volume(con, "primary", commodity, destination)
        v[f"{key}_dv"] = f"{abs(r['d_value']) / 1e9:.1f}"
        v[f"{key}_dir"] = "rose" if r["d_value"] > 0 else "fell"
        v[f"{key}_pe"] = f"{abs(r['price_effect']) / 1e9:.1f}"
        v[f"{key}_ve"] = f"{abs(r['volume_effect']) / 1e9:.1f}"
        v[f"{key}_main"] = (
            "price" if abs(r["price_effect"]) >= abs(r["volume_effect"]) else "volume"
        )
        v[f"{key}_price_share"] = f"{r['price_share']:.0%}"
        v[f"{key}_p"] = f"{100 * r['p_growth']:+.0f}"
        v[f"{key}_q"] = f"{100 * r['q_growth']:+.0f}"
    # Flag a thin margin when the sensitivity ratio is within 5 points of the threshold.
    thin = abs(h2s["ratio"] - h2s["limit"]) < 0.05
    v["thin_note"] = "; thin margin" if thin else ""
    v["thin_clause"] = ", but the margin is thin" if thin else ""
    for key in ("h1_verdict", "h1_verdict_x", "h2_verdict"):
        v[key + "_cap"] = v[key].capitalize()
    # Signed component values (share reductions are negative), typographic minus everywhere.
    v["d_total_s"] = signed(h2p["total"])
    v["d_gold_s"], v["d_energy_s"], v["d_rest_s"] = (
        signed(h2p["gold"]),
        signed(h2p["energy"]),
        signed(h2p["rest"]),
    )
    v["d_gold_sens_s"], v["d_rest_sens_s"] = signed(h2s["gold"]), signed(h2s["rest"])
    v["gold_lo_s"], v["gold_hi_s"] = signed(min(h2p["gold_range"])), signed(max(h2p["gold_range"]))
    g_us = analysis.price_volume(con, "primary", "gold", "United States")
    v["g_us_ve_s"] = signed(g_us["volume_effect"] / 1e9)
    v["c_row_ve_s"] = signed(
        analysis.price_volume(con, "primary", "crude", "Non-US")["volume_effect"] / 1e9
    )
    c_row = analysis.price_volume(con, "primary", "crude", "Non-US")
    v["c_row_vol_share"] = f"{c_row['volume_effect'] / c_row['d_value']:.0%}"
    v["row_growth_x_abs"] = f"{abs(float(v['row_growth_x'])):.1f}"
    for key, value in v.items():
        if isinstance(value, str) and re.fullmatch(r"[+-]\d[\d.,]*", value):
            v[key] = value.replace("-", "\u2212")
    return v


def render(template: str, target, v: dict) -> None:
    text = (TEMPLATES / template).read_text(encoding="utf-8").format(**v)
    target.write_text(text, encoding="utf-8")
    print(f"  {target.relative_to(ROOT)}")


def main() -> None:
    con = analysis.connect()
    v = values(con)
    con.close()
    render("README.md.tpl", ROOT / "README.md", v)
    render("one_pager.md.tpl", DOCS / "one_pager.md", v)


if __name__ == "__main__":
    main()
