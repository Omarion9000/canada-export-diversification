"""Writes README.md and docs/one_pager.md from templates, filling every number from the marts.

Templates live in docs/templates/. Run after the marts and figures (`make report`).
"""

import re

from src import analysis
from src.common import DOCS, ROOT, load_settings
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
    v.update(later_phase_values(con))
    for key, value in v.items():
        if isinstance(value, str) and re.fullmatch(r"[+-]\d[\d.,]*", value):
            v[key] = value.replace("-", "\u2212")
    return v


SECTOR_NAMES = {
    "steel": "Steel",
    "aluminum": "Aluminum",
    "copper": "Copper",
    "autos": "Autos and parts",
    "lumber": "Softwood lumber",
    "energy": "Energy (HS 27)",
    "gold": "Gold (HS 7108)",
    "other": "All other goods",
}


def join(items: list[str], sep: str = ", ") -> str:
    """'a', 'a and b', 'a, b and c'. With semicolons, or when an item itself contains 'and',
    the last separator keeps its punctuation ('a; b; and c')."""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    keep = sep != ", " or any(" and " in i for i in items)
    last = f"{sep}and " if keep else " and "
    return sep.join(items[:-1]) + last + items[-1]


def minus(text: str) -> str:
    return text.replace("-", "\u2212")


def pct0(x: float) -> str:
    """Signed whole percent with a typographic minus, from a ratio (0.12 -> '+12')."""
    return minus(f"{100 * x:+.0f}")


def ratio2(x: float) -> str:
    return minus(f"{x:+.2f}")


