"""Builds charts from marts and saves PNGs in figures/.

Style: titles state the finding, a source line sits under each chart, axes carry units,
colors come from a palette checked for colour-blind safety (blue #2a78d6, orange #eb6834).
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from src import analysis  # noqa: E402
from src.common import ROOT  # noqa: E402

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


def main() -> None:
    con = analysis.connect()
    for name in [
        waterfall_chart(con, "primary"),
        waterfall_chart(con, "sensitivity"),
        us_share_chart(con),
        h1_chart(con, "primary"),
        price_volume_chart(con),
    ]:
        print(f"  figures/{name}")
    con.close()


if __name__ == "__main__":
    main()
