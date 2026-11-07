"""Builds charts from marts and saves PNGs in figures/.

Style: titles state the finding, a source line sits under each chart, axes carry units,
colors come from a palette checked for colour-blind safety (blue #2a78d6, orange #eb6834).
"""

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from src import analysis  # noqa: E402
from src.common import ROOT, load_settings  # noqa: E402

FIGURES = ROOT / "figures"
DPI = 200
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
LEVEL = "#52514e"  # neutral ink for level (total) bars


def signed(value: float, digits: int = 1) -> str:
    """Signed number with a typographic minus."""
    return f"{value:+.{digits}f}".replace("-", "\u2212")


def source_line(con) -> str:
    first, last = con.execute(
        "select strftime(min(month), '%b %Y'), strftime(max(month), '%b %Y') from dim_month"
    ).fetchall()[0]
    return f"Source: Statistics Canada, CIMT domestic exports (customs basis), {first}–{last}."


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=INK_2, labelsize=9, length=3, color=AXIS)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def new_figure(width=9.0, height=5.2):
    plt.rcParams["font.family"] = ["Helvetica", "Arial", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(width, height), dpi=DPI)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    return fig, ax


def finish(fig, ax, title: str, subtitle: str, footer: str, name: str) -> None:
    fig.text(0.02, 0.965, title, ha="left", va="top", fontsize=13.5, weight="bold", color=INK)
    fig.text(0.02, 0.905, subtitle, ha="left", va="top", fontsize=10, color=INK_2)
    fig.text(
        0.02, 0.02, footer, ha="left", va="bottom", fontsize=8.2, color=MUTED, linespacing=1.45
    )
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(FIGURES / name, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


def pct(x, _pos=None) -> str:
    return f"{x:.0f}%"


def waterfall_chart(con, baseline: str = "primary") -> str:
    """M3: baseline share -> gold -> energy -> everything else -> latest share."""
    w = analysis.waterfall(con, baseline)
    start, end = analysis.tariff_window(con)
    steps = [("Gold", w["gold"]), ("Energy", w["energy"]), ("Everything\nelse", w["rest"])]
    labels = (
        [f"US share,\nbaseline\n{analysis.BASELINES[baseline]}"]
        + [s[0] for s in steps]
        + [f"US share,\nlatest 12 months\n{start}–{end}"]
    )

    fig, ax = new_figure()
    fig.subplots_adjust(top=0.80, bottom=0.33, left=0.08, right=0.97)
    width = 0.36
    ax.bar(0, w["s_base_pct"], width, color=LEVEL, zorder=2)
    ax.text(
        0,
        w["s_base_pct"] + 1.2,
        f"{w['s_base_pct']:.1f}%",
        ha="center",
        va="bottom",
        fontsize=10,
        color=INK,
        weight="bold",
    )
    level = w["s_base_pct"]
    for i, (_, value) in enumerate(steps, start=1):
        bottom = level + min(value, 0)
        ax.bar(i, abs(value), width, bottom=bottom, color=ORANGE if value < 0 else BLUE, zorder=2)
        ax.plot([i - 1 + width / 2, i - width / 2], [level, level], color=MUTED, lw=0.8, zorder=1)
        ax.text(
            i,
            max(level, level + value) + 1.2,
            f"{signed(value)} pp",
            ha="center",
            va="bottom",
            fontsize=10,
            color=INK,
        )
        level += value
    last = len(steps) + 1
    ax.plot([last - 1 + width / 2, last - width / 2], [level, level], color=MUTED, lw=0.8)
    ax.bar(last, w["s_tariff_pct"], width, color=LEVEL, zorder=2)
    ax.text(
        last,
        w["s_tariff_pct"] + 1.2,
        f"{w['s_tariff_pct']:.1f}%",
        ha="center",
        va="bottom",
        fontsize=10,
        color=INK,
        weight="bold",
    )
    ax.set_xticks(range(last + 1), labels, fontsize=9, color=INK_2)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, 88)
    ax.yaxis.set_major_formatter(FuncFormatter(pct))
    ax.set_ylabel("US share of Canada's domestic exports (%)", fontsize=9, color=INK_2)

    title = (
        f"Gold accounts for {abs(w['gold']):.1f} of the {abs(w['total']):.1f} pp drop "
        f"in the US share of Canada's exports"
    )
    subtitle = (
        f"Change in the US share in percentage points (pp): gold {signed(w['gold'])}, "
        f"energy {signed(w['energy'])}, everything else {signed(w['rest'])}. "
        f"Orange = lowers the share, blue = raises it."
    )
    g_lo, g_hi = sorted(w["gold_range"])
    e_lo, e_hi = sorted(w["energy_range"])
    footer = (
        f"Note: gold and energy effects are the average of two removal orders (gold first, "
        f"energy first). Range between orders: gold {signed(g_lo)} to {signed(g_hi)} pp; "
        f"energy {signed(e_lo)} to {signed(e_hi)} pp.\n"
        f"Gold = HS 7108; energy = HS 27. Shares use 12-month sums; the baseline averages each "
        f"calendar month over {analysis.BASELINES[baseline]}, without Nov 2024–Feb 2025.\n"
        f"Shares may not sum to 100% due to rounding.\n" + source_line(con)
    )
    name = "h2_waterfall.png" if baseline == "primary" else "h2_waterfall_sensitivity.png"
    finish(fig, ax, title, subtitle, footer, name)
    return name