def later_phase_values(con) -> dict:
    """H3, H4 and M8 values for the README and the one-pager."""
    v = {}
    t = load_settings()["thresholds"]
    v["h3_lo"], v["h3_hi"] = (
        f"{t['h3_offset_ratio_confirm_below']}",
        f"{t['h3_offset_ratio_reject_above']}",
    )
    # H3: one table row per sector, both baselines.
    prim = analysis.h3(con, "primary")
    sens = {r["sector_group"]: r for r in analysis.h3(con, "sensitivity")}
    lines = [
        "| Sector | Window | To the US | To other countries | Offset ratio 2022–2024 | "
        "Offset ratio 2023–2024 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in prim:
        s = sens[r["sector_group"]]
        lines.append(
            f"| {r['label']} | {r['window_start']:%b %Y}–{r['window_end']:%b %Y} | "
            f"{pct0(r['d_us_pct'])}% | {pct0(r['d_nonus_pct'])}% | "
            f"{ratio2(r['offset_ratio'])} ({r['verdict']}) | "
            f"{ratio2(s['offset_ratio'])} ({s['verdict']}) |"
        )
    group = analysis.no_sector_tariff(con, "primary", "steel", "ex_gold_ex_energy")
    group_all = analysis.no_sector_tariff(con, "primary", "steel", "all")
    group_s = analysis.no_sector_tariff(con, "sensitivity", "steel", "ex_gold_ex_energy")
    lines.append(
        f"| *No sector-specific tariff* (comparison, without gold and energy) | "
        f"{group['window_start']:%b %Y}–{group['window_end']:%b %Y} | "
        f"{pct0(group['d_us_pct'])}% | {pct0(group['d_nonus_pct'])}% | "
        f"not defined (US rose) | not defined (US rose) |"
    )
    v["h3_table"] = "\n".join(lines)
    by = {}
    for r in prim:
        by.setdefault(r["verdict"], []).append(r)
    v["h3_confirmed"] = join([r["label"].lower() for r in by.get("confirmed", [])])
    v["h3_partial"] = (
        join([r["label"].lower() for r in by.get("partial", [])]) if "partial" in by else "none"
    )
    v["h3_rejected"] = (
        join([r["label"].lower() for r in by.get("rejected", [])]) if "rejected" in by else "none"
    )
    bullets = []
    for r in by.get("rejected", []):
        bullets.append(
            f"- **Redirected (H3 rejected): {r['label'].lower()}**, offset ratio "
            f"{r['offset_ratio']:.2f}. Exports to the US fell {abs(100 * r['d_us_pct']):.0f}% "
            f"(CAD {abs(r['d_us']) / 1e9:.1f} billion) while exports to other countries went from "
            f"CAD {r['x_nonus_base'] / 1e9:.1f} billion to "
            f"{r['x_nonus_tariff'] / 1e9:.1f} billion: "
            f"about {100 * r['offset_ratio']:.0f} cents gained elsewhere for every dollar lost in "
            f"the US."
        )
    if "confirmed" in by:
        bullets.append(
            f"- **Not redirected (H3 confirmed): {v['h3_confirmed']}**, offset ratios "
            + join([f"{ratio2(r['offset_ratio'])} ({r['label'].lower()})" for r in by["confirmed"]])
            + ". Exports to the US fell and exports to other countries did not make up for it."
        )
    for r in by.get("partial", []):
        bullets.append(
            f"- **Partial: {r['label'].lower()}**, offset ratio {r['offset_ratio']:.2f}. "
            f"Exports to the US fell {abs(100 * r['d_us_pct']):.0f}% "
            f"(CAD {abs(r['d_us']) / 1e9:.1f} billion); "
            f"exports to other countries went from CAD {r['x_nonus_base'] / 1e9:.1f} billion to "
            f"{r['x_nonus_tariff'] / 1e9:.1f} billion, a large % rise from a small base."
        )
    v["h3_bullets"] = "\n".join(bullets)
    n_conf = len(by.get("confirmed", []))
    v["h3_headline"] = (
        f"{n_conf} of 5 tariffed sectors sold less to the US without finding other buyers"
    )
    v["h3_partial_clause"] = f"; {v['h3_partial']} partly did" if "partial" in by else ""
    v["h3_n_confirmed"] = len(by.get("confirmed", []))
    v["h3_same"] = (
        "the same for every sector"
        if all(r["verdict"] == sens[r["sector_group"]]["verdict"] for r in prim)
        else "different for some sectors"
    )
    # Details for the first rejected sector (aluminum in the current data).
    alu = (by.get("rejected") or [next(r for r in prim if r["sector_group"] == "aluminum")])[0]
    cop = next(r for r in prim if r["sector_group"] == "copper")
    v["alu_or"], v["alu_or_sens"] = (
        f"{alu['offset_ratio']:.2f}",
        f"{sens['aluminum']['offset_ratio']:.2f}",
    )
    v["alu_us"], v["alu_row"] = (
        minus(f"{100 * alu['d_us_pct']:+.0f}"),
        minus(f"{100 * alu['d_nonus_pct']:+.0f}"),
    )
    v["alu_cents"] = f"{100 * alu['offset_ratio']:.0f}"
    v["cop_or"], v["cop_or_sens"] = (
        f"{cop['offset_ratio']:.2f}",
        f"{sens['copper']['offset_ratio']:.2f}",
    )
    v["cop_us"], v["cop_row"] = (
        minus(f"{100 * cop['d_us_pct']:+.0f}"),
        minus(f"{100 * cop['d_nonus_pct']:+.0f}"),
    )
    v["cop_us_bn"] = f"{abs(cop['d_us']) / 1e9:.1f}"
    v["cop_row_bn"] = f"{cop['d_nonus'] / 1e9:.1f}"
    v["grp_us"], v["grp_row"] = (
        minus(f"{100 * group['d_us_pct']:+.1f}"),
        minus(f"{100 * group['d_nonus_pct']:+.1f}"),
    )
    v["grp_us_abs"] = f"{abs(100 * group['d_us_pct']):.1f}"
    v["grp_us_dir"] = "more" if group["d_us_pct"] > 0 else "less"
    v["grp_us_all"], v["grp_row_all"] = (
        minus(f"{100 * group_all['d_us_pct']:+.1f}"),
        minus(f"{100 * group_all['d_nonus_pct']:+.1f}"),
    )
    v["grp_us_sens"], v["grp_row_sens"] = (
        minus(f"{100 * group_s['d_us_pct']:+.1f}"),
        minus(f"{100 * group_s['d_nonus_pct']:+.1f}"),
    )
    lumber = next(r for r in prim if r["sector_group"] == "lumber")
    v["lumber_months"] = lumber["n_months"]
    v["lumber_window"] = f"{lumber['window_start']:%b %Y}–{lumber['window_end']:%b %Y}"
    # H4.
    h4p, h4s = analysis.h4(con, "primary"), analysis.h4(con, "sensitivity")
    tp, ts = h4p[0], h4s[0]
    v["h4_band"] = f"{tp['band']:.0%}"
    v["h4_count"] = tp["tariff_count"]
    v["h4_snapshot"] = f"{tp['tariff_snapshot']:%B %Y}"
    v["h4_mean"], v["h4_low"], v["h4_high"] = (
        f"{tp['baseline_mean']:.1f}",
        f"{tp['low']:.0f}",
        f"{tp['high']:.0f}",
    )
    v["h4_high_exact"] = f"{tp['high']:.1f}"
    v["h4_change"] = minus(f"{100 * tp['change_vs_baseline']:+.1f}")
    v["h4_verdict"], v["h4_verdict_cap"] = tp["verdict"], tp["verdict"].capitalize()
    v["h4_verdict_sens"] = ts["verdict"]
    v["h4_same"] = (
        "The verdict is the same with both baselines"
        if all(a["verdict"] == b["verdict"] for a, b in zip(h4p, h4s, strict=True))
        else "**The verdict changes between baselines**"
    )
    v["h4_change_abs"] = f"{abs(100 * tp['change_vs_baseline']):.1f}"
    room = tp["high"] - tp["tariff_count"]
    v["h4_room"] = f"{room:.1f} pairs below" if room >= 0 else f"{-room:.1f} pairs above"
    v["h4_edge"] = (
        f"{v['h4_verdict_cap']} by the frozen rule, but at the edge ({tp['tariff_count']} vs a "
        f"limit of {tp['high']:.0f}). The front-loading bias pushes the count down, so this "
        f"result cannot rule out a moderate rise in new export pairs."
        if tp["verdict"] == "confirmed"
        and (tp["high"] - tp["tariff_count"]) / tp["baseline_mean"] < 0.02
        else f"{v['h4_verdict_cap']} by the frozen rule ({tp['tariff_count']} vs a band of "
        f"{tp['low']:.0f}–{tp['high']:.0f})."
    )
    edge = (
        tp["verdict"] == "confirmed"
        and (tp["high"] - tp["tariff_count"]) / tp["baseline_mean"] < 0.02
    )
    v["h4_header"] = (
        f"{v['h4_verdict_cap']} (both baselines), at the edge"
        if edge and v["h4_same"].startswith("The verdict is the same")
        else v["h4_verdict_cap"]
    )
    v["h4_short"] = (
        f"{v['h4_verdict']} by the frozen rule, but at the edge" if edge else v["h4_verdict"]
    )
    v["h4_edge_short"] = (
        f"{v['h4_verdict']} by the frozen rule, but at the edge." if edge else f"{v['h4_verdict']}."
    )
    explo = analysis.h4_context(con, "exploratory")
    post = analysis.h4_context(con, "post_hoc")
    v["h4_explo_ref"] = explo["reference_label"]
    v["h4_explo_n"] = f"{explo['reference']:.0f}"
    v["h4_explo_change"] = minus(f"{100 * explo['change_vs_reference']:+.1f}")
    v["h4_post_n"] = post["n_new_pairs"]
    v["h4_post_month"] = f"{post['snapshot']:%B %Y}"
    v["h4_post_change"] = minus(f"{100 * post['change_vs_reference']:+.1f}")
    snaps = {r["variant"]: r for r in h4p}
    snaps_s = {r["variant"]: r for r in h4s}
    lines = [
        "| Variant | Latest count | Baseline mean (Dec 2023, Dec 2024) | Band (mean ± 20%) | "
        "Change | Verdict, both baselines |",
        "|---|---:|---:|---:|---:|---|",
    ]
    names = {
        "total": "All goods",
        "ex_gold": "Without gold",
        "ex_gold_ex_energy": "Without gold and energy",
    }
    for key, label in names.items():
        a, b = snaps[key], snaps_s[key]
        verdict = (
            a["verdict"] if a["verdict"] == b["verdict"] else f"{a['verdict']} / {b['verdict']}"
        )
        lines.append(
            f"| {label} | {a['tariff_count']} | {a['baseline_mean']:.1f} | "
            f"{a['low']:.1f}–{a['high']:.1f} | {minus(f'{100 * a["change_vs_baseline"]:+.1f}')}% | "
            f"{verdict} |"
        )
    v["h4_table"] = "\n".join(lines)
    countries, chapters = analysis.h4_top(con, "country"), analysis.h4_top(con, "hs2")
    lines = ["| Rank | Destination | New pairs | Baseline mean |", "|---:|---|---:|---:|"]
    lines += [
        f"| {r['rank_in_snapshot']} | {r['label']} | {r['n_new_pairs']} | "
        f"{r['baseline_mean']:.1f} |"
        for r in countries
    ]
    v["h4_country_table"] = "\n".join(lines)
    lines = [
        "| Rank | HS2 chapter | Statistics Canada description | New pairs | Baseline mean |",
        "|---:|---|---|---:|---:|",
    ]
    lines += [
        f"| {r['rank_in_snapshot']} | {r['code']} {analysis.hs2_short(r['code'])} | {r['label']} | "
        f"{r['n_new_pairs']} | "
        f"{r['baseline_mean']:.1f} |"
        for r in chapters
    ]
    v["h4_chapter_table"] = "\n".join(lines)
    v["h4_countries"] = join([f"{r['label']} ({r['n_new_pairs']})" for r in countries], "; ")
    v["h4_chapters"] = join([f"HS {r['code']} ({r['n_new_pairs']})" for r in chapters])
    v["h4_top_country"], v["h4_top_country_n"] = countries[0]["label"], countries[0]["n_new_pairs"]
    v["h4_top_country_mean"] = f"{countries[0]['baseline_mean']:.1f}"
    v["h4_top_hs2"], v["h4_top_hs2_n"] = chapters[0]["code"], chapters[0]["n_new_pairs"]
    v["h4_top_hs2_mean"] = f"{chapters[0]['baseline_mean']:.1f}"
    v["h4_top_hs2_short"] = analysis.hs2_short(chapters[0]["code"]).lower()
    risers = analysis.h4_risers(con, "country")

    def the(name: str) -> str:
        return f"the {name}" if name in ("United Kingdom", "Netherlands", "United States") else name

    v["h4_risers"] = join(
        [f"{the(r['label'])} ({r['n_new_pairs']} vs {r['baseline_mean']:.1f})" for r in risers]
    )
    v["h4_risers_short"] = join(
        [
            f"{the(r['label'])} {r['n_new_pairs']} vs {r['baseline_mean']:.1f}"
            + (f" ({r['n_gold']} gold)" if r["n_gold"] else "")
            for r in risers
        ]
    )
    gold_notes = []
    for r in risers:
        if r["n_gold"]:
            plural = "s" if r["n_gold"] > 1 else ""
            text = f"{the(r['label'])}'s include {r['n_gold']} gold pair{plural}"
            if r["n_hs2_71"] > r["n_gold"]:
                text += f" (HS 7108; {r['n_hs2_71']} precious-metal pairs in chapter 71 in total)"
            gold_notes.append(text)
    v["h4_risers_gold"] = (
        "Gold is part of it: " + join(gold_notes, "; ") + "."
        if gold_notes
        else "None of these pairs are gold."
    )
    hs_risers = analysis.h4_risers(con, "hs2")
    top_rise = hs_risers[0]
    v["h4_hs2_riser"] = (
        f"HS {top_rise['code']} {analysis.hs2_short(top_rise['code']).lower()} "
        f"({top_rise['n_new_pairs']} vs {top_rise['baseline_mean']:.1f}"
        + (f", {top_rise['n_gold']} of them gold)" if top_rise["n_gold"] else ")")
    )
    v["h4_hs2_leader"] = (
        f"HS {chapters[0]['code']} {analysis.hs2_short(chapters[0]['code']).lower()} "
        f"({chapters[0]['n_new_pairs']} vs {chapters[0]['baseline_mean']:.1f})"
    )
    ch71 = next((r for r in chapters if r["code"] == "71"), None)
    v["h4_ch71_note"] = (
        " Chapter 71 includes gold (HS 7108): "
        f"{ch71['n_new_pairs'] - ch71['n_new_pairs_ex_gold_ex_energy']} "
        f"of its {ch71['n_new_pairs']} new pairs are gold."
        if ch71
        else ""
    )
    room = (tp["high"] - tp["tariff_count"]) / tp["baseline_mean"]
    if tp["verdict"] == "confirmed":
        v["h4_band_phrase"] = (
            f"just inside the frozen ±{tp['band']:.0%} band"
            if room < 0.02
            else f"inside the frozen ±{tp['band']:.0%} band"
        )
    else:
        v["h4_band_phrase"] = f"outside the frozen ±{tp['band']:.0%} band"
    v["h4_top_hs2_share"] = f"{chapters[0]['n_new_pairs'] / tp['tariff_count']:.0%}"
    fl = {
        (r["variant"], r["destination"]): r
        for r in analysis.records(con, "select * from mart_frontload_check")
    }
    v["fl_nonus"] = minus(f"{100 * fl[('total', 'Non-US')]['change_pct']:+.1f}")
    v["fl_nonus_abs"] = f"{abs(100 * fl[('total', 'Non-US')]['change_pct']):.1f}"
    # M8.
    rows = analysis.exposure(con, "primary")
    lines = [
        "| Sector | Share of exports, latest | US dependence, 2022–2024 | "
        "US dependence, latest | Change (pp) | Destination HHI, latest | "
        "Under a US sector tariff, latest (full / partial) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {SECTOR_NAMES[r['sector_group']]} | {100 * r['share_of_exports_latest']:.1f}% | "
            f"{100 * r['us_dependence_base']:.1f}% | {100 * r['us_dependence_latest']:.1f}% | "
            f"{minus(f'{r["us_dependence_change_pp"]:+.1f}')} | {r['hhi_latest']:.2f} | "
            f"{100 * r['share_full_scope']:.0f}% / {100 * r['share_partial_scope']:.0f}% |"
        )
    v["m8_table"] = "\n".join(lines)
    tariffed = [r for r in rows if r["is_tariffed_sector"]]
    v["m8_top"] = join(
        [
            f"{SECTOR_NAMES[r['sector_group']].lower()} ({100 * r['us_dependence_latest']:.0f}%)"
            for r in tariffed[:2]
        ]
    )
    v["m8_top_cap"] = v["m8_top"][0].upper() + v["m8_top"][1:]
    drop = min(rows, key=lambda r: r["us_dependence_change_pp"])
    v["m8_drop"] = SECTOR_NAMES[drop["sector_group"]].lower()
    v["m8_drop_size"] = f"{drop['x_sector_latest'] / 1e9:.1f}"
    v["m8_drop_base"] = f"{100 * drop['us_dependence_base']:.0f}"
    v["m8_drop_latest"] = f"{100 * drop['us_dependence_latest']:.0f}"
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