def us_share_chart(con) -> str:
    """M1: rolling 12-month US share, all goods vs without gold and energy."""
    rows = analysis.records(
        con,
        """
        select month, variant, 100 * us_share_12m as share
        from mart_us_share
        where variant in ('total', 'ex_gold_ex_energy') and us_share_12m is not null
        order by month""",
    )
    series = {"total": ([], []), "ex_gold_ex_energy": ([], [])}
    for r in rows:
        series[r["variant"]][0].append(r["month"])
        series[r["variant"]][1].append(r["share"])
    first_event = con.execute(
        "select event_date from tariff_events where event_id = 'E01'"
    ).fetchall()[0][0]

    fig, ax = new_figure()
    fig.subplots_adjust(top=0.80, bottom=0.20, left=0.08, right=0.83)
    names = {
        "total": ("All goods", BLUE),
        "ex_gold_ex_energy": ("Without gold\nand energy", ORANGE),
    }
    for key, (label, color) in names.items():
        x, y = series[key]
        ax.plot(x, y, color=color, lw=2, solid_capstyle="round", zorder=3)
        ax.plot(x[-1], y[-1], "o", color=color, ms=6, mec=SURFACE, mew=1.5, zorder=4)
        ax.annotate(
            f"{label}\n{y[-1]:.1f}%",
            (x[-1], y[-1]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=INK,
        )
    ax.axvline(first_event, color=MUTED, lw=0.8, ls=(0, (3, 3)), zorder=1)
    ax.text(
        first_event,
        63.6,
        "  First US tariffs on\n  Canadian goods (Mar 2025)",
        fontsize=8.5,
        color=INK_2,
        va="bottom",
    )
    ax.set_ylim(63, 80)
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))
    ax.yaxis.set_major_formatter(FuncFormatter(pct))
    ax.set_ylabel("US share, 12-month sums (%)", fontsize=9, color=INK_2)

    total_last = series["total"][1][-1]
    both_last = series["ex_gold_ex_energy"][1][-1]
    peak_total = max(series["total"][1])
    title = "The US share fell much less once gold and energy are set aside"
    subtitle = (
        f"US share of Canada's domestic exports, rolling 12-month sums. All goods: peak "
        f"{peak_total:.1f}%, latest {total_last:.1f}%. Without gold and energy: latest "
        f"{both_last:.1f}%."
    )
    footer = (
        "Each point sums the 12 months ending in that month. The y-axis starts at 63%.\n"
        + source_line(con)
    )
    finish(fig, ax, title, subtitle, footer, "m1_us_share.png")
    return "m1_us_share.png"


def h1_chart(con, baseline: str = "primary") -> str:
    """M2: US-side vs rest-of-world-side contributions, all goods and without gold/energy."""
    cases = [
        ("All goods", analysis.h1(con, baseline, "total")),
        ("Without gold\nand energy", analysis.h1(con, baseline, "ex_gold_ex_energy")),
    ]
    fig, ax = new_figure(height=5.0)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    fig.subplots_adjust(top=0.70, bottom=0.26, left=0.17, right=0.95)
    height = 0.22
    for i, (_label, r) in enumerate(cases):
        y = len(cases) - 1 - i
        for offset, value, color, name in [
            (
                height / 2 + 0.02,
                100 * r["row_side"],
                ORANGE,
                "Rest-of-world side (exports elsewhere grew, pushing the share down)",
            ),
            (-height / 2 - 0.02, 100 * r["us_side"], BLUE, "US side (exports to the US fell)"),
        ]:
            ax.barh(
                y + offset, value, height, color=color, zorder=2, label=name if i == 0 else None
            )
            ax.text(
                value - 0.15,
                y + offset,
                signed(value).lstrip("+"),
                ha="right",
                va="center",
                fontsize=9,
                color=INK,
            )
    ax.set_yticks(range(len(cases)), [c[0] for c in reversed(cases)], fontsize=9.5, color=INK)
    ax.tick_params(axis="y", length=0)
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.set_xlim(-12.5, 0.5)
    ax.set_xlabel(
        "Contribution to the change in the log of the US share (log points × 100, about % change)",
        fontsize=9,
        color=INK_2,
    )
    ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=1, bbox_to_anchor=(0, 1.0))
    total = cases[0][1]
    title = (
        f"About {total['row_share_of_change']:.0%} of the drop in the US share is linked "
        f"to faster growth in exports to other countries"
    )
    subtitle = (
        f"Baseline {analysis.BASELINES[baseline]} vs latest 12 months. Negative bars lower "
        f"the US share; the longer the bar, the bigger its part in the drop."
    )
    forms = ", ".join(f"{c[0].replace(chr(10), ' ').lower()}: {c[1]['method']}" for c in cases)
    footer = (
        f"Weight: rest-of-world share of exports. Form used: {forms}.\n"
        f"The exact form (log-mean weights) applies when the simple form's error is "
        f"above 10% of the total.\n" + source_line(con)
    )
    finish(fig, ax, title, subtitle, footer, "h1_decomposition.png")
    return "h1_decomposition.png"


def price_volume_chart(con, baseline: str = "primary") -> str:
    """M4: price and volume effects for gold and crude, to the US and to other countries."""
    cases = [
        ("Gold → other\ncountries", "gold", "Non-US"),
        ("Gold → US", "gold", "United States"),
        ("Crude oil → other\ncountries", "crude", "Non-US"),
        ("Crude oil → US", "crude", "United States"),
    ]
    rows = [(label, analysis.price_volume(con, baseline, c, d)) for label, c, d in cases]
    fig, ax = new_figure(height=5.0)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    fig.subplots_adjust(top=0.76, bottom=0.25, left=0.18, right=0.95)
    height = 0.26
    for i, (_label, r) in enumerate(rows):
        y = len(rows) - 1 - i
        for offset, value, color, name in [
            (height / 2 + 0.02, r["price_effect"] / 1e9, BLUE, "Price effect"),
            (-height / 2 - 0.02, r["volume_effect"] / 1e9, ORANGE, "Volume effect"),
        ]:
            ax.barh(
                y + offset, value, height, color=color, zorder=2, label=name if i == 0 else None
            )
            pad = 0.6 if value >= 0 else -0.6
            text = "≈0" if abs(value) < 0.05 else signed(value)
            ax.text(
                value + pad,
                y + offset,
                text,
                ha="left" if value >= 0 else "right",
                va="center",
                fontsize=9,
                color=INK,
            )
        ax.text(
            1.0,
            y,
            f"total {signed(r['d_value'] / 1e9)}",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=9,
            color=INK_2,
        )
    ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)], fontsize=9.5, color=INK)
    ax.tick_params(axis="y", length=0)
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.set_xlim(-12, 48)
    ax.set_xlabel("Change in yearly export value, CAD billions", fontsize=9, color=INK_2)
    ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=2, bbox_to_anchor=(0, 1.0))
    g = rows[0][1]
    title = (
        f"Higher gold prices account for {g['price_share']:.0%} of the rise in gold "
        f"exports to other countries"
    )
    subtitle = (
        f"Baseline {analysis.BASELINES[baseline]} vs latest 12 months. Gold to other "
        f"countries: price per gram {signed(100 * g['p_growth'], 0)}%, grams "
        f"{signed(100 * g['q_growth'], 0)}%."
    )
    footer = (
        "Price = customs unit value (value / quantity: grams for gold HS 7108, cubic metres "
        "for crude HS 2709).\nMidpoint split: change in value = change in price × average "
        "quantity + change in quantity × average price.\n" + source_line(con)
    )
    finish(fig, ax, title, subtitle, footer, "m4_price_volume.png")
    return "m4_price_volume.png"


def names(items: list[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def h3_chart(con) -> str:
    """M6/H3: offset ratio by tariffed sector, and % changes next to the comparison group."""
    t = load_settings()["thresholds"]
    lo, hi = t["h3_offset_ratio_confirm_below"], t["h3_offset_ratio_reject_above"]
    prim = analysis.h3(con, "primary")
    sens = {r["sector_group"]: r for r in analysis.h3(con, "sensitivity")}
    group = analysis.no_sector_tariff(con, "primary", "steel", "ex_gold_ex_energy")

    plt.rcParams["font.family"] = ["Helvetica", "Arial", "DejaVu Sans"]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11, 6.4), dpi=DPI, gridspec_kw={"width_ratios": [1, 1.25]}
    )
    fig.patch.set_facecolor(SURFACE)
    fig.subplots_adjust(top=0.81, bottom=0.28, left=0.12, right=0.97, wspace=0.42)
    for ax in (ax1, ax2):
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.tick_params(axis="y", length=0)

    # Left: offset ratio, primary bars and sensitivity markers, with the frozen zones.
    n = len(prim)
    ys = list(range(n - 1, -1, -1))
    ax1.axvspan(-0.25, lo, color="#f1f0eb", zorder=0)
    ax1.axvspan(hi, 1.25, color="#f1f0eb", zorder=0)
    for x, text in [
        ((-0.25 + lo) / 2, "Not redirected\n(< 0.25)"),
        ((lo + hi) / 2, "Partial"),
        ((hi + 1.25) / 2, "Redirected\n(> 0.75)"),
    ]:
        ax1.text(x, n - 0.35, text, ha="center", va="bottom", fontsize=8.5, color=INK_2)
    for y, r in zip(ys, prim, strict=True):
        v = r["offset_ratio"]
        ax1.barh(
            y, v, 0.42, color=LEVEL, zorder=2, label="Baseline 2022–2024" if y == ys[0] else None
        )
        s_v = sens[r["sector_group"]]["offset_ratio"]
        ax1.plot(
            s_v,
            y,
            "o",
            ms=7,
            mfc=SURFACE,
            mec=INK,
            mew=1.4,
            zorder=3,
            label="Baseline 2023–2024" if y == ys[0] else None,
        )
        ax1.text(
            max(v, s_v, 0) + 0.04,
            y,
            f"{signed(v, 2)}  (H3 {r['verdict']})",
            ha="left",
            va="center",
            fontsize=8.5,
            color=INK,
        )
    ax1.set_yticks(ys, [r["label"] for r in prim], fontsize=9.5, color=INK)
    ax1.axvline(0, color=AXIS, lw=0.8)
    ax1.set_xlim(-0.25, 1.25)
    ax1.set_ylim(-0.6, n + 0.25)
    ax1.set_xlabel("Offset ratio: non-US gain ÷ US loss", fontsize=9, color=INK_2)
    ax1.legend(
        loc="upper left",
        bbox_to_anchor=(-0.02, -0.13),
        frameon=False,
        fontsize=8.5,
        ncol=2,
        handlelength=1.2,
    )

    # Right: % change toward the US and toward other countries, plus the comparison group.
    cap = 100
    rows = [(r["label"], r["d_us_pct"], r["d_nonus_pct"]) for r in prim]
    rows.append(
        ("No sector-specific\ntariff (comparison)", group["d_us_pct"], group["d_nonus_pct"])
    )
    m = len(rows)
    ys2 = [m - i - (0.5 if i == m - 1 else 0) for i in range(m)]
    h = 0.32
    for y, (_label, us, row) in zip(ys2, rows, strict=True):
        for off, value, color, name in [
            (h / 2 + 0.02, 100 * us, BLUE, "To the US"),
            (-h / 2 - 0.02, 100 * row, ORANGE, "To other countries"),
        ]:
            shown = min(value, cap)
            ax2.barh(y + off, shown, h, color=color, zorder=2, label=name if y == ys2[0] else None)
            text = f"{signed(value, 0)}%" + (" (bar cut)" if value > cap else "")
            ax2.text(
                shown + (2.5 if value >= 0 else -2.5),
                y + off,
                text,
                ha="left" if value >= 0 else "right",
                va="center",
                fontsize=8.5,
                color=INK,
            )
    ax2.axhline((ys2[-2] + ys2[-1]) / 2, color=AXIS, lw=0.8, ls=(0, (3, 3)))
    ax2.set_yticks(ys2, [r[0] for r in rows], fontsize=9.5, color=INK)
    ax2.axvline(0, color=AXIS, lw=0.8)
    ax2.set_xlim(-125, 150)
    ax2.xaxis.set_major_formatter(FuncFormatter(pct))
    ax2.set_xlabel("Change in exports vs baseline (%)", fontsize=9, color=INK_2)
    ax2.legend(
        loc="upper left",
        bbox_to_anchor=(-0.02, -0.13),
        frameon=False,
        fontsize=8.5,
        ncol=2,
        handlelength=1.2,
    )

    short = {"autos": "autos", "lumber": "lumber"}
    by_verdict = {}
    for r in prim:
        by_verdict.setdefault(r["verdict"], []).append(r)
    parts = []
    for r in by_verdict.get("rejected", []):
        parts.append(f"{r['label']} redirected {r['offset_ratio']:.0%} of its US loss")
    if "confirmed" in by_verdict:
        sectors = [
            short.get(r["sector_group"], r["label"].lower()) for r in by_verdict["confirmed"]
        ]
        parts.append(f"{names(sectors)} did not redirect")
    title = "; ".join(parts)
    title = title[0].upper() + title[1:]
    subtitle = (
        f"Products with no sector-specific tariff changed {signed(100 * group['d_us_pct'])}% "
        f"to the US and {signed(100 * group['d_nonus_pct'])}% elsewhere: the fall in US sales "
        f"is concentrated in the tariffed sectors."
    )
    lumber = next(r for r in prim if r["sector_group"] == "lumber")
    amounts = "; ".join(
        f"{r['label'].lower()} CAD {r['x_nonus_base'] / 1e9:.1f} bn → "
        f"{r['x_nonus_tariff'] / 1e9:.1f} bn"
        for r in prim
        if r["sector_group"] in ("copper", "aluminum")
    )
    footer = (
        "Offset ratio = gain in exports to other countries ÷ loss in exports to the US, latest "
        "window vs baseline 2022–2024. Frozen rule: H3 confirmed below "
        f"{lo}, rejected above {hi}.\n"
        f"Exports to other countries, baseline → latest window: {amounts}. Large % changes "
        "start from small bases.\n"
        "Each window starts in the first full month after the sector's first US tariff and is "
        f"the latest 12 months; softwood lumber has {lumber['n_months']} months "
        f"({lumber['window_start']:%b %Y}–{lumber['window_end']:%b %Y}), same calendar months "
        "in the baseline.\n"
        "Comparison group: products outside the five sectors with no sector-specific US tariff "
        "that month, without gold and energy (Oct 2025–Sep 2026).\n" + source_line(con)
    )
    fig.text(0.02, 0.965, title, ha="left", va="top", fontsize=13.5, weight="bold", color=INK)
    fig.text(0.02, 0.905, subtitle, ha="left", va="top", fontsize=10, color=INK_2, wrap=True)
    fig.text(
        0.02, 0.02, footer, ha="left", va="bottom", fontsize=8.2, color=MUTED, linespacing=1.45
    )
    fig.savefig(FIGURES / "h3_redirection.png", dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
    return "h3_redirection.png"


def h4_chart(con) -> str:
    """M7/H4: new non-US pairs at each frozen snapshot against the frozen band."""
    rows = analysis.records(
        con,
        "select snapshot, role, n_new_pairs from mart_extensive_margin "
        "where variant = 'total' and role in ('baseline', 'tariff') order by snapshot",
    )
    prim = analysis.h4(con, "primary")[0]
    sens = analysis.h4(con, "sensitivity")[0]
    explo = analysis.h4_context(con, "exploratory")
    post = analysis.h4_context(con, "post_hoc")
    fig, ax = new_figure(width=10.0, height=5.8)
    fig.subplots_adjust(top=0.80, bottom=0.31, left=0.09, right=0.74)
    ax.axhspan(prim["low"], prim["high"], color="#f1f0eb", zorder=0)
    ax.axhline(prim["baseline_mean"], color=MUTED, lw=0.8, ls=(0, (3, 3)), zorder=1)
    for i, r in enumerate(rows):
        color = ORANGE if r["role"] == "tariff" else LEVEL
        ax.bar(i, r["n_new_pairs"], 0.45, color=color, zorder=2)
        ax.text(
            i,
            r["n_new_pairs"] + 8,
            f"{r['n_new_pairs']}",
            ha="center",
            va="bottom",
            fontsize=10,
            color=INK,
            weight="bold",
        )
    labels = [
        f"{r['snapshot']:%b %Y}\n" + ("baseline" if r["role"] == "baseline" else "latest month")
        for r in rows
    ]
    ax.set_xticks(range(len(rows)), labels, fontsize=9, color=INK_2)
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylim(0, 720)
    ax.set_ylabel("New product × country pairs outside the US (count)", fontsize=9, color=INK_2)
    right = ax.get_yaxis_transform()
    for y, text, va in [
        (prim["high"], f"Upper limit: {prim['high']:.1f}", "bottom"),
        (prim["baseline_mean"], f"Baseline mean: {prim['baseline_mean']:.1f}", "center"),
        (prim["low"], f"Lower limit: {prim['low']:.1f}", "bottom"),
    ]:
        ax.text(1.01, y, text, transform=right, fontsize=8.5, color=INK_2, va=va)
    title = (
        f"New export pairs outside the US reached {prim['tariff_count']}, at the edge of the "
        f"frozen band ({prim['high']:.0f})"
    )
    same = prim["verdict"] == sens["verdict"]
    subtitle = (
        f"{signed(100 * prim['change_vs_baseline'])}% vs the baseline mean of Dec 2023 and "
        f"Dec 2024 (both baselines). H4 {prim['verdict']} by the frozen rule"
        + (", the same with both baselines." if same else "; the verdict differs by baseline.")
    )
    notes = []
    if explo:
        notes.append(
            f"Exploratory, defined after seeing the result (not a verdict): vs the "
            f"{explo['reference_label']} alone ({explo['reference']:.0f}), the latest count is "
            f"{signed(100 * explo['change_vs_reference'])}%."
        )
    if post:
        notes.append(
            f"Post hoc context: {post['n_new_pairs']} new pairs in {post['snapshot']:%b %Y}, the "
            f"same calendar month as the baseline snapshots "
            f"({signed(100 * post['change_vs_reference'])}% vs the baseline mean)."
        )
    footer = (
        "New pair: an HS6 product × non-US country with under CAD 100,000 in the prior 12 "
        "months and over CAD 1 million in the latest 12 months,\nat 3 consecutive month-ends. "
        "Shaded band: baseline mean ± 20% (frozen rule). The latest month's prior 12 months "
        "include\nthe front-loading months (Nov 2024–Feb 2025), which can make fewer pairs look "
        "new. All goods.\n" + "\n".join(notes) + "\n" + source_line(con)
    )
    finish(fig, ax, title, subtitle, footer, "h4_new_pairs.png")
    return "h4_new_pairs.png"


def wrap_label(text: str, width: int = 34, lines: int = 2) -> str:
    out = textwrap.wrap(text, width)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1].rstrip(",;") + "…"
    return "\n".join(out)


def h4_where_chart(con) -> str:
    """Where the new pairs are: top destination countries and HS2 chapters (ties kept)."""
    countries = analysis.h4_top(con, "country")
    chapters = analysis.h4_top(con, "hs2")
    plt.rcParams["font.family"] = ["Helvetica", "Arial", "DejaVu Sans"]
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11, 6.2), dpi=DPI, gridspec_kw={"width_ratios": [1, 1.25]}
    )
    fig.patch.set_facecolor(SURFACE)
    fig.subplots_adjust(top=0.78, bottom=0.23, left=0.13, right=0.97, wspace=0.45)
    for ax, rows, label_of, head in [
        (ax1, countries, lambda r: r["label"], "Destination country"),
        (ax2, chapters, lambda r: f"{r['code']} {analysis.hs2_short(r['code'])}", "HS2 chapter"),
    ]:
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.tick_params(axis="y", length=0)
        ys = list(range(len(rows) - 1, -1, -1))
        xmax = max(max(r["n_new_pairs"], r["baseline_mean"]) for r in rows) * 1.15
        for y, r in zip(ys, rows, strict=True):
            ax.barh(
                y,
                r["n_new_pairs"],
                0.55,
                color=ORANGE,
                zorder=2,
                label="Latest month (Sep 2026)" if y == ys[0] else None,
            )
            ax.plot(
                r["baseline_mean"],
                y,
                "D",
                ms=6,
                color=INK,
                mec=SURFACE,
                mew=1.2,
                zorder=3,
                label="Baseline mean (Dec 2023, Dec 2024)" if y == ys[0] else None,
            )
            ax.text(
                max(r["n_new_pairs"], r["baseline_mean"]) + 0.05 * xmax,
                y,
                f"{r['n_new_pairs']}",
                ha="left",
                va="center",
                fontsize=9,
                color=INK,
            )
        ax.set_yticks(ys, [label_of(r) for r in rows], fontsize=8.8, color=INK)
        ax.set_xlim(0, xmax)
        ax.set_title(head, loc="left", fontsize=10, color=INK, weight="bold", pad=8)
        ax.set_xlabel("New pairs (count)", fontsize=9, color=INK_2)
    ax1.legend(
        loc="upper left",
        bbox_to_anchor=(-0.3, -0.11),
        frameon=False,
        fontsize=8.5,
        ncol=2,
        handlelength=1.2,
    )
    top_c, top_h = countries[0], chapters[0]
    title = (
        f"{top_c['label']} and {analysis.hs2_short(top_h['code']).lower()} "
        f"(HS {top_h['code']}) have the most new export pairs outside the US"
    )
    subtitle = (
        f"Top 5 destinations and top 5 HS2 chapters by new pairs in the latest 12 months "
        f"(ties shown). {top_c['label']}: {top_c['n_new_pairs']} vs a baseline mean of "
        f"{top_c['baseline_mean']:.1f}."
    )
    gold_note = ""
    ch71 = next((r for r in chapters if r["code"] == "71"), None)
    if ch71:
        gold_note = (
            f" Chapter 71 includes gold (HS 7108): "
            f"{ch71['n_new_pairs'] - ch71['n_new_pairs_ex_gold_ex_energy']} of its "
            f"{ch71['n_new_pairs']} new pairs are gold."
        )
    footer = (
        "New pair: an HS6 product × non-US country with under CAD 100,000 in the prior 12 months "
        "and over CAD 1 million in the latest 12 months, at 3 consecutive\nmonth-ends. All goods. "
        "Short chapter names are mapped in config/settings.yaml (hs2_short_names) from Statistics "
        "Canada's HS2 descriptions.\n" + gold_note.strip() + "\n" + source_line(con)
    )
    fig.text(0.02, 0.965, title, ha="left", va="top", fontsize=13.5, weight="bold", color=INK)
    fig.text(0.02, 0.905, subtitle, ha="left", va="top", fontsize=10, color=INK_2)
    fig.text(
        0.02, 0.02, footer, ha="left", va="bottom", fontsize=8.2, color=MUTED, linespacing=1.45
    )
    fig.savefig(FIGURES / "h4_where_new_pairs.png", dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
    return "h4_where_new_pairs.png"


SECTOR_LABELS = {
    "steel": "Steel",
    "aluminum": "Aluminum",
    "copper": "Copper",
    "autos": "Autos and parts",
    "lumber": "Softwood lumber",
    "energy": "Energy (HS 27)",
    "gold": "Gold (HS 7108)",
    "other": "All other goods",
}


def exposure_chart(con) -> str:
    """M8: US dependence by sector, baseline vs latest 12 months (dumbbell)."""
    rows = analysis.exposure(con, "primary")
    fig, ax = new_figure(width=9.5, height=6.2)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.tick_params(axis="y", length=0)
    fig.subplots_adjust(top=0.79, bottom=0.22, left=0.19, right=0.95)
    ys = list(range(len(rows) - 1, -1, -1))
    for y, r in zip(ys, rows, strict=True):
        b, latest = 100 * r["us_dependence_base"], 100 * r["us_dependence_latest"]
        ax.plot([b, latest], [y, y], color=AXIS, lw=2, zorder=1, solid_capstyle="round")
        ax.plot(
            b,
            y,
            "o",
            ms=7,
            color=LEVEL,
            mec=SURFACE,
            mew=1.2,
            zorder=2,
            label="Baseline 2022–2024" if y == ys[0] else None,
        )
        ax.plot(
            latest,
            y,
            "o",
            ms=8,
            color=BLUE,
            mec=SURFACE,
            mew=1.2,
            zorder=3,
            label="Latest 12 months" if y == ys[0] else None,
        )
        ax.text(
            min(b, latest) - 2.2,
            y,
            f"{latest:.0f}%",
            ha="right",
            va="center",
            fontsize=9,
            color=INK,
        )
        ax.text(
            max(b, latest) + 2.2,
            y,
            f"{signed(r['us_dependence_change_pp'])} pp",
            ha="left",
            va="center",
            fontsize=8.5,
            color=INK_2,
        )
    ax.set_yticks(
        ys,
        [
            f"{SECTOR_LABELS[r['sector_group']]}\nCAD {r['x_sector_latest'] / 1e9:,.1f} bn"
            for r in rows
        ],
        fontsize=9.2,
        color=INK,
    )
    ax.set_xlim(-8, 112)
    ax.xaxis.set_major_formatter(FuncFormatter(pct))
    ax.set_xlabel(
        "US dependence: exports to the US ÷ the sector's exports (%)", fontsize=9, color=INK_2
    )
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, fontsize=9, ncol=2)
    top = [r for r in rows if r["is_tariffed_sector"]][:2]
    drop = min(rows, key=lambda r: r["us_dependence_change_pp"])
    title = (
        names(
            [
                f"{SECTOR_LABELS[r['sector_group']].lower()} "
                f"({100 * r['us_dependence_latest']:.0f}%)"
                for r in top
            ]
        ).capitalize()
        + f" still depend most on the US; {SECTOR_LABELS[drop['sector_group']].lower()} "
        f"fell from {100 * drop['us_dependence_base']:.0f}% to "
        f"{100 * drop['us_dependence_latest']:.0f}%"
    )
    subtitle = (
        "Share of each sector's exports going to the US, 2022–2024 vs latest 12 months. "
        f"{SECTOR_LABELS[drop['sector_group']]} is small: CAD "
        f"{drop['x_sector_latest'] / 1e9:.1f} bn a year."
    )
    footer = (
        "Baseline: each calendar month averaged over 2022–2024, without Nov 2024–Feb 2025. "
        "Latest 12 months: Oct 2025–Sep 2026.\nUnder each sector name: its exports in the latest "
        "12 months, CAD billions.\nSector groups follow the official US tariff lists (see "
        "docs/methodology.md); gold and energy are shown as their own groups.\n" + source_line(con)
    )
    finish(fig, ax, title, subtitle, footer, "m8_exposure.png")
    return "m8_exposure.png"


def main() -> None:
    con = analysis.connect()
    for name in [
        waterfall_chart(con, "primary"),
        waterfall_chart(con, "sensitivity"),
        us_share_chart(con),
        h1_chart(con, "primary"),
        price_volume_chart(con),
        h3_chart(con),
        h4_chart(con),
        h4_where_chart(con),
        exposure_chart(con),
    ]:
        print(f"  figures/{name}")
    con.close()


if __name__ == "__main__":
    main()
